from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os

app = FastAPI(title="GSTGraph AI API")

# --- CORS CONFIGURATION ---
# This allows your React frontend (port 5173) to talk to this Python backend (port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, change this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- HELPER TO LOAD DATA ---
def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level and into data_pipeline
    taxpayer_path = os.path.join(base_dir, "../data_pipeline/taxpayers.csv")
    invoice_path = os.path.join(base_dir, "../data_pipeline/invoices_gstr1.csv")
    
    try:
        df_taxpayers = pd.read_csv(taxpayer_path)
        df_invoices = pd.read_csv(invoice_path)
        return df_taxpayers, df_invoices
    except FileNotFoundError:
        print("⚠️ Data files not found. Did you run generate_data.py?")
        return pd.DataFrame(), pd.DataFrame()

@app.get("/")
def read_root():
    return {"status": "GSTGraph AI Backend is running 🟢"}

@app.get("/api/graph-data")
def get_graph_data():
    """
    Reads the CSVs and transforms them into the exact {nodes: [], links: []} 
    format required by our D3.js frontend.
    """
    df_taxpayers, df_invoices = load_data()
    
    if df_taxpayers.empty or df_invoices.empty:
        return {"nodes": [], "links": []}

    # 1. PROCESS NODES (Taxpayers)
    nodes = []
    for _, row in df_taxpayers.iterrows():
        trust = float(row['trust_score'])
        
        # Determine risk level based on trust score
        if trust < 0.3:
            risk = "critical"
        elif trust < 0.6:
            risk = "warning"
        else:
            risk = "normal"

        # Check if they are suspended
        icon = "🚫" if row['status'] != "Active" else "🏢"

        nodes.append({
            "id": row['gstin'],
            # Truncate very long names for the graph UI
            "label": str(row['legal_name'])[:15] + "..", 
            "riskLevel": risk,
            "trustScore": trust,
            "status": row['status'],
            "icon": icon
        })

    # 2. PROCESS LINKS (Invoices)
    links = []
    for _, row in df_invoices.iterrows():
        # Check if this invoice is part of the fraud ring we injected!
        invoice_no = str(row['invoice_no'])
        is_fraud = "FRAUD-RING" in invoice_no
        
        links.append({
            "source": row['seller_gstin'],
            "target": row['buyer_gstin'],
            "value": 3 if is_fraud else 1, # Make fraud lines thicker
            "isRisk": is_fraud,
            "invoice_no": invoice_no,
            "total_value": row['total_value']
        })

    return {"nodes": nodes, "links": links}