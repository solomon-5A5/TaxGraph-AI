# 🕸️ TaxGraph AI — GST Fraud Detection System

> An AI-powered, graph-based intelligence platform that detects **circular trading rings**, **fake ITC claims**, and **shell company networks** in India's Goods and Services Tax (GST) ecosystem.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Groq](https://img.shields.io/badge/Groq_LLM-Llama_3.3_70B-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Setup & Installation](#-setup--installation)
- [Running the App](#-running-the-app)
- [About Datasets](#-about-datasets)
- [API Endpoints](#-api-endpoints)
- [Project Structure](#-project-structure)
- [Contributing](#-contributing)

---

## 🔍 Overview

TaxGraph AI applies **graph algorithms (DFS cycle detection)** on GST invoice data to uncover fraud rings that are invisible to traditional rule-based auditing. It pairs this with a **Groq-hosted LLM (Llama 3.3 70B)** that generates executive-level fraud summaries for tax officers.

### The Problem
Circular trading fraud costs India's exchequer thousands of crores annually. Fraudsters create chains of shell companies that issue fake invoices to each other, generating illegitimate Input Tax Credit (ITC).

### The Solution
TaxGraph AI ingests GST returns data, builds a **directed transaction graph**, runs **DFS-based cycle detection** to find circular trading rings, cross-references **GSTR-1 vs GSTR-2B** to flag fake ITC claims, and generates AI-powered intelligence reports.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Upload Modal │  │ Force Graph  │  │ AI Insight +   │  │
│  │ (5 CSVs)    │  │ Visualization│  │ Fraud Table    │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘  │
│         │                │                   │           │
└─────────┼────────────────┼───────────────────┼───────────┘
          │  HTTP/REST     │                   │
┌─────────▼────────────────▼───────────────────▼───────────┐
│                   FastAPI Backend                         │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────┐  │
│  │ /api/upload   │  │ /api/graph-   │  │ /api/ai-      │  │
│  │ (5 files)    │  │ data          │  │ insight       │  │
│  └──────┬───────┘  └───────┬───────┘  └───────┬───────┘  │
│         │                  │                   │          │
│  ┌──────▼──────────────────▼───────────────────▼───────┐  │
│  │          Core Engine                                │  │
│  │  • DFS Cycle Detection (circular trading)           │  │
│  │  • GSTR-1 vs 2B Mismatch (fake ITC)                │  │
│  │  • Risk Scoring (trust + 3B cash analysis)          │  │
│  │  • Groq LLM (Llama 3.3 70B executive summary)      │  │
│  └──────┬──────────────────────────────────────────────┘  │
│         │                                                 │
│  ┌──────▼──────────────────────────────────────────────┐  │
│  │          data_pipeline/ (CSV Storage)               │  │
│  │  taxpayers.csv  gstr1_invoices.csv  gstr2b.csv      │  │
│  │  gstr3b_summary.csv  fraud_labels.csv               │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

---

## ✨ Features

| Feature | Description |
|---|---|
| **DFS Cycle Detection** | Finds circular trading rings in the invoice graph using depth-first search |
| **GSTR-1 vs 2B Mismatch** | Flags invoices claimed in GSTR-2B but missing from GSTR-1 (fake ITC) |
| **Mastermind Identification** | Identifies the node with the highest outward fraud value |
| **AI Executive Summary** | Groq LLM generates 2-sentence professional fraud briefs |
| **Structured Fraud Table** | Displays each entity's role (Mastermind / Shell Node) and fake invoice values |
| **Interactive Network Graph** | D3.js force-directed graph with risk-based coloring and animations |
| **Drag & Drop Upload** | Upload all 5 CSV datasets through the browser UI |
| **Real-Time Analysis** | Graph rebuilds and AI re-analyzes on every new upload |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Tailwind CSS v4, D3.js, Lucide Icons, Vite |
| **Backend** | Python 3.9+, FastAPI, Pandas, Uvicorn |
| **AI/LLM** | Groq API → Llama 3.3 70B Versatile |
| **Algorithm** | DFS Cycle Detection, Graph Adjacency List |
| **Data Format** | 5 CSV files (GST return schemas) |

---

## 📦 Prerequisites

Before you begin, make sure you have:

- **Python 3.9+** — [Download](https://www.python.org/downloads/)
- **Node.js 18+** and **npm** — [Download](https://nodejs.org/)
- **Git** — [Download](https://git-scm.com/)
- **Groq API Key** (free) — [Get one here](https://console.groq.com/keys)

---

## 🚀 Setup & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/solomon-5A5/TaxGraph-AI.git
cd TaxGraph-AI
```

### 2. Backend Setup

```bash
# Navigate to backend
cd backend

# (Recommended) Create a virtual environment
python3 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate          # Windows

# Install Python dependencies
pip install fastapi uvicorn pandas python-dotenv groq python-multipart

# Create your .env file with your Groq API key
echo "GROQ_API_KEY=your_groq_api_key_here" > .env
```

> ⚠️ **Replace** `your_groq_api_key_here` with your actual key from [console.groq.com/keys](https://console.groq.com/keys).

### 3. Frontend Setup

```bash
# Navigate to frontend (from project root)
cd ../frontend

# Install Node dependencies
npm install
```

That's it — no database, no Docker, no extra config needed.

---

## ▶️ Running the App

You need **two terminals** running simultaneously:

### Terminal 1 — Start the Backend

```bash
cd backend
python3 -m uvicorn main:app --reload
```

The API will be live at **http://127.0.0.1:8000**. Visit http://127.0.0.1:8000 to confirm you see `{"status":"GSTGraph AI Backend is running 🟢"}`.

### Terminal 2 — Start the Frontend

```bash
cd frontend
npm run dev
```

The dashboard will be live at **http://localhost:5173** (Vite's default port).

### 4. Upload Data & Analyze

1. Open **http://localhost:5173** in your browser
2. Click the **"+ New Investigation"** button in the sidebar
3. Upload the 5 required CSV files (see [About Datasets](#-about-datasets) below)
4. The graph visualization and AI analysis will render automatically

---

## 📊 About Datasets

### ❓ Do I need to include datasets in the repo?

**No.** All datasets are uploaded at runtime through the browser UI (drag & drop). The `.gitignore` excludes all CSV files from `data_pipeline/` because:

- In production, data is **provided by the user** (tax authority uploads real GST returns)
- CSVs can be large and contain sensitive taxpayer information
- The app works with **any data** that matches the expected column schemas

### 🧪 Want to test with synthetic data?

A data generator script is included for development/demo purposes:

```bash
cd data_pipeline
pip install faker         # One-time install
python3 generate_data.py
```

This generates 5 synthetic CSV files with realistic GST data including planted fraud rings.

### 📄 Required CSV Schemas

The upload modal expects exactly **5 CSV files** with these columns:

#### 1. `taxpayers.csv`
| Column | Type | Description |
|---|---|---|
| `gstin` | string | 15-digit GST Identification Number |
| `legal_name` | string | Registered business name |
| `state_code` | int | 2-digit state code (e.g., 27 = Maharashtra) |
| `status` | string | `Active`, `Suspended`, or `Cancelled` |
| `trust_score` | float | 0.0 – 1.0 risk trust score |

#### 2. `gstr1_invoices.csv` (Outward Supplies)
| Column | Type | Description |
|---|---|---|
| `invoice_id` | string | Unique invoice identifier |
| `supplier_gstin` | string | Seller's GSTIN |
| `receiver_gstin` | string | Buyer's GSTIN |
| `total_value` | float | Invoice total in ₹ |
| `tax_amount` | float | GST charged |
| `invoice_date` | date | Date of invoice |

#### 3. `gstr2b_invoices.csv` (Auto-drafted ITC)
| Column | Type | Description |
|---|---|---|
| `invoice_id` | string | Invoice identifier |
| `supplier_gstin` | string | Seller's GSTIN |
| `receiver_gstin` | string | Buyer's GSTIN |
| `total_value` | float | Claimed value in ₹ |
| `tax_amount` | float | ITC claimed |

#### 4. `gstr3b_summary.csv` (Monthly Summary)
| Column | Type | Description |
|---|---|---|
| `gstin` | string | Taxpayer GSTIN |
| `total_sales_declared` | float | Total outward sales declared |
| `itc_claimed` | float | Total ITC claimed |
| `tax_paid_cash` | float | Tax paid via cash ledger |

#### 5. `fraud_labels.csv` (Ground Truth — optional for training)
| Column | Type | Description |
|---|---|---|
| `gstin` | string | Taxpayer GSTIN |
| `is_fraud` | int | `1` = known fraudster, `0` = clean |
| `fraud_type` | string | e.g., `Circular Trading`, `Fake ITC`, `None` |

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/api/graph-data` | Returns nodes & links JSON for the network graph |
| `GET` | `/api/ai-insight` | Returns AI summary + structured fraud table |
| `POST` | `/api/upload` | Accepts 5 CSV files, saves them, and returns graph data |

---

## 📁 Project Structure

```
TaxGraph-AI/
├── backend/
│   ├── main.py              # FastAPI server (all endpoints + DFS algorithm)
│   └── .env                 # Groq API key (not committed)
│
├── data_pipeline/
│   ├── generate_data.py     # Synthetic data generator (for testing)
│   └── *.csv                # Uploaded CSVs stored here (gitignored)
│
├── frontend/
│   ├── public/              # Static assets
│   ├── src/
│   │   ├── App.jsx          # Main dashboard (layout, state, modals)
│   │   ├── NetworkGraph.jsx # D3.js force-directed graph visualization
│   │   ├── App.css          # Global styles
│   │   ├── index.css        # Tailwind imports
│   │   └── main.jsx         # React entry point
│   ├── package.json         # Node dependencies
│   ├── vite.config.js       # Vite bundler config
│   └── index.html           # HTML shell
│
├── .gitignore               # Ignores .env, node_modules, CSVs, etc.
└── README.md                # You are here
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "Add my feature"`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📜 License

This project is licensed under the MIT License.

---

<p align="center">
  Built with ❤️ for India's tax integrity by <a href="https://github.com/solomon-5A5">solomon-5A5</a>
</p>
