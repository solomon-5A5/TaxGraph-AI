"""
FraudDetectionEngine — Detect fraud patterns using Neo4j graph + Cypher queries.
Patterns: Circular trading, shell companies, reciprocal trading, fake invoices.
"""

import networkx as nx
import pandas as pd
from collections import defaultdict
from services.neo4j_driver import run_read_query


class FraudDetectionEngine:
    """Detect fraud patterns in GST transaction networks via Neo4j."""

    def __init__(self, gstr1_df: pd.DataFrame, fraud_labels_df: pd.DataFrame = None):
        self.gstr1_df = gstr1_df
        # Build set of GSTINs labeled as circular traders for targeted detection
        self.circular_gstins: set = set()
        if fraud_labels_df is not None and not fraud_labels_df.empty:
            mask = fraud_labels_df["fraud_type"].astype(str).str.lower().str.contains("circular")
            self.circular_gstins = set(fraud_labels_df.loc[mask, "gstin"].dropna())

    def _get_graph_size(self) -> int:
        """Get the number of Taxpayer nodes in Neo4j."""
        result = run_read_query("MATCH (t:Taxpayer) RETURN count(t) AS cnt")
        return result[0]["cnt"] if result else 0

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
                "total_patterns": len(flagged_entities),
                "unique_entities_flagged": len(flagged_entities),
            },
        }

    def detect_circular_trading(self, min_chain_length: int = 3) -> list[dict]:
        """
        Detect circular invoice chains (A → B → C → A) using Neo4j Cypher.
        Returns cycles with metadata: chain, value, edges.
        """
        if self._get_graph_size() == 0:
            return []

        # Use Cypher to find cycles of length 3 to 6
        # We query for variable-length paths that return to the start node
        results = []

        for cycle_len in range(min_chain_length, 7):
            if len(results) >= 50:
                break

            cypher = f"""
                MATCH path = (start:Taxpayer)-[:INVOICE*{cycle_len}]->(start)
                WITH nodes(path) AS cycle_nodes, relationships(path) AS rels
                LIMIT 200
                RETURN
                    [n IN cycle_nodes | n.gstin] AS chain,
                    [r IN rels | {{
                        invoice_id: r.invoice_id,
                        total_value: r.total_value,
                        from_gstin: startNode(r).gstin,
                        to_gstin: endNode(r).gstin
                    }}] AS edges
            """

            try:
                records = run_read_query(cypher)
            except Exception as e:
                print(f"⚠️ Cycle detection error (length {cycle_len}): {e}")
                continue

            for record in records:
                if len(results) >= 50:
                    break

                chain = record["chain"][:-1]  # Remove duplicate start node at end
                edges_data = record["edges"]

                # If fraud labels exist, only surface cycles that involve a labeled GSTIN
                if self.circular_gstins and not any(
                    gstin in self.circular_gstins for gstin in chain
                ):
                    continue

                # Calculate total circular value
                circular_value = sum(float(e.get("total_value", 0)) for e in edges_data)

                edges_in_cycle = []
                for e in edges_data:
                    edges_in_cycle.append({
                        "from": e.get("from_gstin", "N/A"),
                        "to": e.get("to_gstin", "N/A"),
                        "invoice_id": e.get("invoice_id", "N/A"),
                        "value": float(e.get("total_value", 0)),
                    })

                results.append({
                    "chain": chain,
                    "chain_length": len(chain),
                    "circular_value": round(circular_value, 2),
                    "formatted_value": f"₹{circular_value:,.2f}",
                    "edges": edges_in_cycle,
                    "severity": "CRITICAL",
                })

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
        Uses NetworkX-based PageRank on adjacency fetched from Neo4j.
        """
        if self._get_graph_size() == 0 or self.gstr1_df.empty:
            return []

        # Compute PageRank via NetworkX on data fetched from Neo4j
        pagerank = self._compute_pagerank()
        if not pagerank:
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
        Detect A→B and B→A invoice pairs (potential round-tripping) via Cypher.
        """
        if self._get_graph_size() == 0:
            return []

        # Cypher: find all bidirectional invoice relationships
        cypher = """
            MATCH (a:Taxpayer)-[r1:INVOICE]->(b:Taxpayer)-[r2:INVOICE]->(a)
            WHERE elementId(a) < elementId(b)
            RETURN a.gstin AS party_a, b.gstin AS party_b,
                   r1.total_value AS a_to_b_value,
                   r2.total_value AS b_to_a_value,
                   r1.invoice_id AS a_to_b_invoice,
                   r2.invoice_id AS b_to_a_invoice
        """

        try:
            records = run_read_query(cypher)
        except Exception as e:
            print(f"⚠️ Reciprocal trading detection error: {e}")
            return []

        reciprocals = []
        for record in records:
            a_to_b = float(record.get("a_to_b_value", 0))
            b_to_a = float(record.get("b_to_a_value", 0))

            reciprocals.append({
                "party_a": record["party_a"],
                "party_b": record["party_b"],
                "a_to_b_value": round(a_to_b, 2),
                "b_to_a_value": round(b_to_a, 2),
                "a_to_b_formatted": f"₹{a_to_b:,.2f}",
                "b_to_a_formatted": f"₹{b_to_a:,.2f}",
                "a_to_b_invoice": record.get("a_to_b_invoice", "N/A"),
                "b_to_a_invoice": record.get("b_to_a_invoice", "N/A"),
                "severity": "WARNING",
            })

        reciprocals.sort(
            key=lambda x: x["a_to_b_value"] + x["b_to_a_value"],
            reverse=True,
        )
        return reciprocals

    def detect_fake_invoices(self) -> list[dict]:
        """
        Detect invoices with suspicious patterns:
        round-number amounts, repeated identical values between same parties.
        (Pure DataFrame logic — unchanged)
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

    # ──────────────────────────────────────────────
    # Private: PageRank via Neo4j → NetworkX fallback
    # ──────────────────────────────────────────────
    def _compute_pagerank(self) -> dict:
        """
        Compute PageRank by fetching adjacency from Neo4j and running NetworkX.
        This avoids requiring the Neo4j GDS plugin.
        """
        try:
            # Fetch all edges from Neo4j
            edges = run_read_query(
                "MATCH (a:Taxpayer)-[r:INVOICE]->(b:Taxpayer) RETURN a.gstin AS src, b.gstin AS dst"
            )
            if not edges:
                return {}

            # Build a lightweight in-memory graph for PageRank only
            G = nx.DiGraph()
            for edge in edges:
                G.add_edge(edge["src"], edge["dst"])

            # Also add isolated nodes
            nodes = run_read_query("MATCH (t:Taxpayer) RETURN t.gstin AS gstin")
            for node in nodes:
                G.add_node(node["gstin"])

            return nx.pagerank(G, alpha=0.85, max_iter=100)
        except Exception as e:
            print(f"⚠️ PageRank computation error: {e}")
            return {}
