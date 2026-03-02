"""
generate_large_dataset.py — Generate a larger synthetic dataset (200 taxpayers)
with realistic fraud patterns for robust XGBoost training.
Produces: taxpayers.csv, gstr1_invoices.csv, gstr2b_invoices.csv,
          gstr3b_summary.csv, fraud_labels.csv
"""

import pandas as pd
import numpy as np
import random
import string
import os

random.seed(42)
np.random.seed(42)

# ─── Configuration ───
NUM_TAXPAYERS = 200
NUM_INVOICES = 800
NUM_FRAUD_CIRCULAR = 12  # 3 rings of 4
NUM_FRAUD_SHELL = 8
NUM_FRAUD_FAKE_ITC = 6
STATES = [27, 29, 7, 33, 9, 6, 24, 21, 19, 36]

COMPANY_TYPES = [
    "Industries Pvt Ltd", "Exports Ltd", "Trading Co", "Enterprises",
    "Solutions Pvt Ltd", "Corp", "Distributors", "Mills",
    "Components Pvt Ltd", "Traders", "Works", "Mining Corp",
    "Pharma Distributors", "IT Solutions", "Logistics Hub",
    "Steel Industries", "Textiles LLP", "Agro Exports",
    "Auto Components", "Polymers Ltd", "Ceramic Works",
    "Spice Exports", "Rice Millers", "Dyes & Chemicals",
]

CITY_NAMES = [
    "Mumbai", "Bangalore", "Delhi", "Chennai", "Lucknow",
    "Faridabad", "Ahmedabad", "Bhubaneswar", "Kolkata",
    "Hyderabad", "Pune", "Jaipur", "Coimbatore", "Indore",
    "Nagpur", "Vadodara", "Surat", "Kanpur", "Patna", "Vizag",
]


def random_pan():
    """Generate a random PAN-like string."""
    return ''.join(random.choices(string.ascii_uppercase, k=5)) + \
        ''.join(random.choices(string.digits, k=4)) + \
        random.choice(string.ascii_uppercase)


def generate_gstin(state_code):
    """Generate a valid-format GSTIN."""
    pan = random_pan()
    return f"{state_code:02d}{pan}1Z{random.choice(string.ascii_uppercase)}"


def main():
    print("🚀 Generating large synthetic dataset (200 taxpayers, 800+ invoices)...")

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # ─── Step 1: Generate Taxpayers ───
    taxpayers = []
    for i in range(NUM_TAXPAYERS):
        state = random.choice(STATES)
        city = random.choice(CITY_NAMES)
        ctype = random.choice(COMPANY_TYPES)
        taxpayers.append({
            "gstin": generate_gstin(state),
            "legal_name": f"{city} {ctype}",
            "registration_date": f"20{random.randint(16, 24):02d}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            "status": random.choices(["Active", "Suspended"], weights=[92, 8])[0],
            "state_code": state,
            "trust_score": round(random.uniform(0.3, 0.95), 2),
        })

    # ─── Step 2: Designate fraud entities ───
    fraud_labels = []

    # Circular trading rings (3 rings of 4 entities)
    circular_gstins = set()
    ring_starts = [0, 4, 8]
    for ring_idx, start in enumerate(ring_starts):
        ring = taxpayers[start: start + 4]
        for t in ring:
            circular_gstins.add(t["gstin"])
            fraud_labels.append({
                "gstin": t["gstin"],
                "is_fraud": 1,
                "fraud_type": "Circular Trading",
            })

    # Shell companies
    shell_gstins = set()
    for i in range(12, 12 + NUM_FRAUD_SHELL):
        shell_gstins.add(taxpayers[i]["gstin"])
        fraud_labels.append({
            "gstin": taxpayers[i]["gstin"],
            "is_fraud": 1,
            "fraud_type": "Shell Company",
        })

    # Fake ITC claimers
    fake_itc_gstins = set()
    for i in range(20, 20 + NUM_FRAUD_FAKE_ITC):
        fake_itc_gstins.add(taxpayers[i]["gstin"])
        fraud_labels.append({
            "gstin": taxpayers[i]["gstin"],
            "is_fraud": 1,
            "fraud_type": "Fake ITC",
        })

    # Clean taxpayers
    all_fraud_gstins = circular_gstins | shell_gstins | fake_itc_gstins
    for t in taxpayers:
        if t["gstin"] not in all_fraud_gstins:
            fraud_labels.append({
                "gstin": t["gstin"],
                "is_fraud": 0,
                "fraud_type": "None",
            })

    # ─── Step 3: Generate GSTR-1 Invoices ───
    invoices = []
    invoice_counter = 1

    # Normal invoices between random taxpayers
    for _ in range(NUM_INVOICES):
        seller = random.choice(taxpayers)
        buyer = random.choice(taxpayers)
        while buyer["gstin"] == seller["gstin"]:
            buyer = random.choice(taxpayers)

        base_value = round(random.uniform(50_000, 800_000), 2)
        tax = round(base_value * 0.18, 2)

        invoices.append({
            "invoice_id": f"INV-2024-{invoice_counter:04d}",
            "supplier_gstin": seller["gstin"],
            "receiver_gstin": buyer["gstin"],
            "total_value": base_value,
            "tax_amount": tax,
        })
        invoice_counter += 1

    # Inject circular trading invoices (high value, round numbers)
    for ring_start in ring_starts:
        ring = taxpayers[ring_start: ring_start + 4]
        for j in range(len(ring)):
            value = round(random.uniform(2_000_000, 5_000_000), 2)
            tax = round(value * 0.18, 2)
            invoices.append({
                "invoice_id": f"INV-2024-{invoice_counter:04d}",
                "supplier_gstin": ring[j]["gstin"],
                "receiver_gstin": ring[(j + 1) % len(ring)]["gstin"],
                "total_value": value,
                "tax_amount": tax,
            })
            invoice_counter += 1

    # Inject shell company invoices (high volume from few sources)
    for gstin in shell_gstins:
        for _ in range(random.randint(8, 15)):
            buyer = random.choice(taxpayers)
            while buyer["gstin"] == gstin:
                buyer = random.choice(taxpayers)
            value = round(random.uniform(1_000_000, 3_000_000), 2)
            tax = round(value * 0.18, 2)
            invoices.append({
                "invoice_id": f"INV-2024-{invoice_counter:04d}",
                "supplier_gstin": gstin,
                "receiver_gstin": buyer["gstin"],
                "total_value": value,
                "tax_amount": tax,
            })
            invoice_counter += 1

    # Inject fake ITC claimers (receive large amounts, no corresponding sales)
    for gstin in fake_itc_gstins:
        for _ in range(random.randint(5, 10)):
            seller = random.choice(taxpayers)
            while seller["gstin"] == gstin:
                seller = random.choice(taxpayers)
            value = round(random.uniform(500_000, 2_000_000), 2)
            tax = round(value * 0.18, 2)
            invoices.append({
                "invoice_id": f"INV-2024-{invoice_counter:04d}",
                "supplier_gstin": seller["gstin"],
                "receiver_gstin": gstin,
                "total_value": value,
                "tax_amount": tax,
            })
            invoice_counter += 1

    # ─── Step 4: Generate GSTR-2B (mirror of received invoices) ───
    gstr2b = []
    for inv in invoices:
        gstr2b.append({
            "invoice_id": inv["invoice_id"],
            "supplier_gstin": inv["supplier_gstin"],
            "receiver_gstin": inv["receiver_gstin"],
            "total_value": inv["total_value"],
            "itc_available": inv["tax_amount"],
        })

    # Inject mismatches (5% of invoices have value differences)
    mismatch_count = int(len(gstr2b) * 0.05)
    for idx in random.sample(range(len(gstr2b)), mismatch_count):
        gstr2b[idx]["total_value"] = round(gstr2b[idx]["total_value"] * random.uniform(0.9, 1.1), 2)

    # ─── Step 5: Generate GSTR-3B (monthly summaries) ───
    gstr3b = []
    for t in taxpayers:
        gstin = t["gstin"]

        # Sum outward supply
        outward_invoices = [inv for inv in invoices if inv["supplier_gstin"] == gstin]
        total_sales = sum(inv["total_value"] for inv in outward_invoices)

        # Sum ITC available
        inward_invoices = [inv for inv in invoices if inv["receiver_gstin"] == gstin]
        total_itc = sum(inv["tax_amount"] for inv in inward_invoices)

        # Fraud entities: claim more ITC, pay less cash
        if gstin in all_fraud_gstins:
            itc_claimed = round(total_itc * random.uniform(1.3, 2.0), 2)
            cash_paid = 0.0
        else:
            itc_claimed = round(total_itc * random.uniform(0.85, 1.0), 2)
            cash_paid = round(max(total_sales * 0.18 - itc_claimed, 0) * random.uniform(0.8, 1.0), 2)

        gstr3b.append({
            "gstin": gstin,
            "return_period": "2024-01",
            "total_sales_declared": round(total_sales, 2),
            "total_itc_claimed": itc_claimed,
            "tax_paid_cash": cash_paid,
        })

    # ─── Step 6: Save all CSVs ───
    df_taxpayers = pd.DataFrame(taxpayers)
    df_gstr1 = pd.DataFrame(invoices)
    df_gstr2b = pd.DataFrame(gstr2b)
    df_gstr3b = pd.DataFrame(gstr3b)
    df_fraud = pd.DataFrame(fraud_labels)

    df_taxpayers.to_csv(os.path.join(base_dir, "taxpayers.csv"), index=False)
    df_gstr1.to_csv(os.path.join(base_dir, "gstr1_invoices.csv"), index=False)
    df_gstr2b.to_csv(os.path.join(base_dir, "gstr2b_invoices.csv"), index=False)
    df_gstr3b.to_csv(os.path.join(base_dir, "gstr3b_summary.csv"), index=False)
    df_fraud.to_csv(os.path.join(base_dir, "fraud_labels.csv"), index=False)

    print(f"✅ Generated:")
    print(f"   📋 {len(df_taxpayers)} taxpayers ({len(all_fraud_gstins)} fraud, {len(df_taxpayers) - len(all_fraud_gstins)} clean)")
    print(f"   📑 {len(df_gstr1)} GSTR-1 invoices")
    print(f"   📑 {len(df_gstr2b)} GSTR-2B invoices ({mismatch_count} mismatches)")
    print(f"   📊 {len(df_gstr3b)} GSTR-3B summaries")
    print(f"   🏷️  {len(df_fraud)} fraud labels")
    print(f"   📂 Saved to: {base_dir}")


if __name__ == "__main__":
    main()
