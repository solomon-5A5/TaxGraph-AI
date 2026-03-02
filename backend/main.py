from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import shutil
import random
from groq import Groq
from dotenv import load_dotenv

# ─── New Service Imports ───
from services.ingestion import GSTIngestionService
from services.reconciliation import ReconciliationEngine
from services.fraud import FraudDetectionEngine
from services.risk import RiskScoringEngine
from services.explain import ExplainableAIService
from services.nl_query import NLQueryEngine
from services.alerts import AlertService
from services.anomaly import AnomalyDetectionService
from services.xgboost_classifier import XGBoostFraudClassifier
from services.neo4j_driver import health_check as neo4j_health_check, close_driver as neo4j_close, create_indexes
from datetime import datetime
import json

load_dotenv()  # Load variables from .env

app = FastAPI(title="GSTGraph AI API")


@app.on_event("startup")
def startup_event():
    """Initialize Neo4j connection on app startup."""
    neo4j_health_check()
    create_indexes()
    print("🚀 GSTGraph AI API started with Neo4j")


@app.on_event("shutdown")
def shutdown_event():
    """Close Neo4j connection on app shutdown."""
    neo4j_close()
    print("🔌 Neo4j connection closed")

# ─── Audit Trail ───
_audit_log = []

def _log_audit(action: str, details: str = ""):
    """Log an API action with timestamp."""
    entry = {
        "id": f"AUDIT-{len(_audit_log)+1}",
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "details": details,
    }
    _audit_log.append(entry)
    if len(_audit_log) > 500:
        _audit_log.pop(0)  # Keep last 500 entries

# ─── AI Response Cache ───
_ai_cache = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "../uploads")
    os.makedirs(data_dir, exist_ok=True) # Ensure directory exists

    paths = {
        "taxpayers": os.path.join(data_dir, "taxpayers.csv"),
        "gstr1": os.path.join(data_dir, "gstr1_invoices.csv"),
        "gstr2b": os.path.join(data_dir, "gstr2b_invoices.csv"),
        "gstr3b": os.path.join(data_dir, "gstr3b_summary.csv"),
        "fraud_labels": os.path.join(data_dir, "fraud_labels.csv"),
    }
    
    data = {}
    for key, path in paths.items():
        try:
            data[key] = pd.read_csv(path)
        except FileNotFoundError:
            data[key] = pd.DataFrame() # Return empty if not uploaded yet
            
    return data

# --- UPGRADED ALGORITHM: DFS Cycle Detection ---
def detect_circular_trading(df_gstr1, value_threshold=20000000):
    graph = {}
    if df_gstr1.empty:
        return set()
        
    for _, row in df_gstr1.iterrows():
        seller = row.get('supplier_gstin')
        buyer = row.get('receiver_gstin')
        inv_no = row.get('invoice_id')
        val = row.get('total_value', 0)
        
        if seller not in graph:
            graph[seller] = []
        graph[seller].append((buyer, inv_no, val))

    visited = set()
    rec_stack = set()
    fraud_invoices = set()
    path = []

    def dfs(node):
        visited.add(node)
        rec_stack.add(node)

        if node in graph:
            for neighbor, inv_no, val in graph[node]:
                path.append((node, neighbor, inv_no, val))
                
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    idx = len(path) - 1
                    cycle_invoices = []
                    cycle_value = 0
                    
                    while idx >= 0:
                        u, v, i_no, i_val = path[idx]
                        cycle_invoices.append(i_no)
                        cycle_value += i_val
                        if u == neighbor: 
                            break
                        idx -= 1
                    
                    if cycle_value >= value_threshold:
                        for c_inv in cycle_invoices:
                            fraud_invoices.add(c_inv)
                
                path.pop()
        rec_stack.remove(node)

    for node in list(graph.keys()):
        if node not in visited:
            dfs(node)

    return fraud_invoices

@app.get("/")
def read_root():
    return {"status": "GSTGraph AI Backend is running 🟢"}

@app.post("/api/upload")
async def upload_files(
    taxpayers: UploadFile = File(...),
    gstr1: UploadFile = File(...),
    gstr2b: UploadFile = File(...),
    gstr3b: UploadFile = File(...),
    fraud_labels: UploadFile = File(...)
):
    """Receives all 5 CSVs from the React UI drag-and-drop."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "../uploads")
    os.makedirs(data_dir, exist_ok=True)

    files_to_save = {
        "taxpayers.csv": taxpayers,
        "gstr1_invoices.csv": gstr1,
        "gstr2b_invoices.csv": gstr2b,
        "gstr3b_summary.csv": gstr3b,
        "fraud_labels.csv": fraud_labels
    }

    for filename, upload_file in files_to_save.items():
        file_path = os.path.join(data_dir, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

    _log_audit("DATA_UPLOAD", "5 CSV files uploaded via UI")
    return get_graph_data()

@app.get("/api/graph-data")
def get_graph_data():
    data = load_data()
    df_taxpayers = data["taxpayers"]
    df_gstr1 = data["gstr1"]
    df_gstr2b = data["gstr2b"]
    df_gstr3b = data["gstr3b"]
    df_labels = data["fraud_labels"]
    
    if df_taxpayers.empty or df_gstr1.empty:
        return {"nodes": [], "links": []}

    # 1. Base Graph Analytics
    suspicious_invoices = df_gstr1[df_gstr1['total_value'] > 1000000]
    fraudulent_invoice_ids = detect_circular_trading(suspicious_invoices, value_threshold=0)

    fraud_gstins = set()
    fraud_out_value = {}
    for _, row in df_gstr1.iterrows():
        if str(row['invoice_id']) in fraudulent_invoice_ids:
            seller = row['supplier_gstin']
            val = row['total_value']
            fraud_gstins.add(seller)
            fraud_gstins.add(row['receiver_gstin'])
            fraud_out_value[seller] = fraud_out_value.get(seller, 0) + val

    mastermind_gstin = max(fraud_out_value, key=fraud_out_value.get) if fraud_out_value else None

    # 2. Lookups for 3B and Fraud Labels
    dict_3b = df_gstr3b.set_index('gstin').to_dict('index') if not df_gstr3b.empty else {}
    dict_labels = df_labels.set_index('gstin').to_dict('index') if not df_labels.empty else {}
    
    # 3. Mismatch Detection (In 2B but not in 1)
    gstr1_ids = set(df_gstr1['invoice_id'].astype(str)) if not df_gstr1.empty else set()

    nodes = []
    for _, row in df_taxpayers.iterrows():
        gstin = row['gstin']
        trust = float(row.get('trust_score', random.uniform(0.1, 0.9)))
        
        # Pull data from 3B and Labels
        node_3b = dict_3b.get(gstin, {})
        cash_paid = node_3b.get('tax_paid_cash', -1)
        sales_declared = node_3b.get('total_sales_declared', 0)
        
        node_label = dict_labels.get(gstin, {})
        is_known_fraud = node_label.get('is_fraud', 0) == 1
        fraud_type = node_label.get('fraud_type', 'None')

        is_mastermind = (gstin == mastermind_gstin)
        
        # 🚨 ADVANCED RISK CALCULATION 🚨
        if is_known_fraud or gstin in fraud_gstins:
            risk = "critical"
        elif cash_paid == 0 and sales_declared > 5000000:
            # High sales but ₹0 cash paid (100% ITC utilization) = Shell Company Behavior
            risk = "high"
        else:
            risk = "warning" if trust < 0.5 else "normal"

        if is_mastermind:
            icon = "🚫"
            label_text = "🚨 MASTERMIND"
        elif risk == "critical":
            icon = "🛑"
            label_text = fraud_type if fraud_type != 'None' else "FRAUD"
        else:
            icon = "🏢"
            label_text = str(row['legal_name'])[:15] + ".."
            if risk != "critical" and row['status'] != "Active":
                icon = "🔒"

        nodes.append({
            "id": gstin,
            "label": label_text, 
            "riskLevel": risk,
            "trustScore": trust,
            "status": row['status'],
            "cashPaid": cash_paid,
            "icon": icon,
            "isCentral": is_mastermind
        })

    links = []
    for _, row in df_gstr1.iterrows():
        inv_id = str(row['invoice_id'])
        is_circular = inv_id in fraudulent_invoice_ids
        
        links.append({
            "source": row['supplier_gstin'],
            "target": row['receiver_gstin'],
            "value": 4 if is_circular else 1,
            "isRisk": is_circular,
            "isMismatched": False, # Exists in GSTR-1, so it's a declared outward supply
            "invoice_no": inv_id,
            "total_value": row['total_value']
        })
        
    # Add phantom links for fake ITC claims (In 2B but not in 1)
    if not df_gstr2b.empty:
        for _, row in df_gstr2b.iterrows():
            inv_id = str(row['invoice_id'])
            if inv_id not in gstr1_ids:
                links.append({
                    "source": row['supplier_gstin'],
                    "target": row['receiver_gstin'],
                    "value": 2,
                    "isRisk": True,
                    "isMismatched": True, # Fake ITC Claim!
                    "invoice_no": inv_id,
                    "total_value": row['total_value']
                })

    return {"nodes": nodes, "links": links}

@app.get("/api/ai-insight")
def get_ai_insight():
    data = load_data()
    df_gstr1 = data["gstr1"]
    
    if df_gstr1.empty:
        return {"insight": "Data pipeline offline. Cannot generate insights.", "fraud_table": []}

    suspicious_invoices = df_gstr1[df_gstr1['total_value'] > 1000000]
    fraudulent_invoice_ids = detect_circular_trading(suspicious_invoices, value_threshold=0)

    if not fraudulent_invoice_ids:
        return {"insight": "Graph is currently stable. No systemic circular trading detected.", "fraud_table": []}

    total_fraud_value = 0
    fraud_nodes = set()
    fraud_out_value = {}

    for _, row in df_gstr1.iterrows():
        if str(row['invoice_id']) in fraudulent_invoice_ids:
            seller = row['supplier_gstin']
            buyer = row['receiver_gstin']
            val = row['total_value']
            
            total_fraud_value += val
            fraud_nodes.add(seller)
            fraud_nodes.add(buyer)
            fraud_out_value[seller] = fraud_out_value.get(seller, 0) + val

    mastermind = max(fraud_out_value, key=fraud_out_value.get) if fraud_out_value else "Unknown"

    # 🔥 NEW: Build the structured data for the React Table!
    fraud_table_data = []
    for gstin in fraud_nodes:
        out_val = fraud_out_value.get(gstin, 0)
        role = "🚨 Mastermind" if gstin == mastermind else "🏢 Shell Node"
        
        fraud_table_data.append({
            "gstin": gstin,
            "role": role,
            "fake_outward_value": out_val,
            "formatted_value": f"₹{out_val:,.2f}"
        })
    
    # Sort the table so the Mastermind is always at the top
    fraud_table_data.sort(key=lambda x: x['fake_outward_value'], reverse=True)

    prompt = f"""
    You are an expert Goods and Services Tax (GST) Intelligence Officer in India.
    Our graph database just detected a circular trading ring designed to manipulate Input Tax Credit (ITC).
    
    EVIDENCE:
    - Mastermind GSTIN: {mastermind}
    - Total Fake Invoice Value: ₹{total_fraud_value:,.2f}
    - Shell Companies Involved: {len(fraud_nodes)}
    - Detection Method: DFS Cycle Detection + NetworkX simple_cycles()
    - Confidence: {min(95, 60 + len(fraud_nodes) * 5)}%
    
    CHAIN OF THOUGHT:
    1. Analyze the circular trading pattern and its financial impact.
    2. Assess the severity relative to typical GST fraud cases.
    3. Determine the urgency of intervention.
    
    TASK: Write a highly professional, urgent 2-sentence executive summary. Include a confidence percentage. Explain the severity and recommend immediate suspension. Do not include lists or tables.
    """

    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an expert Goods and Services Tax (GST) Intelligence Officer."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
        )
        insight_text = chat_completion.choices[0].message.content
        confidence = min(95, 60 + len(fraud_nodes) * 5)
        
        result = {
            "insight": insight_text, 
            "mastermind": mastermind, 
            "value": total_fraud_value,
            "fraud_table": fraud_table_data,
            "confidence": confidence,
            "model": "llama-3.3-70b-versatile",
            "generated_at": datetime.utcnow().isoformat(),
        }
        _ai_cache["last_insight"] = result
        _log_audit("AI_INSIGHT_GENERATED", f"Confidence: {confidence}%, Fraud Value: ₹{total_fraud_value:,.2f}")
        return result
        
    except Exception as e:
        print(f"\n--- GROQ API CRASHED ---")
        print(f"Error details: {str(e)}")
        print(f"------------------------\n")
        
        mock_summary = f"CRITICAL ALERT: Graph algorithms have isolated a closed-loop recursive invoicing ring originating from {mastermind}. Immediate suspension recommended. (Confidence: {min(95, 60 + len(fraud_nodes) * 5)}%)"
        return {
            "insight": mock_summary, 
            "mastermind": mastermind, 
            "value": total_fraud_value,
            "fraud_table": fraud_table_data,
            "confidence": min(95, 60 + len(fraud_nodes) * 5),
            "model": "fallback-mock",
            "generated_at": datetime.utcnow().isoformat(),
        }


# ═══════════════════════════════════════════════════════════════
#  NEW API v1 ENDPOINTS (Services Layer)
# ═══════════════════════════════════════════════════════════════

# Singleton service instance
_service = GSTIngestionService()
_explain_service = ExplainableAIService()
_nl_query_engine = NLQueryEngine()
_alert_service = AlertService()


def _ensure_service_loaded():
    """Load data into the service if not already loaded."""
    if not _service.has_data():
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "../uploads")
        _service.load_from_disk(data_dir)
        _service.rebuild_graph()


@app.get("/api/v1/stats")
def get_stats():
    """Dashboard statistics — computed from real data."""
    _ensure_service_loaded()

    total_invoices = len(_service.gstr1_df) + len(_service.gstr2b_df)
    active_taxpayers = len(_service.taxpayers_df[
        _service.taxpayers_df["status"] == "Active"
    ]) if not _service.taxpayers_df.empty and "status" in _service.taxpayers_df.columns else 0

    # Run reconciliation for mismatch count
    recon = ReconciliationEngine(_service.gstr1_df, _service.gstr2b_df, _service.gstr3b_df)
    recon_summary = recon.get_summary()

    # Run fraud detection for fraud count
    fraud_engine = FraudDetectionEngine(_service.gstr1_df, _service.fraud_labels_df)
    fraud_patterns = fraud_engine.detect_all_patterns()

    # Generate alerts
    mismatches = recon.get_mismatches()
    alerts = _alert_service.generate_alerts(mismatches, fraud_patterns)

    return {
        "total_invoices": total_invoices,
        "total_gstr1": len(_service.gstr1_df),
        "total_gstr2b": len(_service.gstr2b_df),
        "active_taxpayers": active_taxpayers,
        "total_taxpayers": len(_service.taxpayers_df),
        "total_mismatches": recon_summary["missing_in_gstr1"] + recon_summary["missing_in_gstr2b"] + recon_summary["value_mismatch"] + recon_summary["tax_mismatch"],
        "fraud_flags": fraud_patterns["summary"]["total_patterns"],
        "reconciliation": recon_summary,
        "fraud_summary": fraud_patterns["summary"],
        "alert_count": len(alerts),
        "critical_alerts": len([a for a in alerts if a["severity"] == "CRITICAL"]),
    }


@app.post("/api/v1/reconcile")
def run_reconciliation():
    """Run full chain reconciliation."""
    _ensure_service_loaded()
    recon = ReconciliationEngine(_service.gstr1_df, _service.gstr2b_df, _service.gstr3b_df)
    recon.full_chain_reconciliation()
    return {
        "summary": recon.get_summary(),
        "mismatches": recon.get_mismatches(),
    }


@app.get("/api/v1/reconcile/mismatches")
def get_mismatches():
    """Get all reconciliation mismatches."""
    _ensure_service_loaded()
    recon = ReconciliationEngine(_service.gstr1_df, _service.gstr2b_df, _service.gstr3b_df)
    recon.full_chain_reconciliation()
    return {
        "summary": recon.get_summary(),
        "mismatches": recon.get_mismatches(),
    }


@app.get("/api/v1/fraud/circular-trades")
def get_circular_trades():
    """Detect circular trading patterns."""
    _ensure_service_loaded()
    engine = FraudDetectionEngine(_service.gstr1_df, _service.fraud_labels_df)
    return {"circular_trades": engine.detect_circular_trading()}


@app.get("/api/v1/fraud/shell-companies")
def get_shell_companies():
    """Detect suspected shell companies."""
    _ensure_service_loaded()
    engine = FraudDetectionEngine(_service.gstr1_df, _service.fraud_labels_df)
    return {"shell_companies": engine.detect_shell_companies()}


@app.get("/api/v1/fraud/reciprocal")
def get_reciprocal_trades():
    """Detect reciprocal trading pairs."""
    _ensure_service_loaded()
    engine = FraudDetectionEngine(_service.gstr1_df, _service.fraud_labels_df)
    return {"reciprocal_trades": engine.detect_reciprocal_trading()}


@app.get("/api/v1/fraud/fake-invoices")
def get_fake_invoices():
    """Detect fake invoice patterns."""
    _ensure_service_loaded()
    engine = FraudDetectionEngine(_service.gstr1_df, _service.fraud_labels_df)
    return {"fake_invoices": engine.detect_fake_invoices()}


@app.get("/api/v1/fraud/patterns")
def get_all_fraud_patterns():
    """Get all fraud patterns combined."""
    _ensure_service_loaded()
    engine = FraudDetectionEngine(_service.gstr1_df, _service.fraud_labels_df)
    return engine.detect_all_patterns()


@app.get("/api/v1/risk/vendor/{gstin}")
def get_vendor_risk(gstin: str):
    """Get risk score for a specific vendor."""
    _ensure_service_loaded()
    engine = RiskScoringEngine(
        _service.gstr1_df, _service.gstr2b_df,
        _service.gstr3b_df, _service.fraud_labels_df
    )
    return engine.compute_risk_score(gstin)


@app.get("/api/v1/risk/leaderboard")
def get_risk_leaderboard():
    """Get top risky vendors."""
    _ensure_service_loaded()
    engine = RiskScoringEngine(
        _service.gstr1_df, _service.gstr2b_df,
        _service.gstr3b_df, _service.fraud_labels_df
    )
    return {"leaderboard": engine.get_leaderboard()}


@app.get("/api/v1/explain/mismatch/{invoice_id}")
def explain_mismatch(invoice_id: str):
    """Explain a specific mismatch."""
    _ensure_service_loaded()
    recon = ReconciliationEngine(_service.gstr1_df, _service.gstr2b_df, _service.gstr3b_df)
    recon.full_chain_reconciliation()
    mismatches = recon.get_mismatches()

    target = None
    for m in mismatches:
        if m["invoice_id"] == invoice_id:
            target = m
            break

    if not target:
        return {"error": f"Invoice {invoice_id} not found in mismatches"}

    return _explain_service.explain_mismatch(target)


@app.get("/api/v1/explain/risk/{gstin}")
def explain_risk(gstin: str):
    """Explain why a vendor has a certain risk score."""
    _ensure_service_loaded()
    risk_engine = RiskScoringEngine(
        _service.gstr1_df, _service.gstr2b_df,
        _service.gstr3b_df, _service.fraud_labels_df
    )
    risk_data = risk_engine.compute_risk_score(gstin)
    return _explain_service.explain_risk(risk_data)


@app.post("/api/v1/query")
def nl_query(body: dict):
    """Natural language query interface."""
    _ensure_service_loaded()
    question = body.get("question", "")
    if not question:
        return {"error": "No question provided"}

    return _nl_query_engine.query(
        question,
        _service.taxpayers_df,
        _service.gstr1_df,
        _service.gstr2b_df,
        _service.gstr3b_df,
        _service.fraud_labels_df,
    )


@app.get("/api/v1/alerts")
def get_alerts():
    """Get all generated alerts."""
    _ensure_service_loaded()

    recon = ReconciliationEngine(_service.gstr1_df, _service.gstr2b_df, _service.gstr3b_df)
    recon.full_chain_reconciliation()
    mismatches = recon.get_mismatches()

    fraud_engine = FraudDetectionEngine(_service.gstr1_df, _service.fraud_labels_df)
    fraud_patterns = fraud_engine.detect_all_patterns()

    alerts = _alert_service.generate_alerts(mismatches, fraud_patterns)
    return {"alerts": alerts, "total": len(alerts)}


@app.post("/api/v1/reload")
def reload_data():
    """Force reload data from disk and rebuild graph."""
    global _service
    _service = GSTIngestionService()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "../uploads")
    _service.load_from_disk(data_dir)
    _service.rebuild_graph()
    node_count = _service.get_node_count()
    edge_count = _service.get_edge_count()
    _log_audit("DATA_RELOAD", f"Nodes: {node_count}, Edges: {edge_count}")
    return {"status": "Data reloaded successfully", "nodes": node_count, "edges": edge_count}


# ═══════════════════════════════════════════════════════════════
#  ANOMALY DETECTION ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/v1/anomalies")
def get_anomalies():
    """Run statistical anomaly detection across all data."""
    _ensure_service_loaded()
    engine = AnomalyDetectionService(
        _service.gstr1_df, _service.gstr2b_df,
        _service.gstr3b_df, _service.fraud_labels_df
    )
    report = engine.get_full_anomaly_report()
    _log_audit("ANOMALY_SCAN", f"Found {report['summary']['total_anomalies']} anomalies")
    return report


@app.get("/api/v1/anomalies/invoices")
def get_invoice_anomalies():
    """Get invoices with statistically anomalous values."""
    _ensure_service_loaded()
    engine = AnomalyDetectionService(
        _service.gstr1_df, _service.gstr2b_df,
        _service.gstr3b_df, _service.fraud_labels_df
    )
    return {"anomalies": engine.detect_invoice_value_anomalies()}


@app.get("/api/v1/anomalies/vendors")
def get_vendor_anomalies():
    """Get vendors with anomalous aggregate behavior."""
    _ensure_service_loaded()
    engine = AnomalyDetectionService(
        _service.gstr1_df, _service.gstr2b_df,
        _service.gstr3b_df, _service.fraud_labels_df
    )
    return {"anomalies": engine.detect_vendor_anomalies()}


# ═══════════════════════════════════════════════════════════════
#  XGBOOST ML FRAUD CLASSIFICATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════

_xgb_classifier = None


def _get_xgb_classifier():
    """Get or create the XGBoost classifier (lazy init + auto-train)."""
    global _xgb_classifier
    _ensure_service_loaded()
    if _xgb_classifier is None:
        _xgb_classifier = XGBoostFraudClassifier(
            _service.gstr1_df, _service.gstr2b_df,
            _service.gstr3b_df, _service.fraud_labels_df,
        )
    return _xgb_classifier


@app.post("/api/v1/ml/train")
def train_xgboost():
    """Train the XGBoost fraud classifier."""
    clf = _get_xgb_classifier()
    result = clf.train()
    _log_audit("ML_TRAIN", f"XGBoost trained: {result.get('metrics', {}).get('accuracy', 'N/A')} accuracy")
    return result


@app.get("/api/v1/ml/predict/{gstin}")
def predict_fraud(gstin: str):
    """Predict fraud probability for a specific GSTIN using XGBoost."""
    clf = _get_xgb_classifier()
    prediction = clf.predict(gstin)
    _log_audit("ML_PREDICT", f"{gstin}: {prediction['fraud_probability']:.2%} fraud probability")
    return prediction


@app.get("/api/v1/ml/predict-all")
def predict_all_fraud():
    """Predict fraud probability for all taxpayers using XGBoost."""
    clf = _get_xgb_classifier()
    result = clf.predict_all()
    _log_audit("ML_PREDICT_ALL", f"Predicted {result['total_taxpayers']} taxpayers, {result['predicted_fraud']} flagged")
    return result


@app.get("/api/v1/ml/feature-importance")
def get_feature_importance():
    """Get XGBoost feature importance scores."""
    clf = _get_xgb_classifier()
    if not clf.feature_importance:
        clf.train()
    return {
        "feature_importance": clf.feature_importance,
        "metrics": clf.metrics,
    }


# ═══════════════════════════════════════════════════════════════
#  AUDIT TRAIL ENDPOINT
# ═══════════════════════════════════════════════════════════════

@app.get("/api/v1/audit-trail")
def get_audit_trail():
    """Get the audit trail of all actions."""
    return {"trail": list(reversed(_audit_log)), "total": len(_audit_log)}


# ═══════════════════════════════════════════════════════════════
#  WATCHLIST ENDPOINTS
# ═══════════════════════════════════════════════════════════════

_watchlist = set()


@app.get("/api/v1/watchlist")
def get_watchlist():
    """Get all GSTINs on the watchlist."""
    return {"watchlist": list(_watchlist), "count": len(_watchlist)}


@app.post("/api/v1/watchlist/{gstin}")
def add_to_watchlist(gstin: str):
    """Add a GSTIN to the watchlist."""
    _watchlist.add(gstin)
    _log_audit("WATCHLIST_ADD", f"Added {gstin}")
    return {"status": "added", "gstin": gstin, "count": len(_watchlist)}


@app.delete("/api/v1/watchlist/{gstin}")
def remove_from_watchlist(gstin: str):
    """Remove a GSTIN from the watchlist."""
    _watchlist.discard(gstin)
    _log_audit("WATCHLIST_REMOVE", f"Removed {gstin}")
    return {"status": "removed", "gstin": gstin, "count": len(_watchlist)}


# ═══════════════════════════════════════════════════════════════
#  EXPORT ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/v1/export/mismatches")
def export_mismatches():
    """Export reconciliation mismatches as JSON (frontend converts to CSV)."""
    _ensure_service_loaded()
    recon = ReconciliationEngine(_service.gstr1_df, _service.gstr2b_df, _service.gstr3b_df)
    recon.full_chain_reconciliation()
    mismatches = recon.get_mismatches()
    _log_audit("EXPORT_MISMATCHES", f"Exported {len(mismatches)} mismatches")
    return {"data": mismatches, "count": len(mismatches), "exported_at": datetime.utcnow().isoformat()}


@app.get("/api/v1/export/fraud-report")
def export_fraud_report():
    """Export full fraud analysis as JSON."""
    _ensure_service_loaded()
    engine = FraudDetectionEngine(_service.gstr1_df, _service.fraud_labels_df)
    patterns = engine.detect_all_patterns()
    _log_audit("EXPORT_FRAUD", f"Exported fraud report with {patterns['summary']['total_patterns']} patterns")
    return {"data": patterns, "exported_at": datetime.utcnow().isoformat()}


@app.get("/api/v1/export/risk-leaderboard")
def export_risk_leaderboard():
    """Export risk leaderboard as JSON."""
    _ensure_service_loaded()
    engine = RiskScoringEngine(
        _service.gstr1_df, _service.gstr2b_df,
        _service.gstr3b_df, _service.fraud_labels_df
    )
    lb = engine.get_leaderboard()
    _log_audit("EXPORT_RISK", f"Exported {len(lb)} risk entries")
    return {"data": lb, "count": len(lb), "exported_at": datetime.utcnow().isoformat()}


# ═══════════════════════════════════════════════════════════════
#  GSTIN SEARCH ENDPOINT
# ═══════════════════════════════════════════════════════════════

@app.get("/api/v1/search/{query}")
def search_gstin(query: str):
    """Search for GSTINs or legal names matching the query."""
    _ensure_service_loaded()
    if _service.taxpayers_df.empty:
        return {"results": []}

    q = query.upper()
    df = _service.taxpayers_df
    matches = df[
        df["gstin"].str.upper().str.contains(q, na=False) |
        df["legal_name"].str.upper().str.contains(q, na=False)
    ].head(10)

    results = []
    for _, row in matches.iterrows():
        results.append({
            "gstin": row["gstin"],
            "legal_name": row.get("legal_name", "Unknown"),
            "status": row.get("status", "Active"),
            "state_code": int(row.get("state_code", 0)),
        })

    return {"results": results, "count": len(results)}