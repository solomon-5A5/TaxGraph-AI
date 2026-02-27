"""
ReconciliationEngine — Reconcile GSTR-1 ↔ GSTR-2B ↔ GSTR-3B using Pandas joins.
Implements the multi-join chain validation logic from the system plan.
"""

import pandas as pd


class ReconciliationEngine:
    """Reconcile GST filing data using Pandas merge operations."""

    def __init__(self, gstr1_df: pd.DataFrame, gstr2b_df: pd.DataFrame, gstr3b_df: pd.DataFrame):
        self.gstr1 = gstr1_df.copy() if not gstr1_df.empty else pd.DataFrame()
        self.gstr2b = gstr2b_df.copy() if not gstr2b_df.empty else pd.DataFrame()
        self.gstr3b = gstr3b_df.copy() if not gstr3b_df.empty else pd.DataFrame()
        self._reconciled = None

    def full_chain_reconciliation(self) -> pd.DataFrame:
        """
        Multi-join chain validation:
        Invoice → GSTR-1 → GSTR-2B → GSTR-3B
        Returns a DataFrame with reconciliation status for each invoice.
        """
        if self.gstr1.empty and self.gstr2b.empty:
            return pd.DataFrame()

        # Step 1: Outer join GSTR-1 (seller side) with GSTR-2B (buyer side)
        if not self.gstr1.empty and not self.gstr2b.empty:
            reconciled = self.gstr1.merge(
                self.gstr2b,
                on="invoice_id",
                how="outer",
                suffixes=("_g1", "_g2b"),
                indicator=True,
            )
        elif not self.gstr1.empty:
            reconciled = self.gstr1.copy()
            reconciled["_merge"] = "left_only"
        else:
            reconciled = self.gstr2b.copy()
            reconciled["_merge"] = "right_only"

        # Step 2: Classify each invoice
        reconciled["status"] = reconciled.apply(self._classify_invoice, axis=1)

        # Step 3: Calculate value differences where applicable
        if "total_value_g1" in reconciled.columns and "total_value_g2b" in reconciled.columns:
            reconciled["value_difference"] = (
                reconciled["total_value_g1"].fillna(0) - reconciled["total_value_g2b"].fillna(0)
            ).abs()
        else:
            reconciled["value_difference"] = 0.0

        # Step 4: Determine the receiver GSTIN for joining with GSTR-3B
        if "receiver_gstin_g2b" in reconciled.columns:
            receiver_col = "receiver_gstin_g2b"
        elif "receiver_gstin_g1" in reconciled.columns:
            receiver_col = "receiver_gstin_g1"
        elif "receiver_gstin" in reconciled.columns:
            receiver_col = "receiver_gstin"
        else:
            receiver_col = None

        # Step 5: Join with GSTR-3B to check ITC claims
        if receiver_col and not self.gstr3b.empty:
            # Aggregate GSTR-3B per GSTIN (sum across return periods)
            gstr3b_agg = self.gstr3b.groupby("gstin").agg({
                "total_sales_declared": "sum",
                "total_itc_claimed": "sum",
                "tax_paid_cash": "sum",
            }).reset_index()

            reconciled = reconciled.merge(
                gstr3b_agg,
                left_on=receiver_col,
                right_on="gstin",
                how="left",
                suffixes=("", "_3b"),
            )

        # Step 6: Compute ITC overclaim flag
        if "total_itc_claimed" in reconciled.columns:
            # Get total eligible ITC per receiver
            itc_col = "itc_available" if "itc_available" in reconciled.columns else None
            if itc_col is None:
                itc_col = "itc_available_g2b" if "itc_available_g2b" in reconciled.columns else None

            if itc_col:
                reconciled["itc_overclaimed"] = (
                    reconciled["total_itc_claimed"] > reconciled[itc_col] * 1.05
                )
            else:
                reconciled["itc_overclaimed"] = False
        else:
            reconciled["itc_overclaimed"] = False

        self._reconciled = reconciled
        return reconciled

    def get_reconciled(self) -> pd.DataFrame:
        """Get the reconciled DataFrame, running reconciliation if needed."""
        if self._reconciled is None:
            return self.full_chain_reconciliation()
        return self._reconciled

    def get_summary(self) -> dict:
        """Get reconciliation summary statistics."""
        reconciled = self.get_reconciled()
        if reconciled.empty:
            return {
                "total_invoices": 0,
                "fully_reconciled": 0,
                "missing_in_gstr1": 0,
                "missing_in_gstr2b": 0,
                "value_mismatch": 0,
                "tax_mismatch": 0,
                "itc_overclaimed_count": 0,
                "reconciliation_rate": 0.0,
            }

        total = len(reconciled)
        status_counts = reconciled["status"].value_counts().to_dict()

        fully = status_counts.get("FULLY_RECONCILED", 0)

        return {
            "total_invoices": total,
            "fully_reconciled": fully,
            "missing_in_gstr1": status_counts.get("MISSING_IN_GSTR1", 0),
            "missing_in_gstr2b": status_counts.get("MISSING_IN_GSTR2B", 0),
            "value_mismatch": status_counts.get("VALUE_MISMATCH", 0),
            "tax_mismatch": status_counts.get("TAX_MISMATCH", 0),
            "itc_overclaimed_count": int(reconciled["itc_overclaimed"].sum()) if "itc_overclaimed" in reconciled.columns else 0,
            "reconciliation_rate": round((fully / total * 100) if total > 0 else 0, 1),
        }

    def get_mismatches(self) -> list[dict]:
        """Get all mismatches as a list of structured dicts."""
        reconciled = self.get_reconciled()
        if reconciled.empty:
            return []

        mismatches = reconciled[reconciled["status"] != "FULLY_RECONCILED"]
        results = []

        for _, row in mismatches.iterrows():
            # Determine the invoice_id
            inv_id = row.get("invoice_id", "N/A")

            # Determine supplier and receiver
            supplier = (
                row.get("supplier_gstin_g1")
                or row.get("supplier_gstin_g2b")
                or row.get("supplier_gstin", "N/A")
            )
            receiver = (
                row.get("receiver_gstin_g1")
                or row.get("receiver_gstin_g2b")
                or row.get("receiver_gstin", "N/A")
            )

            # Determine values
            g1_value = row.get("total_value_g1", row.get("total_value", 0))
            g2b_value = row.get("total_value_g2b", 0)

            # Severity based on value difference
            diff = abs(float(g1_value or 0) - float(g2b_value or 0))
            status = row.get("status", "UNKNOWN")

            if status in ("MISSING_IN_GSTR1", "MISSING_IN_GSTR2B"):
                severity = "CRITICAL"
            elif diff > 100000:
                severity = "CRITICAL"
            elif diff > 10000:
                severity = "WARNING"
            else:
                severity = "INFO"

            results.append({
                "invoice_id": str(inv_id),
                "supplier_gstin": str(supplier) if pd.notna(supplier) else "N/A",
                "receiver_gstin": str(receiver) if pd.notna(receiver) else "N/A",
                "status": status,
                "severity": severity,
                "gstr1_value": round(float(g1_value or 0), 2),
                "gstr2b_value": round(float(g2b_value or 0), 2),
                "value_difference": round(diff, 2),
                "itc_overclaimed": bool(row.get("itc_overclaimed", False)),
            })

        # Sort by severity: CRITICAL first
        severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        results.sort(key=lambda x: severity_order.get(x["severity"], 3))

        return results

    def _classify_invoice(self, row) -> str:
        """Classify invoice reconciliation status."""
        merge_status = row.get("_merge", "both")

        if merge_status == "right_only":
            return "MISSING_IN_GSTR1"
        if merge_status == "left_only":
            return "MISSING_IN_GSTR2B"

        # Both exist — check for value mismatches
        g1_val = row.get("total_value_g1", row.get("total_value", 0))
        g2b_val = row.get("total_value_g2b", 0)

        if pd.notna(g1_val) and pd.notna(g2b_val):
            val_diff = abs(float(g1_val) - float(g2b_val))
            if val_diff > 1.0:
                return "VALUE_MISMATCH"

        # Check tax mismatch
        tax_g1 = row.get("tax_amount_g1", row.get("tax_amount", 0))
        itc_g2b = row.get("itc_available_g2b", row.get("itc_available", 0))

        if pd.notna(tax_g1) and pd.notna(itc_g2b):
            tax_diff = abs(float(tax_g1 or 0) - float(itc_g2b or 0))
            if tax_diff > 1.0:
                return "TAX_MISMATCH"

        return "FULLY_RECONCILED"
