import pandas as pd
import random
import string
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import os

fake = Faker("en_IN")
random.seed(42)

# Create data folder if not exists
os.makedirs("data", exist_ok=True)

# -----------------------------
# CONFIG
# -----------------------------
NUM_TAXPAYERS = 500
NUM_INVOICES = 8000
MONTHS = 6

# -----------------------------
# GSTIN Generator
# -----------------------------
def generate_gstin():
    state_code = str(random.randint(1, 37)).zfill(2)
    pan = ''.join(random.choices(string.ascii_uppercase, k=5)) + \
          ''.join(random.choices(string.digits, k=4)) + \
          random.choice(string.ascii_uppercase)
    return state_code + pan + "1Z" + random.choice(string.ascii_uppercase)

# -----------------------------
# 1️⃣ TAXPAYERS
# -----------------------------
taxpayers = []

for _ in range(NUM_TAXPAYERS):
    taxpayers.append({
        "gstin": generate_gstin(),
        "legal_name": fake.company(),
        "trade_name": fake.company_suffix(),
        "state_code": random.randint(1, 37),
        "registration_date": fake.date_between(start_date='-5y', end_date='-1y'),
        "status": random.choice(["Active"]*8 + ["Suspended"]*1 + ["Cancelled"]*1),
        "annual_turnover": random.randint(5000000, 500000000)
    })

taxpayer_df = pd.DataFrame(taxpayers)
taxpayer_df.to_csv("data/taxpayers.csv", index=False)

gstin_list = taxpayer_df["gstin"].tolist()

# -----------------------------
# 2️⃣ GSTR1 INVOICES
# -----------------------------
invoices = []

for i in range(NUM_INVOICES):
    seller = random.choice(gstin_list)
    buyer = random.choice([g for g in gstin_list if g != seller])

    taxable_value = random.randint(10000, 1000000)
    igst = round(taxable_value * 0.18, 2)

    invoice_date = datetime.now() - timedelta(days=random.randint(0, 180))

    invoices.append({
        "invoice_no": f"INV-{i+1}",
        "seller_gstin": seller,
        "buyer_gstin": buyer,
        "invoice_date": invoice_date.date(),
        "taxable_value": taxable_value,
        "cgst": 0,
        "sgst": 0,
        "igst": igst,
        "total_tax": igst
    })

gstr1_df = pd.DataFrame(invoices)
gstr1_df.to_csv("data/gstr1_invoices.csv", index=False)

# -----------------------------
# 3️⃣ GSTR2B (Inject Mismatches)
# -----------------------------
gstr2b = []

for row in invoices:
    # 10% mismatch
    if random.random() < 0.1:
        auto_tax = row["total_tax"] * random.uniform(0.8, 0.95)
    else:
        auto_tax = row["total_tax"]

    gstr2b.append({
        "invoice_no": row["invoice_no"],
        "buyer_gstin": row["buyer_gstin"],
        "period": "2025-01",
        "auto_tax": round(auto_tax, 2),
        "auto_value": row["taxable_value"]
    })

gstr2b_df = pd.DataFrame(gstr2b)
gstr2b_df.to_csv("data/gstr2b_invoices.csv", index=False)

# -----------------------------
# 4️⃣ GSTR3B SUMMARY
# -----------------------------
gstr3b = []

for gstin in gstin_list:
    for month in range(MONTHS):
        itc_claimed = random.randint(10000, 2000000)
        total_paid = itc_claimed + random.randint(-50000, 50000)

        filing_delay = random.choice([0]*7 + [random.randint(1,30)])

        gstr3b.append({
            "gstin": gstin,
            "period": f"2025-0{month+1}",
            "itc_claimed": itc_claimed,
            "total_tax_paid": total_paid,
            "filing_date": datetime.now().date(),
            "due_date": (datetime.now() - timedelta(days=filing_delay)).date()
        })

gstr3b_df = pd.DataFrame(gstr3b)
gstr3b_df.to_csv("data/gstr3b_summary.csv", index=False)

# -----------------------------
# 5️⃣ FRAUD LABELS
# -----------------------------
fraud_labels = []

for gstin in gstin_list:
    label = 1 if random.random() < 0.15 else 0  # 15% fraud
    fraud_labels.append({
        "gstin": gstin,
        "label": label
    })

fraud_df = pd.DataFrame(fraud_labels)
fraud_df.to_csv("data/fraud_labels.csv", index=False)

print("✅ All datasets generated successfully in /data folder!")