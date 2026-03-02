"""
GSTIngestionService — Ingests GST filing data into Pandas DataFrames + Neo4j graph.
Provides validated, deduplicated data to all downstream engines.
"""

import pandas as pd
import os
from services.neo4j_driver import (
    run_write_query,
    run_read_query,
    clear_database,
    create_indexes,
    get_node_count,
    get_edge_count,
)


class GSTIngestionService:
    """Central data service holding all DataFrames + Neo4j graph."""

    def __init__(self):
        self.taxpayers_df = pd.DataFrame()
        self.gstr1_df = pd.DataFrame()
        self.gstr2b_df = pd.DataFrame()
        self.gstr3b_df = pd.DataFrame()
        self.fraud_labels_df = pd.DataFrame()

    # ──────────────────────────────────────────────
    # Public: Load from disk (backward-compatible)
    # ──────────────────────────────────────────────
    def load_from_disk(self, data_dir: str):
        """Load all CSVs from the data_pipeline directory."""
        paths = {
            "taxpayers": os.path.join(data_dir, "taxpayers.csv"),
            "gstr1": os.path.join(data_dir, "gstr1_invoices.csv"),
            "gstr2b": os.path.join(data_dir, "gstr2b_invoices.csv"),
            "gstr3b": os.path.join(data_dir, "gstr3b_summary.csv"),
            "fraud_labels": os.path.join(data_dir, "fraud_labels.csv"),
        }

        for key, path in paths.items():
            try:
                df = pd.read_csv(path)
                if key == "taxpayers":
                    self.ingest_taxpayers_df(df)
                elif key == "gstr1":
                    self.ingest_gstr1_df(df)
                elif key == "gstr2b":
                    self.ingest_gstr2b_df(df)
                elif key == "gstr3b":
                    self.ingest_gstr3b_df(df)
                elif key == "fraud_labels":
                    self.ingest_fraud_labels_df(df)
            except FileNotFoundError:
                pass  # File not uploaded yet

    # ──────────────────────────────────────────────
    # Public: Ingest from DataFrames
    # ──────────────────────────────────────────────
    def ingest_taxpayers_df(self, df: pd.DataFrame):
        """Validate and store taxpayer master data, add nodes to Neo4j."""
        if df.empty:
            return
        df = self._validate_and_dedup(df, key_cols=["gstin"])

        # Ensure trust_score exists
        if "trust_score" not in df.columns:
            df["trust_score"] = 0.5

        self.taxpayers_df = df

        # Add nodes to Neo4j graph (batch MERGE)
        for _, row in df.iterrows():
            run_write_query(
                """
                MERGE (t:Taxpayer {gstin: $gstin})
                SET t.legal_name = $legal_name,
                    t.status = $status,
                    t.trust_score = $trust_score,
                    t.state_code = $state_code
                """,
                {
                    "gstin": row["gstin"],
                    "legal_name": row.get("legal_name", "Unknown"),
                    "status": row.get("status", "Active"),
                    "trust_score": float(row.get("trust_score", 0.5)),
                    "state_code": int(row.get("state_code", 0)),
                },
            )

    def ingest_gstr1_df(self, df: pd.DataFrame):
        """Validate and store GSTR-1 outward supply data, add edges to Neo4j."""
        if df.empty:
            return
        df = self._validate_and_dedup(df, key_cols=["invoice_id"])

        # Ensure required numeric columns
        for col in ["total_value", "tax_amount"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        self.gstr1_df = df

        # Add invoice edges to Neo4j graph
        for _, row in df.iterrows():
            supplier = row.get("supplier_gstin")
            receiver = row.get("receiver_gstin")
            if pd.notna(supplier) and pd.notna(receiver):
                run_write_query(
                    """
                    MERGE (s:Taxpayer {gstin: $supplier})
                    MERGE (r:Taxpayer {gstin: $receiver})
                    MERGE (s)-[inv:INVOICE {invoice_id: $invoice_id}]->(r)
                    SET inv.total_value = $total_value,
                        inv.tax_amount = $tax_amount
                    """,
                    {
                        "supplier": supplier,
                        "receiver": receiver,
                        "invoice_id": row.get("invoice_id"),
                        "total_value": float(row.get("total_value", 0)),
                        "tax_amount": float(row.get("tax_amount", 0)),
                    },
                )

    def ingest_gstr2b_df(self, df: pd.DataFrame):
        """Validate and store GSTR-2B inward supply data."""
        if df.empty:
            return
        df = self._validate_and_dedup(df, key_cols=["invoice_id"])

        for col in ["total_value", "itc_available"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # Normalize column name: some CSVs have 'tax_amount' instead of 'itc_available'
        if "itc_available" not in df.columns and "tax_amount" in df.columns:
            df["itc_available"] = df["tax_amount"]

        self.gstr2b_df = df

    def ingest_gstr3b_df(self, df: pd.DataFrame):
        """Validate and store GSTR-3B monthly summary data."""
        if df.empty:
            return

        key_cols = ["gstin"]
        if "return_period" in df.columns:
            key_cols.append("return_period")

        df = self._validate_and_dedup(df, key_cols=key_cols)

        # Normalize column names (handle variations)
        col_map = {
            "itc_claimed": "total_itc_claimed",
            "tax_paid_cash": "tax_paid_cash",
            "total_sales_declared": "total_sales_declared",
        }
        for old_name, new_name in col_map.items():
            if old_name in df.columns and new_name not in df.columns:
                df[new_name] = df[old_name]

        for col in ["total_sales_declared", "total_itc_claimed", "tax_paid_cash"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        self.gstr3b_df = df

    def ingest_fraud_labels_df(self, df: pd.DataFrame):
        """Validate and store fraud labels."""
        if df.empty:
            return
        df = self._validate_and_dedup(df, key_cols=["gstin"])
        self.fraud_labels_df = df

    # ──────────────────────────────────────────────
    # Public: Rebuild graph from current DataFrames
    # ──────────────────────────────────────────────
    def rebuild_graph(self):
        """Rebuild the Neo4j graph from current DataFrames."""
        # Clear all existing data in Neo4j
        clear_database()
        create_indexes()

        # Add taxpayer nodes
        if not self.taxpayers_df.empty:
            for _, row in self.taxpayers_df.iterrows():
                run_write_query(
                    """
                    MERGE (t:Taxpayer {gstin: $gstin})
                    SET t.legal_name = $legal_name,
                        t.status = $status,
                        t.trust_score = $trust_score,
                        t.state_code = $state_code
                    """,
                    {
                        "gstin": row["gstin"],
                        "legal_name": row.get("legal_name", "Unknown"),
                        "status": row.get("status", "Active"),
                        "trust_score": float(row.get("trust_score", 0.5)),
                        "state_code": int(row.get("state_code", 0)),
                    },
                )

        # Add invoice edges from GSTR-1
        if not self.gstr1_df.empty:
            for _, row in self.gstr1_df.iterrows():
                supplier = row.get("supplier_gstin")
                receiver = row.get("receiver_gstin")
                if pd.notna(supplier) and pd.notna(receiver):
                    run_write_query(
                        """
                        MERGE (s:Taxpayer {gstin: $supplier})
                        MERGE (r:Taxpayer {gstin: $receiver})
                        MERGE (s)-[inv:INVOICE {invoice_id: $invoice_id}]->(r)
                        SET inv.total_value = $total_value,
                            inv.tax_amount = $tax_amount
                        """,
                        {
                            "supplier": supplier,
                            "receiver": receiver,
                            "invoice_id": row.get("invoice_id"),
                            "total_value": float(row.get("total_value", 0)),
                            "tax_amount": float(row.get("tax_amount", 0)),
                        },
                    )

        node_count = get_node_count()
        edge_count = get_edge_count()
        print(f"📊 Neo4j graph rebuilt: {node_count} nodes, {edge_count} edges")

    # ──────────────────────────────────────────────
    # Public: Get graph counts (replaces len(self.graph.nodes/edges))
    # ──────────────────────────────────────────────
    def get_node_count(self) -> int:
        """Get total number of Taxpayer nodes in Neo4j."""
        return get_node_count()

    def get_edge_count(self) -> int:
        """Get total number of INVOICE relationships in Neo4j."""
        return get_edge_count()

    # ──────────────────────────────────────────────
    # Public: Check if data is loaded
    # ──────────────────────────────────────────────
    def has_data(self) -> bool:
        """Check if any meaningful data has been loaded."""
        return not self.taxpayers_df.empty or not self.gstr1_df.empty

    # ──────────────────────────────────────────────
    # Private: Validation helpers
    # ──────────────────────────────────────────────
    def _validate_and_dedup(self, df: pd.DataFrame, key_cols: list) -> pd.DataFrame:
        """Validate schema, remove duplicates, handle missing data."""
        # Only dedup on columns that actually exist
        existing_keys = [c for c in key_cols if c in df.columns]
        if existing_keys:
            df = df.drop_duplicates(subset=existing_keys, keep="first")

        # Validate GSTIN length where applicable
        gstin_cols = [c for c in df.columns if "gstin" in c.lower()]
        for col in gstin_cols:
            df[col] = df[col].astype(str).str.strip()
            invalid = df[col].str.len() != 15
            if invalid.any():
                print(f"⚠️  {invalid.sum()} invalid GSTINs in '{col}' — removing them")
                df = df[~invalid]

        return df.reset_index(drop=True)
