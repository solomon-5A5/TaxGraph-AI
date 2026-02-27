"""
RiskScoringEngine — Compute risk scores for each taxpayer using
features from DataFrames + NetworkX graph metrics.
"""

import networkx as nx
import pandas as pd


class RiskScoringEngine:
    """Compute risk scores using graph features + filing behavior."""

    def __init__(self, graph: nx.DiGraph, gstr1_df: pd.DataFrame,
                 gstr2b_df: pd.DataFrame, gstr3b_df: pd.DataFrame,
                 fraud_labels_df: pd.DataFrame):
        self.graph = graph
        self.gstr1 = gstr1_df
        self.gstr2b = gstr2b_df
        self.gstr3b = gstr3b_df
        self.fraud_labels = fraud_labels_df
        self._pagerank = None

    def _get_pagerank(self) -> dict:
        """Compute and cache PageRank scores."""
        if self._pagerank is None:
            try:
                if len(self.graph) > 0:
                    self._pagerank = nx.pagerank(self.graph, alpha=0.85, max_iter=100)
                else:
                    self._pagerank = {}
            except Exception:
                self._pagerank = {}
        return self._pagerank

    def extract_features(self, gstin: str) -> dict:
        """Extract all risk features for a single GSTIN."""
        features = {}

        # 1. Graph features
        pagerank = self._get_pagerank()
        features["pagerank_score"] = round(pagerank.get(gstin, 0), 6)
        features["in_degree"] = self.graph.in_degree(gstin) if gstin in self.graph else 0
        features["out_degree"] = self.graph.out_degree(gstin) if gstin in self.graph else 0

        # 2. Invoice features
        if not self.gstr1.empty:
            seller_inv = self.gstr1[self.gstr1["supplier_gstin"] == gstin]
            buyer_inv = self.gstr1[self.gstr1["receiver_gstin"] == gstin]
            features["total_invoices_issued"] = len(seller_inv)
            features["total_invoices_received"] = len(buyer_inv)
            features["total_outward_value"] = round(float(seller_inv["total_value"].sum()), 2)
            features["total_inward_value"] = round(float(buyer_inv["total_value"].sum()), 2)
        else:
            features["total_invoices_issued"] = 0
            features["total_invoices_received"] = 0
            features["total_outward_value"] = 0.0
            features["total_inward_value"] = 0.0

        # 3. GSTR-3B features
        if not self.gstr3b.empty:
            filings = self.gstr3b[self.gstr3b["gstin"] == gstin]
            features["filing_count"] = len(filings)

            if not filings.empty:
                total_itc = float(filings["total_itc_claimed"].sum()) if "total_itc_claimed" in filings.columns else 0
                total_sales = float(filings["total_sales_declared"].sum()) if "total_sales_declared" in filings.columns else 0
                cash_paid = float(filings["tax_paid_cash"].sum()) if "tax_paid_cash" in filings.columns else 0

                zero_cash_months = int((filings["tax_paid_cash"] == 0).sum()) if "tax_paid_cash" in filings.columns else 0

                features["total_itc_claimed"] = round(total_itc, 2)
                features["total_sales_declared"] = round(total_sales, 2)
                features["total_tax_paid_cash"] = round(cash_paid, 2)
                features["zero_cash_tax_months"] = zero_cash_months
                features["itc_to_sales_ratio"] = round(total_itc / max(total_sales, 1), 4)
            else:
                features["filing_count"] = 0
                features["total_itc_claimed"] = 0.0
                features["total_sales_declared"] = 0.0
                features["total_tax_paid_cash"] = 0.0
                features["zero_cash_tax_months"] = 0
                features["itc_to_sales_ratio"] = 0.0
        else:
            features["filing_count"] = 0
            features["total_itc_claimed"] = 0.0
            features["total_sales_declared"] = 0.0
            features["total_tax_paid_cash"] = 0.0
            features["zero_cash_tax_months"] = 0
            features["itc_to_sales_ratio"] = 0.0

        # 4. Known fraud label
        if not self.fraud_labels.empty:
            label_row = self.fraud_labels[self.fraud_labels["gstin"] == gstin]
            if not label_row.empty:
                features["is_known_fraud"] = int(label_row.iloc[0].get("is_fraud", 0))
                features["fraud_type"] = str(label_row.iloc[0].get("fraud_type", "None"))
            else:
                features["is_known_fraud"] = 0
                features["fraud_type"] = "None"
        else:
            features["is_known_fraud"] = 0
            features["fraud_type"] = "None"

        return features

    def compute_risk_score(self, gstin: str) -> dict:
        """Compute a weighted risk score for a GSTIN."""
        features = self.extract_features(gstin)

        # Weighted heuristic scoring (0.0 = safe, 1.0 = high risk)
        score = 0.0

        # Known fraud = instant critical
        if features["is_known_fraud"] == 1:
            score = 0.95
        else:
            # ITC-to-sales ratio anomaly (high ratio = risky)
            itc_ratio = features["itc_to_sales_ratio"]
            if itc_ratio > 0.9:
                score += 0.25
            elif itc_ratio > 0.5:
                score += 0.10

            # Zero cash tax months
            zero_months = features["zero_cash_tax_months"]
            if zero_months >= 3:
                score += 0.20
            elif zero_months >= 1:
                score += 0.10

            # Low PageRank + high volume = shell company behavior
            if features["pagerank_score"] < 0.005 and features["total_outward_value"] > 5_000_000:
                score += 0.25

            # High in/out degree concentration
            total_degree = features["in_degree"] + features["out_degree"]
            if total_degree > 20:
                score += 0.05

            # High outward value with few invoices (bulk fake invoicing)
            if features["total_invoices_issued"] > 0:
                avg_invoice = features["total_outward_value"] / features["total_invoices_issued"]
                if avg_invoice > 1_000_000:
                    score += 0.10

        score = min(round(score, 4), 1.0)

        # Determine risk level
        if score > 0.85:
            risk_level = "CRITICAL"
        elif score > 0.65:
            risk_level = "HIGH"
        elif score > 0.35:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "gstin": gstin,
            "risk_score": score,
            "risk_level": risk_level,
            "features": features,
        }

    def get_leaderboard(self, top_n: int = 20) -> list[dict]:
        """Get the top-N riskiest taxpayers."""
        if len(self.graph) == 0:
            return []

        all_gstins = list(self.graph.nodes())
        results = []

        for gstin in all_gstins:
            risk = self.compute_risk_score(gstin)
            results.append({
                "gstin": risk["gstin"],
                "risk_score": risk["risk_score"],
                "risk_level": risk["risk_level"],
                "total_outward_value": risk["features"]["total_outward_value"],
                "zero_cash_tax_months": risk["features"]["zero_cash_tax_months"],
                "itc_to_sales_ratio": risk["features"]["itc_to_sales_ratio"],
                "pagerank_score": risk["features"]["pagerank_score"],
            })

        results.sort(key=lambda x: x["risk_score"], reverse=True)
        return results[:top_n]
