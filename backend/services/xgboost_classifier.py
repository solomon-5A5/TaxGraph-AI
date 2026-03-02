"""
XGBoostFraudClassifier — ML-based fraud classification using XGBoost.
Extracts features from Neo4j graph + DataFrames, trains a gradient-boosted
tree classifier, and provides explainable predictions with feature importance.
"""

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
)
from services.neo4j_driver import run_read_query
import networkx as nx


# Feature column ordering (must be consistent between train and predict)
FEATURE_COLUMNS = [
    "pagerank_score",
    "in_degree",
    "out_degree",
    "total_invoices_issued",
    "total_invoices_received",
    "total_outward_value",
    "total_inward_value",
    "filing_count",
    "total_itc_claimed",
    "total_sales_declared",
    "total_tax_paid_cash",
    "zero_cash_tax_months",
    "itc_to_sales_ratio",
    "avg_invoice_value",
    "degree_ratio",
    "itc_over_inward_ratio",
]


class XGBoostFraudClassifier:
    """XGBoost-based fraud classifier for GST taxpayers."""

    def __init__(self, gstr1_df: pd.DataFrame, gstr2b_df: pd.DataFrame,
                 gstr3b_df: pd.DataFrame, fraud_labels_df: pd.DataFrame):
        self.gstr1 = gstr1_df
        self.gstr2b = gstr2b_df
        self.gstr3b = gstr3b_df
        self.fraud_labels = fraud_labels_df
        self.model = None
        self.feature_importance = {}
        self.metrics = {}
        self._pagerank = None

    # ─────────────────────────────────────────────
    # Feature Engineering
    # ─────────────────────────────────────────────
    def _compute_pagerank(self) -> dict:
        """Fetch adjacency from Neo4j and compute PageRank via NetworkX."""
        if self._pagerank is not None:
            return self._pagerank
        try:
            edges = run_read_query(
                "MATCH (a:Taxpayer)-[:INVOICE]->(b:Taxpayer) RETURN a.gstin AS src, b.gstin AS dst"
            )
            nodes = run_read_query("MATCH (t:Taxpayer) RETURN t.gstin AS gstin")
            G = nx.DiGraph()
            for e in edges:
                G.add_edge(e["src"], e["dst"])
            for n in nodes:
                G.add_node(n["gstin"])
            self._pagerank = nx.pagerank(G, alpha=0.85, max_iter=100)
        except Exception:
            self._pagerank = {}
        return self._pagerank

    def _get_degree(self, gstin: str) -> tuple:
        """Get in-degree and out-degree from Neo4j."""
        in_result = run_read_query(
            "MATCH ()-[:INVOICE]->(t:Taxpayer {gstin:$g}) RETURN count(*) AS c", {"g": gstin}
        )
        out_result = run_read_query(
            "MATCH (t:Taxpayer {gstin:$g})-[:INVOICE]->() RETURN count(*) AS c", {"g": gstin}
        )
        in_deg = in_result[0]["c"] if in_result else 0
        out_deg = out_result[0]["c"] if out_result else 0
        return in_deg, out_deg

    def extract_features(self, gstin: str) -> dict:
        """Extract all ML features for a GSTIN."""
        f = {}

        # Graph features
        pr = self._compute_pagerank()
        f["pagerank_score"] = float(pr.get(gstin, 0))
        in_deg, out_deg = self._get_degree(gstin)
        f["in_degree"] = in_deg
        f["out_degree"] = out_deg

        # Invoice features
        if not self.gstr1.empty:
            seller = self.gstr1[self.gstr1["supplier_gstin"] == gstin]
            buyer = self.gstr1[self.gstr1["receiver_gstin"] == gstin]
            f["total_invoices_issued"] = len(seller)
            f["total_invoices_received"] = len(buyer)
            f["total_outward_value"] = float(seller["total_value"].sum())
            f["total_inward_value"] = float(buyer["total_value"].sum())
            f["avg_invoice_value"] = float(seller["total_value"].mean()) if len(seller) > 0 else 0
        else:
            f["total_invoices_issued"] = 0
            f["total_invoices_received"] = 0
            f["total_outward_value"] = 0.0
            f["total_inward_value"] = 0.0
            f["avg_invoice_value"] = 0.0

        # GSTR-3B features
        if not self.gstr3b.empty:
            filings = self.gstr3b[self.gstr3b["gstin"] == gstin]
            f["filing_count"] = len(filings)
            if not filings.empty:
                itc = float(filings["total_itc_claimed"].sum()) if "total_itc_claimed" in filings.columns else 0
                sales = float(filings["total_sales_declared"].sum()) if "total_sales_declared" in filings.columns else 0
                cash = float(filings["tax_paid_cash"].sum()) if "tax_paid_cash" in filings.columns else 0
                zero = int((filings["tax_paid_cash"] == 0).sum()) if "tax_paid_cash" in filings.columns else 0
                f["total_itc_claimed"] = itc
                f["total_sales_declared"] = sales
                f["total_tax_paid_cash"] = cash
                f["zero_cash_tax_months"] = zero
                f["itc_to_sales_ratio"] = itc / max(sales, 1)
            else:
                f["filing_count"] = 0
                f["total_itc_claimed"] = 0.0
                f["total_sales_declared"] = 0.0
                f["total_tax_paid_cash"] = 0.0
                f["zero_cash_tax_months"] = 0
                f["itc_to_sales_ratio"] = 0.0
        else:
            f["filing_count"] = 0
            f["total_itc_claimed"] = 0.0
            f["total_sales_declared"] = 0.0
            f["total_tax_paid_cash"] = 0.0
            f["zero_cash_tax_months"] = 0
            f["itc_to_sales_ratio"] = 0.0

        # Derived features
        total_deg = f["in_degree"] + f["out_degree"]
        f["degree_ratio"] = f["out_degree"] / max(total_deg, 1)
        f["itc_over_inward_ratio"] = f["total_itc_claimed"] / max(f["total_inward_value"], 1)

        return f

    def _build_feature_matrix(self) -> tuple:
        """Build feature matrix X and label vector y from all labeled GSTINs."""
        if self.fraud_labels.empty:
            return None, None

        X_rows = []
        y = []

        for _, row in self.fraud_labels.iterrows():
            gstin = row["gstin"]
            label = int(row.get("is_fraud", 0))
            features = self.extract_features(gstin)
            X_rows.append([features.get(col, 0) for col in FEATURE_COLUMNS])
            y.append(label)

        X = np.array(X_rows, dtype=np.float32)
        y = np.array(y, dtype=np.int32)

        # Replace NaN/inf with 0
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        return X, y

    # ─────────────────────────────────────────────
    # Training
    # ─────────────────────────────────────────────
    def train(self) -> dict:
        """Train the XGBoost fraud classifier."""
        X, y = self._build_feature_matrix()
        if X is None or len(X) < 4:
            return {"error": "Not enough data to train", "trained": False}

        n_fraud = int(y.sum())
        n_clean = int(len(y) - n_fraud)

        # Handle class imbalance with scale_pos_weight
        scale = n_clean / max(n_fraud, 1)

        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.1,
            scale_pos_weight=scale,
            eval_metric="logloss",
            random_state=42,
        )

        # Train on full data (small dataset — also compute LOO-style metrics)
        self.model.fit(X, y)

        # Predictions on training data
        y_pred = self.model.predict(X)
        y_proba = self.model.predict_proba(X)[:, 1]

        # Compute metrics
        self.metrics = {
            "accuracy": round(float(accuracy_score(y, y_pred)), 4),
            "precision": round(float(precision_score(y, y_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y, y_pred, zero_division=0)), 4),
            "f1_score": round(float(f1_score(y, y_pred, zero_division=0)), 4),
            "samples": len(y),
            "fraud_count": n_fraud,
            "clean_count": n_clean,
        }

        # Cross-validation (Leave-One-Out for small datasets)
        if len(y) >= 6:
            n_splits = min(5, n_fraud, n_clean)
            if n_splits >= 2:
                cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
                cv_scores = cross_val_score(self.model, X, y, cv=cv, scoring="f1")
                self.metrics["cv_f1_mean"] = round(float(cv_scores.mean()), 4)
                self.metrics["cv_f1_std"] = round(float(cv_scores.std()), 4)

        # Confusion matrix
        cm = confusion_matrix(y, y_pred)
        self.metrics["confusion_matrix"] = {
            "true_negatives": int(cm[0][0]),
            "false_positives": int(cm[0][1]) if cm.shape[1] > 1 else 0,
            "false_negatives": int(cm[1][0]) if cm.shape[0] > 1 else 0,
            "true_positives": int(cm[1][1]) if cm.shape[0] > 1 and cm.shape[1] > 1 else 0,
        }

        # Feature importance
        importance = self.model.feature_importances_
        self.feature_importance = {
            col: round(float(imp), 4)
            for col, imp in sorted(
                zip(FEATURE_COLUMNS, importance),
                key=lambda x: x[1], reverse=True,
            )
        }
        self.metrics["feature_importance"] = self.feature_importance

        return {
            "trained": True,
            "metrics": self.metrics,
        }

    # ─────────────────────────────────────────────
    # Prediction
    # ─────────────────────────────────────────────
    def predict(self, gstin: str) -> dict:
        """Predict fraud probability for a single GSTIN."""
        if self.model is None:
            self.train()

        features = self.extract_features(gstin)
        X = np.array([[features.get(col, 0) for col in FEATURE_COLUMNS]], dtype=np.float32)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        proba = float(self.model.predict_proba(X)[0][1])
        prediction = int(self.model.predict(X)[0])

        # Determine risk level from probability
        if proba >= 0.85:
            risk_level = "CRITICAL"
        elif proba >= 0.65:
            risk_level = "HIGH"
        elif proba >= 0.35:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Get top contributing features
        top_features = []
        if self.feature_importance:
            sorted_imp = sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)
            for feat_name, imp in sorted_imp[:5]:
                feat_value = features.get(feat_name, 0)
                top_features.append({
                    "feature": feat_name,
                    "importance": imp,
                    "value": round(float(feat_value), 4) if isinstance(feat_value, (int, float)) else feat_value,
                })

        return {
            "gstin": gstin,
            "is_fraud_predicted": prediction,
            "fraud_probability": round(proba, 4),
            "risk_level": risk_level,
            "features": {k: round(float(v), 4) if isinstance(v, (int, float, np.floating)) else v
                         for k, v in features.items()},
            "top_contributing_features": top_features,
        }

    def predict_all(self) -> dict:
        """Predict fraud for all taxpayers and return ranked results."""
        if self.model is None:
            self.train()

        all_gstins = run_read_query("MATCH (t:Taxpayer) RETURN t.gstin AS gstin")
        if not all_gstins:
            return {"predictions": [], "model_metrics": self.metrics}

        predictions = []
        for record in all_gstins:
            pred = self.predict(record["gstin"])
            predictions.append(pred)

        # Sort by fraud probability (highest first)
        predictions.sort(key=lambda x: x["fraud_probability"], reverse=True)

        return {
            "predictions": predictions,
            "model_metrics": self.metrics,
            "total_taxpayers": len(predictions),
            "predicted_fraud": sum(1 for p in predictions if p["is_fraud_predicted"] == 1),
            "predicted_clean": sum(1 for p in predictions if p["is_fraud_predicted"] == 0),
        }
