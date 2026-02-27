import pandas as pd
import random
from faker import Faker
import os

fake = Faker()

# Create output folders
os.makedirs("clean_data", exist_ok=True)
os.makedirs("fraud_data", exist_ok=True)

# -----------------------------
# 1. Generate Taxpayers
# -----------------------------
def generate_gstin():
    return str(random.randint(10, 99)) + fake.bothify(text='?????#####?Z#')

num_taxpayers = 60
taxpayers = []

for _ in range(num_taxpayers):
    taxpayers.append({
        "gstin": generate_gstin(),
        "legal_name": fake.company(),
        "registration_date": fake.date_between(start_date='-5y', end_date='today'),
        "status": "Active"
    })

taxpayers_df = pd.DataFrame(taxpayers)
gstins = taxpayers_df["gstin"].tolist()

# Save taxpayers
taxpayers_df.to_csv("clean_data/taxpayers.csv", index=False)
taxpayers_df.to_csv("fraud_data/taxpayers.csv", index=False)

# -----------------------------
# 2. Generate GSTR1 (Sales)
# -----------------------------
def generate_gstr1(mismatch=False, circular=False):

    invoices = []
    mismatch_invoice_ids = set()

    for i in range(100):
        supplier = random.choice(gstins)
        receiver = random.choice(gstins)

        while supplier == receiver:
            receiver = random.choice(gstins)

        total = round(random.uniform(10000, 100000), 2)
        tax = round(total * 0.18, 2)

        invoice_id = f"INV{i+1}"

        if mismatch and i < 10:
            tax = round(tax * 1.5, 2)
            mismatch_invoice_ids.add(invoice_id)

        invoices.append({
            "invoice_id": invoice_id,
            "supplier_gstin": supplier,
            "receiver_gstin": receiver,
            "invoice_date": fake.date_this_year(),
            "total_value": total,
            "tax_amount": tax
        })

    # Add 3 circular loops
    if circular:
        for loop in range(3):
            a, b, c = random.sample(gstins, 3)
            circular_data = [
                (f"CIR{loop*3+1}", a, b),
                (f"CIR{loop*3+2}", b, c),
                (f"CIR{loop*3+3}", c, a)
            ]
            for inv_id, s, r in circular_data:
                total = 50000
                invoices.append({
                    "invoice_id": inv_id,
                    "supplier_gstin": s,
                    "receiver_gstin": r,
                    "invoice_date": fake.date_this_year(),
                    "total_value": total,
                    "tax_amount": round(total * 0.18, 2)
                })

    return pd.DataFrame(invoices), mismatch_invoice_ids

# Generate Clean & Fraud GSTR1
clean_gstr1, _ = generate_gstr1()
fraud_gstr1, mismatch_ids = generate_gstr1(mismatch=True, circular=True)

clean_gstr1.to_csv("clean_data/gstr1_invoices.csv", index=False)
fraud_gstr1.to_csv("fraud_data/gstr1_invoices.csv", index=False)

# -----------------------------
# 3. Generate GSTR2B (Purchases)
# -----------------------------
def generate_gstr2b(gstr1_df, mismatch_ids=None):

    records = []

    for _, row in gstr1_df.iterrows():

        itc = row["tax_amount"]

        # Fix mismatch in fraud dataset
        if mismatch_ids and row["invoice_id"] in mismatch_ids:
            itc = round(itc * 0.7, 2)

        records.append({
            "invoice_id": row["invoice_id"],
            "receiver_gstin": row["receiver_gstin"],
            "supplier_gstin": row["supplier_gstin"],
            "invoice_date": row["invoice_date"],
            "total_value": row["total_value"],
            "itc_available": itc
        })

    return pd.DataFrame(records)

clean_gstr2b = generate_gstr2b(clean_gstr1)
fraud_gstr2b = generate_gstr2b(fraud_gstr1, mismatch_ids)

clean_gstr2b.to_csv("clean_data/gstr2b_invoices.csv", index=False)
fraud_gstr2b.to_csv("fraud_data/gstr2b_invoices.csv", index=False)

# -----------------------------
# 4. Generate GSTR3B Summary
# -----------------------------
def generate_gstr3b(gstr1_df, gstr2b_df):

    summary = []

    for gstin in gstins:

        sales = gstr1_df[gstr1_df["supplier_gstin"] == gstin]["total_value"].sum()
        itc = gstr2b_df[gstr2b_df["receiver_gstin"] == gstin]["itc_available"].sum()

        summary.append({
            "gstin": gstin,
            "return_period": "2023-10",
            "total_sales_declared": round(sales, 2),
            "total_itc_claimed": round(itc, 2),
            "tax_paid_cash": round(max(0, sales * 0.18 - itc), 2)
        })

    return pd.DataFrame(summary)

clean_gstr3b = generate_gstr3b(clean_gstr1, clean_gstr2b)
fraud_gstr3b = generate_gstr3b(fraud_gstr1, fraud_gstr2b)

clean_gstr3b.to_csv("clean_data/gstr3b_summary.csv", index=False)
fraud_gstr3b.to_csv("fraud_data/gstr3b_summary.csv", index=False)

# -----------------------------
# 5. Generate Fraud Labels
# -----------------------------
def generate_fraud_labels():

    labels = []

    fraud_entities = random.sample(gstins, 5)

    for gstin in gstins:
        if gstin in fraud_entities:
            labels.append({
                "gstin": gstin,
                "is_fraud": 1,
                "fraud_type": random.choice(["Circular Trading", "Fake ITC"])
            })
        else:
            labels.append({
                "gstin": gstin,
                "is_fraud": 0,
                "fraud_type": "None"
            })

    return pd.DataFrame(labels)

fraud_labels = generate_fraud_labels()

# Clean dataset labels (all legit)
clean_labels = fraud_labels.copy()
clean_labels["is_fraud"] = 0
clean_labels["fraud_type"] = "None"

clean_labels.to_csv("clean_data/fraud_labels.csv", index=False)
fraud_labels.to_csv("fraud_data/fraud_labels.csv", index=False)

print("All 5 CSV files generated successfully for CLEAN and FRAUD datasets.")