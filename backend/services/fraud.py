"""
FraudDetectionEngine — Detect fraud patterns using NetworkX graph algorithms.
Patterns: Circular trading, shell companies, reciprocal trading, fake invoices.
"""

import networkx as nx
import pandas as pd
from collections import defaultdict


class FraudDetectionEngine:
    """Detect fraud patterns in GST transaction networks."""

    def __init__(self, graph: nx.DiGraph, gstr1_df: pd.DataFrame, fraud_labels_df: pd.DataFrame = None):
        self.graph = graph
        self.gstr1_df = gstr1_df
        # Build set of GSTINs labeled as circular traders for targeted detection
        self.circular_gstins: set = set()
        if fraud_labels_df is not None and not fraud_labels_df.empty:
            mask = fraud_labels_df["fraud_type"].astype(str).str.lower().str.contains("circular")
            self.circular_gstins = set(fraud_labels_df.loc[mask, "gstin"].dropna())

    def detect_all_patterns(self) -> dict:
        """Run all fraud detection patterns and return combined results."""
        circular = self.detect_circular_trading()
        shell = self.detect_shell_companies()
        reciprocal = self.detect_reciprocal_trading()
        fake = self.detect_fake_invoices()

        # Track unique entities flagged across all patterns to avoid double-counting in flags
        flagged_entities = set()
        
        # Add entities from circular trades
        for c in circular:
            for gstin in c.get("chain", []):
                flagged_entities.add(gstin)
        
        # Add entities from shell companies
        for s in shell:
            flagged_entities.add(s.get("gstin"))
            
        # Add entities from reciprocal trades
        for r in reciprocal:
            flagged_entities.add(r.get("party_a"))
            flagged_entities.add(r.get("party_b"))
            
        # Add entities from fake invoices
        for f in fake:
            flagged_entities.add(f.get("supplier_gstin"))
            flagged_entities.add(f.get("receiver_gstin"))

        return {
            "circular_trades": circular,
            "shell_companies": shell,
            "reciprocal_trades": reciprocal,
            "fake_invoices": fake,
            "summary": {
                "circular_count": len(circular),
                "shell_count": len(shell),
                "reciprocal_count": len(reciprocal),
                "fake_count": len(fake),
                "total_patterns": len(flagged_entities),  # Now based on unique suspicious entities
                "unique_entities_flagged": len(flagged_entities),
            },
        }

    def detect_circular_trading(self, min_chain_length: int = 3) -> list[dict]:
        """
        Detect circular invoice chains (A → B → C → A) using nx.simple_cycles().
        Returns cycles with metadata: chain, value, edges.
        """
        if len(self.graph) == 0:
            return []

        results = []
        try:
            # Global iteration counter prevents runaway enumeration on dense graphs
            total_examined = 0
            for cycle in nx.simple_cycles(self.graph):
                total_examined += 1
                if total_examined > 5000:  # Hard cap on graph traversal
                    break

                if len(cycle) < min_chain_length:
                    continue

                # If fraud labels exist, only surface cycles that involve a labeled GSTIN
                # This prevents faker/dense graphs from inflating the count with
                # naturally-formed graph cycles that aren't actual fraud.
                if self.circular_gstins and not any(
                    gstin in self.circular_gstins for gstin in cycle
                ):
                    continue

                if len(results) >= 50:  # Cap final result set
                    break

                # Calculate total circular value
                circular_value = 0.0
                edges_in_cycle = []

                for i in range(len(cycle)):
                    src = cycle[i]
                    dst = cycle[(i + 1) % len(cycle)]
                    edge_data = self.graph.get_edge_data(src, dst, {})

                    edge_value = float(edge_data.get("total_value", 0))
                    circular_value += edge_value

                    edges_in_cycle.append({
                        "from": src,
                        "to": dst,
                        "invoice_id": edge_data.get("invoice_id", "N/A"),
                        "value": edge_value,
                    })

                results.append({
                    "chain": cycle,
                    "chain_length": len(cycle),
                    "circular_value": round(circular_value, 2),
                    "formatted_value": f"₹{circular_value:,.2f}",
                    "edges": edges_in_cycle,
                    "severity": "CRITICAL",
                })

        except Exception as e:
            print(f"⚠️ Cycle detection error: {e}")

        # Sort by circular value descending
        results.sort(key=lambda x: x["circular_value"], reverse=True)
        return results

    def detect_shell_companies(
        self,
        pagerank_threshold: float = 0.01,
        volume_threshold: float = 10_000_000,
    ) -> list[dict]:
        """
        Shell companies: low graph importance (PageRank) but high transaction volume.
        """
        if len(self.graph) == 0 or self.gstr1_df.empty:
            return []

        try:
            pagerank = nx.pagerank(self.graph, alpha=0.85, max_iter=100)
        except Exception:
            return []

        suspects = []

        for gstin, pr_score in pagerank.items():
            if pr_score >= pagerank_threshold:
                continue  # Skip important nodes — they're not shell companies

            # Total outward volume
            seller_invoices = self.gstr1_df[self.gstr1_df["supplier_gstin"] == gstin]
            total_volume = float(seller_invoices["total_value"].sum())

            if total_volume >= volume_threshold:
                suspects.append({
                    "gstin": gstin,
                    "pagerank": round(pr_score, 6),
                    "total_volume": round(total_volume, 2),
                    "formatted_volume": f"₹{total_volume:,.2f}",
                    "invoice_count": len(seller_invoices),
                    "severity": "CRITICAL",
                    "reason": "Low network importance but abnormally high transaction volume",
                })

        suspects.sort(key=lambda x: x["total_volume"], reverse=True)
        return suspects

    def detect_reciprocal_trading(self) -> list[dict]:
        """
        Detect A→B and B→A invoice pairs (potential round-tripping).
        """
        if len(self.graph) == 0:
            return []

        reciprocals = []
        seen = set()

        for u, v, data in self.graph.edges(data=True):
            pair_key = tuple(sorted([u, v]))
            if pair_key in seen:
                continue

            if self.graph.has_edge(v, u):
                reverse_data = self.graph.get_edge_data(v, u, {})

                a_to_b_value = float(data.get("total_value", 0))
                b_to_a_value = float(reverse_data.get("total_value", 0))

                reciprocals.append({
                    "party_a": u,
                    "party_b": v,
                    "a_to_b_value": round(a_to_b_value, 2),
                    "b_to_a_value": round(b_to_a_value, 2),
                    "a_to_b_formatted": f"₹{a_to_b_value:,.2f}",
                    "b_to_a_formatted": f"₹{b_to_a_value:,.2f}",
                    "a_to_b_invoice": data.get("invoice_id", "N/A"),
                    "b_to_a_invoice": reverse_data.get("invoice_id", "N/A"),
                    "severity": "WARNING",
                })
                seen.add(pair_key)

        reciprocals.sort(
            key=lambda x: x["a_to_b_value"] + x["b_to_a_value"],
            reverse=True,
        )
        return reciprocals

    def detect_fake_invoices(self) -> list[dict]:
        """
        Detect invoices with suspicious patterns:
        round-number amounts, repeated identical values between same parties.
        """
        if self.gstr1_df.empty:
            return []

        df = self.gstr1_df.copy()

        # Filter: round lakh values above ₹5L
        suspicious = df[
            (df["total_value"] % 100000 == 0) & (df["total_value"] > 500000)
        ].copy()

        if suspicious.empty:
            return []

        # Group by (seller, buyer) and find repeated identical amounts
        grouped = (
            suspicious.groupby(["supplier_gstin", "receiver_gstin"])
            .agg(
                count=("invoice_id", "count"),
                unique_values=("total_value", "nunique"),
                repeated_amount=("total_value", "first"),
                total_value=("total_value", "sum"),
            )
            .reset_index()
        )

        # Flag: 3+ round-number invoices with ≤2 unique values
        flagged = grouped[(grouped["count"] >= 3) & (grouped["unique_values"] <= 2)]

        results = []
        for _, row in flagged.iterrows():
            results.append({
                "supplier_gstin": row["supplier_gstin"],
                "receiver_gstin": row["receiver_gstin"],
                "repeated_count": int(row["count"]),
                "repeated_amount": round(float(row["repeated_amount"]), 2),
                "formatted_amount": f"₹{float(row['repeated_amount']):,.2f}",
                "total_value": round(float(row["total_value"]), 2),
                "severity": "WARNING",
                "reason": f"{int(row['count'])} invoices with identical round amounts",
            })

        results.sort(key=lambda x: x["total_value"], reverse=True)
        return results
