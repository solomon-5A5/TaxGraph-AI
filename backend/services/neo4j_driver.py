"""
Neo4j Driver Manager — Singleton connection manager for Neo4j graph database.
Provides shared driver instance, query helpers, and health-check.
"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# ─── Module-level singleton ───
_driver = None


def get_driver():
    """Get or create the shared Neo4j driver instance."""
    global _driver
    if _driver is None:
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "neo4j")
        _driver = GraphDatabase.driver(uri, auth=(user, password))
    return _driver


def close_driver():
    """Close the Neo4j driver connection."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def run_query(cypher: str, parameters: dict = None, write: bool = False):
    """
    Execute a Cypher query and return list of record dicts.
    Use write=True for CREATE/MERGE/DELETE operations.
    """
    driver = get_driver()
    with driver.session() as session:
        if write:
            result = session.run(cypher, parameters or {})
            summary = result.consume()
            return summary
        else:
            result = session.run(cypher, parameters or {})
            return [record.data() for record in result]


def run_write_query(cypher: str, parameters: dict = None):
    """Execute a write Cypher query (CREATE/MERGE/DELETE)."""
    return run_query(cypher, parameters, write=True)


def run_read_query(cypher: str, parameters: dict = None) -> list[dict]:
    """Execute a read Cypher query and return list of record dicts."""
    return run_query(cypher, parameters, write=False)


def health_check() -> bool:
    """Verify Neo4j connection is alive."""
    try:
        driver = get_driver()
        driver.verify_connectivity()
        print("✅ Neo4j connection verified")
        return True
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
        return False


def clear_database():
    """Delete all nodes and relationships (used during rebuild)."""
    run_write_query("MATCH (n) DETACH DELETE n")
    print("🗑️  Neo4j database cleared")


def create_indexes():
    """Create indexes and constraints for optimal query performance."""
    indexes = [
        "CREATE INDEX taxpayer_gstin IF NOT EXISTS FOR (t:Taxpayer) ON (t.gstin)",
        "CREATE INDEX invoice_id IF NOT EXISTS FOR ()-[r:INVOICE]-() ON (r.invoice_id)",
    ]
    for cypher in indexes:
        try:
            run_write_query(cypher)
        except Exception as e:
            # Index may already exist or syntax may vary by Neo4j version
            print(f"⚠️  Index creation note: {e}")
    print("📇 Neo4j indexes ensured")


def get_node_count() -> int:
    """Get total number of Taxpayer nodes."""
    result = run_read_query("MATCH (t:Taxpayer) RETURN count(t) AS cnt")
    return result[0]["cnt"] if result else 0


def get_edge_count() -> int:
    """Get total number of INVOICE relationships."""
    result = run_read_query("MATCH ()-[r:INVOICE]->() RETURN count(r) AS cnt")
    return result[0]["cnt"] if result else 0
