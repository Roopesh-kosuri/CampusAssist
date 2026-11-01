---
title: CampusAssist - LPU Student AI Assistant
emoji: 🎓
colorFrom: orange
colorTo: red
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# 🎓 CampusAssist · Lovely Professional University (LPU)
### ⚡ AI-Powered Semantic Campus Assistant & Knowledge Engine

[![Live Web App](https://img.shields.io/badge/Render-Live%20App%20Online-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://campusassist-h0zp.onrender.com/)
[![Python 3.11](https://img.shields.io/badge/Python-3.11.9-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Electron](https://img.shields.io/badge/Electron-Desktop%20App-47848F?style=for-the-badge&logo=electron&logoColor=white)](https://www.electronjs.org/)
[![PyTorch CPU](https://img.shields.io/badge/PyTorch-CPU%20Optimized-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![FAISS](https://img.shields.io/badge/FAISS-Dense%20Vector%20Search-00599C?style=for-the-badge&logo=meta&logoColor=white)](https://github.com/facebookresearch/faiss)
[![Groq](https://img.shields.io/badge/Groq-LPU%20AI%20Engine-F55036?style=for-the-badge&logo=openai&logoColor=white)](https://groq.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

---

## 🌟 Overview

**CampusAssist** is an enterprise-grade, offline-first Artificial Intelligence conversational assistant designed specifically for students, faculty, and visitors at **Lovely Professional University (LPU)**, Phagwara, Punjab.

Navigating a 600+ acre campus with 35,000+ students and complex online portals (*UMS, e-Connect, RMS, Fee Portal*) is challenging. Standard keyword search frequently fails when students ask casual questions or use Hinglish slang. **CampusAssist solves this with a multi-engine hybrid retrieval pipeline combining dense vector embeddings (FAISS + MiniLM), lexical TF-IDF, calibrated confidence gating, and a grounded conversational LLM layer.**

```
   Student Question (English / Hinglish / Slang)
                       │
                       ▼
       🛡️ PII Redaction & Normalization
                       │
       ┌───────────────┴───────────────┐
       ▼                               ▼
 🔍 Lexical Engine               🧠 Dense Semantic
  (TF-IDF + Overlap)             (MiniLM + FAISS)
       │                               │
       └───────────────┬───────────────┘
                       ▼
        ⚡ Hybrid Fusion (0.70 Dense + 0.30 Lexical)
                       │
                       ▼
        🎯 Calibrated Confidence Gate (τ*)
             ├─ High Confidence ──► 📜 Top-1 FAQ Answer ──► 🤖 Grounded Groq Polish
             └─ Out-of-Scope    ──► 🏫 Verified LPU Campus Knowledge / Counter Routing
```

---

## ✨ Key Features

- 🧠 **91.0% Top-1 Retrieval Accuracy**: Evaluated on a held-out test split of 144 real-world student paraphrases across 6 core service domains (*Hostel, Library, Fees, ID Card, Transport, Exams*).
- 🧭 **Complete LPU Campus & UMS Pathways**:
  - **Exam Seating Plan**: `UMS → Examination → Seating Plan → Course Code → Block, Room & Bench`.
  - **Admit Card & Datesheet**: `UMS → Examination → Admit Card / Datesheet`.
  - **Hostel Leave Pass**: `UMS → Hostel/Residential Services → Leave Management → Biometric Turnstile`.
  - **RMS Maintenance**: `UMS → Relationship Management System → Log Request (Electrical/Plumbing/Wi-Fi)`.
  - **Fee Payment**: `UMS → Fee Management → Online Payment (Zee Portal) → Tax Invoice Receipts`.
  - **Campus Landmarks**: Complete details on **Blocks 13, 25-28, 29, 30 (DSW), 32 (Admin), 34 (COE), 36, 37 (Central Library), 38**, **Uni-Mall**, and **Uni-Hospital**.
  - **Dining & Food Courts**: Uni-Mall Food Court (*Domino's, Subway, Baskin Robbins, Dosa Plaza, Chai Point*), Block 13 Amphitheatre kiosks, BH/GH night canteens (open till 1 AM).
  - **Hostel Complexes**: Comprehensive knowledge of **BH-1 through BH-8**, **GH-1 through GH-6**, AC/Cooler/Non-AC room configs, and automated laundromats.
- 🎨 **Liquid Glass Web UI**: Frosted glass morphism, adaptive light cream & midnight dark themes, pill-shaped capsule controls, and zero third-party client dependencies.
- 💻 **Windows Desktop Application**: Built with Electron. Features a custom frameless floating pill header, keyboard shortcut (`Ctrl+B`) for sidebar toggle, and pre-packaged **Installer** and **Portable `.exe`** binaries.
- 📱 **Mobile PWA Ready**: Installable as a native app on Android (Chrome) and iOS (Safari) via Progressive Web App manifest and service worker.
- 🛡️ **Privacy by Design**: Automatic client/server scrubbing of 8-digit LPU Registration Numbers, phone numbers (+91), and emails before queries hit search indices.
- ⚡ **Grounded LLM Layer**: Groq-powered natural conversational rewriting with an **Abstract Syntax Tree (AST) entity verifier** preventing hallucinations.
- 📊 **Live Analytics & Evaluation Suite**: In-app live telemetry dashboard tracking query volume, confidence scores, feedback ratings, and error analysis.

---

## 🏆 Benchmark Evaluation Results

Evaluated on held-out **TEST split** of 144 human-authored student queries and 30 adversarial out-of-scope queries under strict offline conditions:

| Retrieval Method | Top-1 Accuracy (%) | Top-3 Accuracy (%) | MRR | Out-of-Scope Rejection (%) | Threshold ($\tau^*$) | Mean Latency |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 🔤 **Keyword Overlap (`kw`)** | 73.6% | 87.5% | 0.795 | 66.7% | 0.24 | < 1 ms |
| 📊 **TF-IDF Cosine (`tf`)** | 69.4% | 85.4% | 0.768 | 53.3% | 0.20 | < 1 ms |
| 🧠 **Semantic Embeddings (`emb`)** | 88.9% | 97.2% | 0.930 | 83.3% | 0.40 | 8.2 ms |
| ⚡ **Hybrid Fusion (`hyb`)** | **91.0%** | **97.9%** | **0.942** | **83.3%** | **0.36** | 8.8 ms |

### Accuracy by Linguistic Challenge Type:
- 🔀 **Synonym Swaps**: **97.1%** *(e.g. "tuition installments" → fees)*
- 🌐 **Hinglish Mixed**: **91.8%** *(e.g. "hostel gate kab band hota hai" → curfew)*
- 🧩 **Low Overlap**: **87.5%** *(e.g. "fan grinding noise" → maintenance request)*
- ✍️ **Typos & Permutations**: **86.8%** *(e.g. "duplcate id crd" → replacement procedure)*

---

## 🚀 Quick Start Guide

### 1. Clone the Repository
```bash
git clone https://github.com/Roopesh-kosuri/CampusAssist.git
cd CampusAssist
```

### 2. Set Up Virtual Environment & Dependencies
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# Install CPU PyTorch and dependencies
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the project root:
```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
HOST=127.0.0.1
PORT=8000
```

### 4. Run the Web Application
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser to: **`http://localhost:8000`**

---

## 💻 Desktop Application (Windows)

CampusAssist includes a native Electron desktop client packaged for Windows:

```bash
cd desktop
npm install

# Run desktop in development
npm start

# Build portable and installer executables
npm run dist:win
```

Pre-built binaries are saved to [`app/static/downloads/`](file:///app/static/downloads/):
- 📦 **Installer**: `CampusAssist Setup 1.0.0.exe` (~74 MB)
- 🚀 **Portable**: `CampusAssist-Portable-1.0.0.exe` (~74 MB, no installation required)

---

## 🚢 Free Cloud Deployment Guide

### Option A: Hugging Face Spaces (Recommended · 100% Free · 16GB RAM)
Hugging Face Spaces provides **2 vCPU + 16GB RAM + Zero Cold Starts** for free, making it ideal for PyTorch & FAISS:

1. Create a free account at [huggingface.co](https://huggingface.co/).
2. Create a **New Space** → Name: `campusassist`.
3. Select **Space SDK**: **Docker** → **Blank** *(our repo contains the optimized `Dockerfile`)*.
4. Go to **Settings → Variables and secrets** → Add secret: `GROQ_API_KEY` = your Groq API key.
5. Push your code:
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/campusassist
   git push space master:main
   ```
6. Your live app is available at: `https://<your-username>-campusassist.hf.space`!

### Option B: Render (render.com)
1. Sign up on [render.com](https://render.com/).
2. Click **New +** → **Web Service** → Connect your GitHub repo.
3. Select **Environment**: **Docker**.
4. Add Environment Variable: `GROQ_API_KEY` = your Groq API key.
5. Click **Deploy**.

---

## 🧪 Running Automated Tests & Benchmark Reproduction

```bash
# Run unit tests (10/10 endpoints verified)
pytest tests/test_api.py -v

# Run full dataset provenance and schema validation
python -m src.validate_data

# Run deterministic benchmark evaluation on the held-out TEST split
python -m src.evaluate_benchmark --split test

# Test LLM entity grounding & hallucination defense audit
python -m src.llm.evaluate_grounding
```

---

## 📁 Repository Structure

```
CampusAssist/
├── app/
│   ├── main.py                     # FastAPI application endpoints & routing
│   └── static/                     # Liquid Glass responsive frontend
│       ├── index.html              # Main single-page interface
│       ├── manifest.json           # Mobile Progressive Web App manifest
│       ├── service-worker.js       # Offline PWA asset caching
│       ├── downloads/              # Desktop .exe installers & portable builds
│       └── icons/                  # High-res transparent emblems
├── data/
│   ├── faqs.json                   # 72 canonical LPU FAQ knowledge entries
│   ├── paraphrases.csv             # 288 query benchmark suite (dev & test splits)
│   ├── out_of_scope.csv            # 60 out-of-scope & adversarial queries
│   └── query_logs.db               # SQLite telemetry & feedback database
├── desktop/                        # Electron desktop application source
│   ├── main.js                     # Main window, IPC & custom titlebar controls
│   ├── preload.js                  # Context-isolated IPC bridge
│   ├── package.json                # electron-builder packaging config
│   └── build/                      # App icons (icon.ico, icon.png)
├── src/
│   ├── config.py                   # Global paths, weights, and constants
│   ├── preprocess.py               # Hinglish slang normalizer & stemmer
│   ├── privacy.py                  # PII regex scrubber (Reg No, Phone, Email)
│   ├── fallback.py                 # Calibrated confidence gate & router
│   ├── validate_data.py            # Dataset validator & provenance checker
│   ├── retrievers/                 # Information retrieval engines
│   │   ├── keyword.py              # Normalized word overlap engine
│   │   ├── tfidf.py                # Sublinear TF-IDF cosine similarity
│   │   ├── embedding.py            # Dense MiniLM + FAISS vector search
│   │   └── hybrid.py               # Convex linear fusion engine
│   └── llm/                        # Grounded conversational engine
│       ├── groq_client.py          # LPU campus knowledge & Groq polisher
│       ├── grounding_check.py      # AST entity grounding verifier
│       └── evaluate_grounding.py   # Grounding & safety audit suite
├── Dockerfile                      # Production container spec (HF Spaces / Render)
├── requirements.txt                # Python package dependencies
├── vercel.json                     # Vercel serverless deployment specification
└── README.md                       # Comprehensive documentation
```

---

## 🛡️ Responsible AI & Ethical Guardrails

- **Zero Hallucination Tolerance**: LLM responses are verified against the canonical FAQ text using regex-based AST entity verification. If an LLM attempts to fabricate a room number, date, or fee amount, the polish is discarded and the verified canonical answer is served.
- **Strict Fallback / Rejection Gate**: When a student query's top confidence score falls below the calibrated threshold ($\tau^* = 0.36$), the system safely abstains from guessing and routes the student directly to the official university helpdesk.
- **Privacy Protection**: All student identifiers (*Registration Numbers, Phone Numbers, Email Addresses*) are automatically redacted in-memory prior to logging and embedding computation.
- **Hinglish Inclusivity**: The preprocessing pipeline recognizes and normalizes common North Indian and campus slang (*kab, kaise, kitna, bhai, duplicate, attendance*) to ensure equitable accessibility for all students.

---

## 👥 Authors & Acknowledgments

- **Lead Developer**: [Roopesh Kosuri](https://github.com/Roopesh-kosuri)
- **Institution**: Lovely Professional University (LPU), Punjab, India
- **Course**: CSE276 Artificial Intelligence Foundations
- **Academic Year**: 2026

*CampusAssist is an independent academic research and student welfare initiative designed for Lovely Professional University.*
