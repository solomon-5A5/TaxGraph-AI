# 🕸️ TaxGraph AI — GST Fraud Detection & Intelligence Platform

> An AI-powered, graph-based intelligence platform that detects **circular trading rings**, **fake ITC claims**, **shell company networks**, and **reciprocal trading** in India's Goods and Services Tax (GST) ecosystem — with natural language querying, explainable AI, and real-time alerts.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![NetworkX](https://img.shields.io/badge/NetworkX-Graph_Engine-blue)
![Groq](https://img.shields.io/badge/Groq_LLM-Llama_3.3_70B-orange)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-v4-38bdf8?logo=tailwindcss&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-7-646CFF?logo=vite&logoColor=white)
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
- [Pages & UI](#-pages--ui)
- [Contributing](#-contributing)

---

## 🔍 Overview

TaxGraph AI applies **graph algorithms** (NetworkX cycle detection, PageRank, bidirectional edge analysis) on GST invoice data to uncover fraud rings that are invisible to traditional rule-based auditing. It pairs this with a **Groq-hosted LLM (Llama 3.3 70B)** that generates executive-level fraud summaries, explainable AI reports, and natural language data querying for tax officers.

### The Problem

Circular trading fraud costs India's exchequer thousands of crores annually. Fraudsters create chains of shell companies that issue fake invoices to each other, generating illegitimate Input Tax Credit (ITC).

### The Solution

TaxGraph AI ingests GST returns data (GSTR-1, GSTR-2B, GSTR-3B), builds a **directed transaction graph** using NetworkX, runs **multiple fraud detection algorithms** (circular trading, shell companies, reciprocal trading, fake invoices), performs **multi-join chain reconciliation** (GSTR-1 ↔ GSTR-2B ↔ GSTR-3B), computes **weighted risk scores** per vendor, and generates **AI-powered intelligence reports** with actionable recommendations.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                       React 19 Frontend (Vite)                   │
│  ┌────────────┐ ┌────────────┐ ┌──────────┐ ┌───────────────┐   │
│  │ Dashboard   │ │ Reconcil-  │ │ Graph    │ │ Fraud         │   │
│  │ (Stats +   │ │ iation     │ │ Analysis │ │ Detection     │   │
│  │  AI Panel) │ │ Table      │ │ (D3.js)  │ │ (4 patterns)  │   │
│  └─────┬──────┘ └─────┬──────┘ └────┬─────┘ └───────┬───────┘   │
│  ┌─────┴──────┐ ┌─────┴──────┐                                   │
│  │ Alert      │ │ NL Query   │                                   │
│  │ Center     │ │ (Chat UI)  │                                   │
│  └─────┬──────┘ └─────┬──────┘                                   │
└────────┼──────────────┼──────────────────────────────────────────┘
         │  HTTP/REST   │
┌────────▼──────────────▼──────────────────────────────────────────┐
│                    FastAPI Backend (Uvicorn)                      │
│                                                                   │
│  ┌─────────────────── Services Layer ──────────────────────────┐  │
│  │                                                             │  │
│  │  GSTIngestionService    — Data loading + NetworkX graph     │  │
│  │  ReconciliationEngine   — GSTR-1↔2B↔3B multi-join chain    │  │
│  │  FraudDetectionEngine   — Circular/Shell/Reciprocal/Fake   │  │
│  │  RiskScoringEngine      — Weighted heuristic risk scores   │  │
│  │  ExplainableAIService   — Template + LLM explanations      │  │
│  │  NLQueryEngine          — Natural language → Pandas code   │  │
│  │  AlertService           — Structured alert generation      │  │
│  │                                                             │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌─────────────────── Core Algorithms ─────────────────────────┐  │
│  │  • NetworkX simple_cycles() — circular trading detection    │  │
│  │  • PageRank anomaly — shell company identification          │  │
│  │  • Bidirectional edge scan — reciprocal trading             │  │
│  │  • Round-number pattern analysis — fake invoices            │  │
│  │  • DFS cycle detection — legacy circular trading            │  │
│  │  • Weighted risk scoring (graph + filing features)          │  │
│  │  • Groq LLM (Llama 3.3 70B) — AI summaries + NL query     │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌─────────────────── Data Layer ──────────────────────────────┐  │
│  │  data_pipeline/ (CSV Storage)                               │  │
│  │  taxpayers.csv · gstr1_invoices.csv · gstr2b_invoices.csv   │  │
│  │  gstr3b_summary.csv · fraud_labels.csv                      │  │
│  └─────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### 🔬 Fraud Detection (4 Algorithms)

| Algorithm | Method | Description |
|---|---|---|
| **Circular Trading** | `nx.simple_cycles()` | Finds closed-loop invoice rings (A→B→C→A) using NetworkX graph traversal |
| **Shell Companies** | PageRank anomaly | Flags entities with low graph importance but abnormally high transaction volume |
| **Reciprocal Trading** | Bidirectional edge scan | Detects A↔B invoice pairs indicating round-tripping |
| **Fake Invoices** | Pattern analysis | Identifies round-number amounts and repeated identical values between same parties |

### 📊 Reconciliation Engine

| Feature | Description |
|---|---|
| **Multi-join Chain** | GSTR-1 ↔ GSTR-2B ↔ GSTR-3B full chain validation using Pandas outer joins |
| **Mismatch Classification** | Missing in GSTR-1, Missing in GSTR-2B, Value Mismatch, Tax Mismatch |
| **ITC Overclaim Detection** | Flags cases where ITC claimed in GSTR-3B exceeds GSTR-2B eligible amount |
| **Severity Scoring** | CRITICAL / WARNING / INFO based on value differences |

### 🧠 AI & Intelligence

| Feature | Description |
|---|---|
| **AI Executive Summary** | Groq LLM generates professional fraud briefs from detected patterns |
| **Explainable AI** | Template + LLM hybrid explanations for every mismatch and risk decision |
| **Natural Language Query** | Ask questions in plain English — LLM converts to Pandas code and executes |
| **Risk Scoring** | Weighted heuristic scoring combining graph features, filing behavior, and fraud labels |

### 🖥️ Frontend (6 Pages)

| Page | Description |
|---|---|
| **Dashboard** | KPI cards, network graph preview, AI analysis panel with fraud table |
| **Reconciliation** | Sortable/filterable mismatch table with per-invoice AI explanations |
| **Graph Analysis** | Full-screen D3.js force-directed graph with node risk profiling sidebar |
| **Fraud Detection** | Tabbed view for all 4 fraud patterns with detailed results |
| **Alert Center** | Severity-filtered alert feed from reconciliation + fraud engines |
| **NL Query** | Chat-style interface with example queries, generated code viewer, and result tables |

### 🌐 Other

| Feature | Description |
|---|---|
| **CSV Upload** | Upload all 5 datasets through the browser UI modal |
| **Interactive Network Graph** | D3.js force-directed graph with risk-based coloring, flowing animations, ring highlighting |
| **Risk Leaderboard** | Top-N riskiest vendors ranked by weighted score |
| **Vendor Risk Profile** | Click any node to see PageRank, degree, ITC ratio, fraud labels |
| **Real-Time Analysis** | Graph rebuilds and all engines re-analyze on every new upload |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Tailwind CSS v4, D3.js, Recharts, Lucide Icons, React Router v7, Vite 7 |
| **Backend** | Python 3.9+, FastAPI, Pandas, NetworkX, Uvicorn |
| **AI/LLM** | Groq API → Llama 3.3 70B Versatile |
| **Algorithms** | NetworkX `simple_cycles()`, PageRank, DFS Cycle Detection, Weighted Risk Scoring |
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
pip install fastapi uvicorn pandas networkx python-dotenv groq python-multipart

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
source venv/bin/activate        # Activate virtual environment (if not already active)
python3 -m uvicorn main:app --reload
```

The API will be live at **http://127.0.0.1:8000**. Visit http://127.0.0.1:8000 to confirm you see:

```json
{"status": "GSTGraph AI Backend is running 🟢"}
```

### Terminal 2 — Start the Frontend

```bash
cd frontend
npm run dev
```

The dashboard will be live at **http://localhost:5173** (Vite's default port).

### 3. Upload Data & Analyze

1. Open **http://localhost:5173** in your browser
2. Click the **"+ New Analysis"** button at the bottom of the sidebar
3. Upload the 5 required CSV files (see [About Datasets](#-about-datasets) below)
4. The dashboard, graph, reconciliation, and fraud detection will populate automatically

### Quick Reference

| Step | Command | Directory |
|---|---|---|
| Create virtual env | `python3 -m venv venv` | `backend/` |
| Activate venv (macOS/Linux) | `source venv/bin/activate` | `backend/` |
| Activate venv (Windows) | `venv\Scripts\activate` | `backend/` |
| Install backend deps | `pip install fastapi uvicorn pandas networkx python-dotenv groq python-multipart` | `backend/` |
| Set Groq API key | `echo "GROQ_API_KEY=your_key" > .env` | `backend/` |
| Run backend | `python3 -m uvicorn main:app --reload` | `backend/` |
| Install frontend deps | `npm install` | `frontend/` |
| Run frontend | `npm run dev` | `frontend/` |

---

## 📊 About Datasets

### ❓ Do I need to include datasets in the repo?

**No.** All datasets are uploaded at runtime through the browser UI. The `.gitignore` excludes CSV files from `data_pipeline/` because:

- In production, data is **provided by the user** (tax authority uploads real GST returns)
- CSVs can be large and contain sensitive taxpayer information
- The app works with **any data** that matches the expected column schemas

### 🧪 Want to test with synthetic data?

Two data generator scripts are included:

**Option A — Quick generator** (50 taxpayers, 300 invoices):

```bash
cd data_pipeline
pip install faker
python3 generate_data.py
```

**Option B — Full generator** (500 taxpayers, 8000 invoices, 6 months):

```bash
cd GSTGraph-AI
pip install faker numpy
python3 generator.py
```

> **Note:** The `data_pipeline/generate_data.py` uses a simpler schema. The `GSTGraph-AI/generator.py` produces more comprehensive data with multi-month GSTR-3B filings and injected mismatches. You may need to rename columns to match the schemas below before uploading.

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
| `tax_amount` / `itc_available` | float | ITC available to buyer |

#### 4. `gstr3b_summary.csv` (Monthly Summary)

| Column | Type | Description |
|---|---|---|
| `gstin` | string | Taxpayer GSTIN |
| `return_period` | string | Filing period (e.g., `2025-01`) |
| `total_sales_declared` | float | Total outward sales declared |
| `total_itc_claimed` / `itc_claimed` | float | Total ITC claimed |
| `tax_paid_cash` | float | Tax paid via cash ledger |

#### 5. `fraud_labels.csv` (Ground Truth)

| Column | Type | Description |
|---|---|---|
| `gstin` | string | Taxpayer GSTIN |
| `is_fraud` | int | `1` = known fraudster, `0` = clean |
| `fraud_type` | string | e.g., `Circular Trading`, `Fake ITC`, `None` |

---

## 🔌 API Endpoints

### Legacy Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check — returns `{"status": "GSTGraph AI Backend is running 🟢"}` |
| `POST` | `/api/upload` | Upload 5 CSV files, saves them, and returns graph data |
| `GET` | `/api/graph-data` | Returns nodes & links JSON for the network graph |
| `GET` | `/api/ai-insight` | Returns AI executive summary + structured fraud table |

### v1 Service Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/stats` | Dashboard statistics (invoices, taxpayers, mismatches, fraud flags, alerts) |
| `POST` | `/api/v1/reconcile` | Run full GSTR-1↔2B↔3B chain reconciliation |
| `GET` | `/api/v1/reconcile/mismatches` | Get all reconciliation mismatches with severity |
| `GET` | `/api/v1/fraud/circular-trades` | Detect circular trading patterns via `nx.simple_cycles()` |
| `GET` | `/api/v1/fraud/shell-companies` | Detect shell companies via PageRank anomaly |
| `GET` | `/api/v1/fraud/reciprocal` | Detect reciprocal (round-trip) trading pairs |
| `GET` | `/api/v1/fraud/fake-invoices` | Detect fake invoice patterns (round numbers, repeats) |
| `GET` | `/api/v1/fraud/patterns` | Get all 4 fraud patterns combined with summary counts |
| `GET` | `/api/v1/risk/vendor/{gstin}` | Get detailed risk score + features for a specific vendor |
| `GET` | `/api/v1/risk/leaderboard` | Get top-20 riskiest vendors ranked by weighted score |
| `GET` | `/api/v1/explain/mismatch/{invoice_id}` | AI explanation for a specific reconciliation mismatch |
| `GET` | `/api/v1/explain/risk/{gstin}` | AI explanation for a vendor's risk score |
| `POST` | `/api/v1/query` | Natural language query → Pandas code → results + explanation |
| `GET` | `/api/v1/alerts` | Get all alerts generated from reconciliation + fraud analysis |
| `POST` | `/api/v1/reload` | Force reload data from disk and rebuild NetworkX graph |

---

## 📁 Project Structure

```
TaxGraph-AI/
├── backend/
│   ├── main.py                        # FastAPI server — all endpoints + DFS algorithm
│   ├── .env                           # Groq API key (not committed)
│   └── services/
│       ├── __init__.py                # Service module marker
│       ├── ingestion.py               # GSTIngestionService — data loading + NetworkX graph builder
│       ├── reconciliation.py          # ReconciliationEngine — GSTR-1↔2B↔3B multi-join chain
│       ├── fraud.py                   # FraudDetectionEngine — 4 pattern detectors
│       ├── risk.py                    # RiskScoringEngine — weighted heuristic risk scoring
│       ├── explain.py                 # ExplainableAIService — template + LLM explanations
│       ├── nl_query.py                # NLQueryEngine — natural language → Pandas → results
│       └── alerts.py                  # AlertService — structured alert generation
│
├── data_pipeline/
│   ├── generate_data.py               # Synthetic data generator (quick — 50 taxpayers)
│   ├── taxpayers.csv                  # Uploaded/generated taxpayer data (gitignored)
│   ├── gstr1_invoices.csv             # Uploaded/generated GSTR-1 data (gitignored)
│   ├── gstr2b_invoices.csv            # Uploaded/generated GSTR-2B data (gitignored)
│   ├── gstr3b_summary.csv            # Uploaded/generated GSTR-3B data (gitignored)
│   └── fraud_labels.csv              # Uploaded/generated fraud labels (gitignored)
│
├── frontend/
│   ├── index.html                     # HTML shell
│   ├── package.json                   # Node dependencies (React 19, D3, Recharts, etc.)
│   ├── vite.config.js                 # Vite bundler config with Tailwind CSS v4 plugin
│   ├── eslint.config.js               # ESLint config
│   ├── public/                        # Static assets
│   └── src/
│       ├── main.jsx                   # React entry point
│       ├── App.jsx                    # Main layout — sidebar, routing, upload modal
│       ├── App.css                    # Global styles
│       ├── index.css                  # Tailwind CSS v4 import
│       ├── NetworkGraph.jsx           # D3.js force-directed graph with ring highlighting
│       └── pages/
│           ├── DashboardPage.jsx      # KPI metrics, graph preview, AI insight panel
│           ├── ReconciliationPage.jsx # Mismatch table with filters, sort, AI explain
│           ├── GraphPage.jsx          # Full-screen graph + vendor risk sidebar
│           ├── FraudPage.jsx          # 4-tab fraud detection results
│           ├── AlertsPage.jsx         # Severity-filtered alert feed
│           └── QueryPage.jsx          # Chat-style NL query interface
│
├── GSTGraph-AI/
│   ├── generator.py                   # Full synthetic data generator (500 taxpayers)
│   └── data/                          # Generated data output (gitignored)
│
├── .gitignore                         # Ignores .env, node_modules, CSVs, __pycache__, etc.
└── README.md                          # You are here
```

---

## 🖥️ Pages & UI

### 1. Dashboard (`/`)

- **4 KPI cards**: Total Invoices, Active Taxpayers, Mismatches, Fraud Flags
- **Network Graph preview** with risk-colored nodes and flowing fraud edges
- **AI Analysis panel** with LLM-generated fraud summary, fraud table, and pattern counts
- **DRC-01 Show Cause Notice** generation button

### 2. Reconciliation (`/reconciliation`)

- **5 summary cards**: Total Invoices, Reconciled, Missing GSTR-1, Value Mismatch, ITC Overclaim
- **Filterable mismatch table** with search, status filters, and column sorting
- **Per-invoice AI Explain** button — fetches LLM-enhanced explanation with recommended actions

### 3. Graph Analysis (`/graph`)

- **Full-screen D3.js force-directed graph** with zoom, pan, and drag
- **Node click** → isolates the fraud ring connected to that node
- **Vendor risk sidebar** — click any node in the list to see PageRank, degree, ITC ratio, fraud labels
- **Legend** with risk-level color coding

### 4. Fraud Detection (`/fraud`)

- **4-tab interface**: Circular Trading, Shell Companies, Reciprocal Trading, Fake Invoices
- **Circular Trading**: Visual chain display (GSTIN → GSTIN → CYCLE) with edge-level details
- **Shell Companies**: PageRank + volume cards with severity badges
- **Reciprocal Trading**: Tabular A↔B pairs with directional values
- **Fake Invoices**: Pattern cards with supplier → receiver details

### 5. Alert Center (`/alerts`)

- **Severity filter buttons** (All / Critical / Warning / Info) with counts
- **Alert cards** with type badges (FRAUD / MISMATCH), related GSTIN, and invoice references
- **Live pulse indicator** for critical alerts

### 6. NL Query (`/query`)

- **Chat-style interface** with user messages and AI responses
- **Example query chips** for quick start
- **Expandable generated Pandas code** viewer
- **Result table** with up to 20 rows displayed
- **AI explanation** of query results

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
  Built with ❤️ for India's tax integrity by <a href="https://github.com/solomon-5A5">Team Code Smashers</a>
</p>