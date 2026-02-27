"""
AnomalyDetectionService — Statistical anomaly detection using z-scores and IQR
for invoice values, ITC ratios, and filing patterns.
"""

import pandas as pd
import numpy as np
from collections import defaultdict


class AnomalyDetectionService:
    """Detect statistical anomalies in GST filing data."""

    def __init__(self, gstr1_df: pd.DataFrame, gstr2b_df: pd.DataFrame,
                 gstr3b_df: pd.DataFrame, fraud_labels_df: pd.DataFrame):
        self.gstr1 = gstr1_df
        self.gstr2b = gstr2b_df
        self.gstr3b = gstr3b_df
        self.fraud_labels = fraud_labels_df

    def detect_invoice_value_anomalies(self, z_threshold: float = 2.5) -> list[dict]:
        """Detect invoices with statistically anomalous values using z-score."""
        if self.gstr1.empty or "total_value" not in self.gstr1.columns:
            return []

        values = self.gstr1["total_value"].dropna().astype(float)
        if len(values) < 5:
            return []

        mean_val = values.mean()
        std_val = values.std()
        if std_val == 0:
            return []

        self.gstr1["z_score"] = (self.gstr1["total_value"].astype(float) - mean_val) / std_val

        anomalies = self.gstr1[self.gstr1["z_score"].abs() > z_threshold].copy()

        results = []
        for _, row in anomalies.iterrows():
            z = float(row["z_score"])
            results.append({
                "invoice_id": str(row.get("invoice_id", "N/A")),
                "supplier_gstin": str(row.get("supplier_gstin", "N/A")),
                "receiver_gstin": str(row.get("receiver_gstin", "N/A")),
                "total_value": round(float(row.get("total_value", 0)), 2),
                "z_score": round(z, 3),
                "anomaly_direction": "UNUSUALLY_HIGH" if z > 0 else "UNUSUALLY_LOW",
                "confidence": round(min(abs(z) / 5.0, 1.0), 3),  # 0-1 confidence
                "severity": "CRITICAL" if abs(z) > 4 else "WARNING" if abs(z) > 3 else "INFO",
            })

        results.sort(key=lambda x: abs(x["z_score"]), reverse=True)
        return results

    def detect_vendor_anomalies(self) -> list[dict]:
        """Detect vendors with anomalous behavior using IQR on aggregate metrics."""
        if self.gstr1.empty:
            return []

        # Aggregate per vendor
        vendor_stats = self.gstr1.groupby("supplier_gstin").agg(
            total_volume=("total_value", "sum"),
            invoice_count=("invoice_id", "count"),
            avg_invoice=("total_value", "mean"),
            max_invoice=("total_value", "max"),
        ).reset_index()

        if len(vendor_stats) < 5:
            return []

        results = []
        for metric in ["total_volume", "avg_invoice"]:
            q1 = vendor_stats[metric].quantile(0.25)
            q3 = vendor_stats[metric].quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue

            upper_fence = q3 + 1.5 * iqr
            lower_fence = q1 - 1.5 * iqr

            outliers = vendor_stats[
                (vendor_stats[metric] > upper_fence) | (vendor_stats[metric] < lower_fence)
            ]

            for _, row in outliers.iterrows():
                val = float(row[metric])
                # Calculate how far outside the fence
                if val > upper_fence:
                    deviation = (val - upper_fence) / iqr
                    direction = "ABOVE_UPPER_FENCE"
                else:
                    deviation = (lower_fence - val) / iqr
                    direction = "BELOW_LOWER_FENCE"

                confidence = round(min(deviation / 3.0, 1.0), 3)

                results.append({
                    "gstin": row["supplier_gstin"],
                    "metric": metric,
                    "value": round(val, 2),
                    "formatted_value": f"₹{val:,.2f}",
                    "upper_fence": round(upper_fence, 2),
                    "lower_fence": round(lower_fence, 2),
                    "direction": direction,
                    "iqr_deviation": round(deviation, 3),
                    "confidence": confidence,
                    "invoice_count": int(row["invoice_count"]),
                    "severity": "CRITICAL" if confidence > 0.8 else "WARNING" if confidence > 0.5 else "INFO",
                })

        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results

    def detect_itc_ratio_anomalies(self) -> list[dict]:
        """Detect vendors with anomalous ITC-to-sales ratios."""
        if self.gstr3b.empty:
            return []

        df = self.gstr3b.copy()

        # Aggregate per GSTIN
        itc_col = "total_itc_claimed" if "total_itc_claimed" in df.columns else "itc_claimed"
        sales_col = "total_sales_declared"

        if itc_col not in df.columns or sales_col not in df.columns:
            return []

        agg = df.groupby("gstin").agg(
            total_itc=(itc_col, "sum"),
            total_sales=(sales_col, "sum"),
        ).reset_index()

        agg["itc_ratio"] = agg["total_itc"] / agg["total_sales"].clip(lower=1)

        ratios = agg["itc_ratio"].dropna()
        if len(ratios) < 5:
            return []

        mean_ratio = ratios.mean()
        std_ratio = ratios.std()
        if std_ratio == 0:
            return []

        results = []
        for _, row in agg.iterrows():
            z = (row["itc_ratio"] - mean_ratio) / std_ratio
            if abs(z) < 2.0:
                continue

            confidence = round(min(abs(z) / 5.0, 1.0), 3)

            results.append({
                "gstin": row["gstin"],
                "itc_ratio": round(float(row["itc_ratio"]), 4),
                "total_itc": round(float(row["total_itc"]), 2),
                "total_sales": round(float(row["total_sales"]), 2),
                "z_score": round(z, 3),
                "confidence": confidence,
                "severity": "CRITICAL" if row["itc_ratio"] > 0.95 else "WARNING" if row["itc_ratio"] > 0.7 else "INFO",
                "reason": f"ITC/Sales ratio of {row['itc_ratio']:.2%} is {abs(z):.1f}σ from mean ({mean_ratio:.2%})",
            })

        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results

    def get_full_anomaly_report(self) -> dict:
        """Run all anomaly detection methods and return combined report."""
        invoice_anomalies = self.detect_invoice_value_anomalies()
        vendor_anomalies = self.detect_vendor_anomalies()
        itc_anomalies = self.detect_itc_ratio_anomalies()

        # Collect unique flagged entities
        flagged = set()
        for a in invoice_anomalies:
            flagged.add(a.get("supplier_gstin"))
        for a in vendor_anomalies:
            flagged.add(a.get("gstin"))
        for a in itc_anomalies:
            flagged.add(a.get("gstin"))

        return {
            "invoice_anomalies": invoice_anomalies[:50],
            "vendor_anomalies": vendor_anomalies[:50],
            "itc_anomalies": itc_anomalies[:50],
            "summary": {
                "invoice_anomaly_count": len(invoice_anomalies),
                "vendor_anomaly_count": len(vendor_anomalies),
                "itc_anomaly_count": len(itc_anomalies),
                "total_anomalies": len(invoice_anomalies) + len(vendor_anomalies) + len(itc_anomalies),
                "unique_entities_flagged": len(flagged),
            },
        }
