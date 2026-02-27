import pandas as pd
import random
from faker import Faker
from datetime import datetime, timedelta
import os

fake = Faker('en_IN')

# --- CONFIGURATION ---
NUM_TAXPAYERS = 50
NUM_INVOICES = 300
STATES = [27, 29, 7, 33] # MH, KA, DL, TN

def generate_gstin(state_code):
    pan = fake.bothify(text='?????####?')
    return f"{state_code:02d}{pan}1Z{fake.lexify(text='?')}"

def build_dataset():
    print("🚀 Generating GSTGraph AI Synthetic Data...")
    
    taxpayers = []
    for _ in range(NUM_TAXPAYERS):
        state = random.choice(STATES)
        taxpayers.append({
            "gstin": generate_gstin(state),
            "legal_name": fake.company(),
            "state_code": state,
            "status": random.choices(['Active', 'Suspended', 'Cancelled'], weights=[90, 8, 2])[0],
            "trust_score": round(random.uniform(0.1, 0.99), 2)
        })
    df_taxpayers = pd.DataFrame(taxpayers)
    
    invoices = []
    start_date = datetime(2026, 1, 1)
    
    for i in range(NUM_INVOICES):
        seller = random.choice(taxpayers)
        buyer = random.choice(taxpayers)
        while buyer['gstin'] == seller['gstin']:
            buyer = random.choice(taxpayers)
            
        taxable_value = round(random.uniform(10000, 500000), 2)
        invoices.append({
            "invoice_no": f"INV-{2026}-{1000+i}",
            "seller_gstin": seller['gstin'],
            "buyer_gstin": buyer['gstin'],
            "total_value": round(taxable_value * 1.18, 2)
        })

    # 🚨 INJECT FRAUD RING 🚨
    ring_nodes = [taxpayers[0], taxpayers[1], taxpayers[2], taxpayers[3]]
    fraud_value = 8500000.00
    
    for i in range(len(ring_nodes)):
        seller = ring_nodes[i]
        buyer = ring_nodes[(i + 1) % len(ring_nodes)]
        invoices.append({
            "invoice_no": f"FRAUD-RING-{100+i}",
            "seller_gstin": seller['gstin'],
            "buyer_gstin": buyer['gstin'],
            "total_value": fraud_value * 1.18
        })

    df_invoices = pd.DataFrame(invoices)
    
    # Save exactly where the FastAPI backend is looking
    base_dir = os.path.dirname(os.path.abspath(__file__))
    df_taxpayers.to_csv(os.path.join(base_dir, "taxpayers.csv"), index=False)
    df_invoices.to_csv(os.path.join(base_dir, "invoices_gstr1.csv"), index=False)
    print("✅ Successfully created CSVs in the data_pipeline folder!")

if __name__ == "__main__":
    build_dataset()