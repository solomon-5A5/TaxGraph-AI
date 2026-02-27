"""
AlertService — Generate structured alerts from reconciliation and fraud results.
"""

from datetime import datetime


class AlertService:
    """Generate and manage alerts from analysis results."""

    def generate_alerts(self, reconciliation_mismatches: list, fraud_patterns: dict) -> list[dict]:
        """Generate alerts from mismatches and fraud patterns."""
        alerts = []
        now = datetime.utcnow().isoformat()

        # 1. Alerts from reconciliation mismatches
        for mismatch in reconciliation_mismatches:
            status = mismatch.get("status", "UNKNOWN")
            invoice_id = mismatch.get("invoice_id", "N/A")

            alert_type_map = {
                "MISSING_IN_GSTR1": "MISMATCH",
                "MISSING_IN_GSTR2B": "MISMATCH",
                "VALUE_MISMATCH": "MISMATCH",
                "TAX_MISMATCH": "MISMATCH",
            }
            alert_type = alert_type_map.get(status, "MISMATCH")

            message_map = {
                "MISSING_IN_GSTR1": f"Invoice {invoice_id} in buyer's GSTR-2B but missing from seller's GSTR-1",
                "MISSING_IN_GSTR2B": f"Invoice {invoice_id} in seller's GSTR-1 but missing from buyer's GSTR-2B",
                "VALUE_MISMATCH": f"Value mismatch of ₹{mismatch.get('value_difference', 0):,.2f} for invoice {invoice_id}",
                "TAX_MISMATCH": f"Tax amount discrepancy detected for invoice {invoice_id}",
            }

            alerts.append({
                "id": f"ALERT-RECON-{len(alerts) + 1}",
                "type": alert_type,
                "severity": mismatch.get("severity", "INFO"),
                "title": status.replace("_", " ").title(),
                "message": message_map.get(status, f"Mismatch: {status} for {invoice_id}"),
                "related_gstin": mismatch.get("supplier_gstin", "N/A"),
                "related_invoice": invoice_id,
                "created_at": now,
                "resolved": False,
            })

        # 2. Alerts from fraud patterns
        # Circular trading
        for pattern in fraud_patterns.get("circular_trades", []):
            chain_str = " → ".join(pattern.get("chain", [])[:4])
            alerts.append({
                "id": f"ALERT-FRAUD-{len(alerts) + 1}",
                "type": "FRAUD",
                "severity": "CRITICAL",
                "title": "Circular Trading Detected",
                "message": f"Circular trading ring: {chain_str} (Value: {pattern.get('formatted_value', 'N/A')})",
                "related_gstin": pattern.get("chain", ["N/A"])[0],
                "related_invoice": "N/A",
                "created_at": now,
                "resolved": False,
            })

        # Shell companies
        for pattern in fraud_patterns.get("shell_companies", []):
            alerts.append({
                "id": f"ALERT-FRAUD-{len(alerts) + 1}",
                "type": "FRAUD",
                "severity": "CRITICAL",
                "title": "Suspected Shell Company",
                "message": f"Entity {pattern.get('gstin', 'N/A')} has low importance but {pattern.get('formatted_volume', 'N/A')} volume",
                "related_gstin": pattern.get("gstin", "N/A"),
                "related_invoice": "N/A",
                "created_at": now,
                "resolved": False,
            })

        # Reciprocal trading
        for pattern in fraud_patterns.get("reciprocal_trades", []):
            alerts.append({
                "id": f"ALERT-FRAUD-{len(alerts) + 1}",
                "type": "FRAUD",
                "severity": "WARNING",
                "title": "Reciprocal Trading Detected",
                "message": (
                    f"Round-tripping: {pattern.get('party_a', 'N/A')[:12]} ↔ "
                    f"{pattern.get('party_b', 'N/A')[:12]}"
                ),
                "related_gstin": pattern.get("party_a", "N/A"),
                "related_invoice": "N/A",
                "created_at": now,
                "resolved": False,
            })

        # Sort by severity
        severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        alerts.sort(key=lambda x: severity_order.get(x["severity"], 3))

        return alerts
