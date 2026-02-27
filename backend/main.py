from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import shutil
import random
from groq import Groq
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env

app = FastAPI(title="GSTGraph AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "../data_pipeline")
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
    data_dir = os.path.join(base_dir, "../data_pipeline")
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
    Our graph database just detected a massive circular trading ring designed to manipulate Input Tax Credit (ITC).
    
    Data points:
    - Mastermind GSTIN: {mastermind}
    - Total Fake Invoice Value: ₹{total_fraud_value:,.2f}
    - Shell Companies Involved: {len(fraud_nodes)}
    
    Task: Write a highly professional, urgent 2-sentence executive summary. Explain the severity of the network and recommend immediate suspension. Do not include a list or table in your text, as we will display the data in a UI table below your summary.
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
        
        # Notice we are now returning the 'fraud_table' array too!
        return {
            "insight": insight_text, 
            "mastermind": mastermind, 
            "value": total_fraud_value,
            "fraud_table": fraud_table_data
        }
        
    except Exception as e:
        print(f"\n--- GROQ API CRASHED ---")
        print(f"Error details: {str(e)}")
        print(f"------------------------\n")
        
        mock_summary = f"CRITICAL ALERT: Graph algorithms have isolated a closed-loop recursive invoicing ring originating from {mastermind}. Immediate suspension recommended."
        return {
            "insight": mock_summary, 
            "mastermind": mastermind, 
            "value": total_fraud_value,
            "fraud_table": fraud_table_data
        }