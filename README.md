# NL2SQL Clinic Chatbot

A production-ready **Natural Language to SQL** chatbot for a clinic management database,
built with **Vanna AI 2.0** and **FastAPI**.

Users ask questions in plain English. The system generates SQL, validates it, executes it
against a SQLite database, and returns structured results with an optional Plotly chart.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| AI Agent | Vanna 2.0 (`Agent` + `DemoAgentMemory`) |
| LLM Provider | **Groq** – `llama-3.3-70b-versatile` (free tier) |
| API Framework | FastAPI |
| Database | SQLite (`clinic.db`) |
| Charting | Plotly |

> **LLM Choice:** Groq was selected because it offers a generous free tier, is OpenAI-compatible
> (easy to swap), and the `llama-3.3-70b-versatile` model produces high-quality SQL.

---

## Project Structure

```
nl2sql_project/
├── setup_database.py   # Creates clinic.db schema + inserts dummy data
├── vanna_setup.py      # Vanna 2.0 Agent initialisation (singleton)
├── seed_memory.py      # Seeds DemoAgentMemory with 15 Q→SQL pairs
├── sql_validator.py    # SELECT-only SQL safety validator
├── main.py             # FastAPI application (POST /chat, GET /health)
├── requirements.txt    # All Python dependencies
├── .env.example        # Environment variable template
├── README.md           # This file
└── RESULTS.md          # Test results for 20 benchmark questions
```

---

## Prerequisites

- Python 3.10 or higher
- A **free Groq API key** → sign up at <https://console.groq.com>

---

## Setup Instructions

### 1. Clone / Download the project

```bash
git clone <your-repo-url>
cd nl2sql_project
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
# macOS / Linux
source venv/bin/activate
# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your Groq API key:

```dotenv
GROQ_API_KEY=your_groq_api_key_here
DB_PATH=clinic.db
```

> **Never commit your `.env` file** – it is listed in `.gitignore`.

### 5. Create the database and insert dummy data

```bash
python setup_database.py
```

Expected output:
```
✅ Database created: clinic.db
   Created 200 patients, 15 doctors, 500 appointments, 281 treatments, 300 invoices.
```

### 6. Seed agent memory with example Q&A pairs

```bash
python seed_memory.py
```

Expected output:
```
Seeding 15 question–SQL pairs into DemoAgentMemory…
  [01] How many patients do we have?
  [02] List all patients with their city and gender
  ...
  [15] Show patient registration trend by month

✅ Agent memory now contains 15 seeded entries.
```

> **Note:** `DemoAgentMemory` is in-process and does not persist across server restarts.
> Re-run `seed_memory.py` each time you start the server for best results.
> For production, replace with a persistent vector store (ChromaDB, Qdrant, etc.).

### 7. Start the API server

```bash
uvicorn main:app --port 8000 --reload
```

The API is now running at `http://localhost:8000`

---

## One-Line Quickstart (from scratch)

```bash
pip install -r requirements.txt && python setup_database.py \
  && python seed_memory.py && uvicorn main:app --port 8000
```

---

## API Documentation

Interactive Swagger UI: `http://localhost:8000/docs`
ReDoc: `http://localhost:8000/redoc`

---

### `POST /chat`

Ask a natural language question. The agent generates SQL, validates it, executes it,
and returns structured results.

**Request:**
```json
{
  "question": "Show me the top 5 patients by total spending"
}
```

**Response:**
```json
{
  "message": "Here are the top 5 patients by total spending...",
  "sql_query": "SELECT p.first_name, p.last_name, ROUND(SUM(i.total_amount),2) AS total_spending FROM invoices i JOIN patients p ON p.id = i.patient_id GROUP BY p.id ORDER BY total_spending DESC LIMIT 5",
  "columns": ["first_name", "last_name", "total_spending"],
  "rows": [
    ["Swati", "Khanna", 74503.41],
    ["Meera", "Verma", 46415.91],
    ["Nandita", "Ghosh", 44745.11],
    ["Rahul", "Dubey", 41362.49],
    ["Tarun", "Tiwari", 38981.34]
  ],
  "row_count": 5,
  "chart": null,
  "chart_type": null,
  "error": null
}
```

**cURL example:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How many patients do we have?"}'
```

**Error response (invalid SQL):**
```json
{
  "message": "The AI generated a query that failed security validation.",
  "sql_query": "DROP TABLE patients",
  "error": "Forbidden SQL statement detected: 'DROP'. Only read-only SELECT queries are permitted.",
  "columns": null,
  "rows": null
}
```

---

### `GET /health`

Health check endpoint. Returns database connectivity status and memory item count.

**Response:**
```json
{
  "status": "ok",
  "database": "connected",
  "agent_memory_items": 15,
  "db_path": "clinic.db"
}
```

**cURL example:**
```bash
curl http://localhost:8000/health
```

---

## Architecture Overview

```
User Question (HTTP POST /chat)
         │
         ▼
   FastAPI Backend (main.py)
         │
         ▼
   Vanna 2.0 Agent (vanna_setup.py)
   ┌─────────────────────────────────┐
   │  OpenAILlmService (Groq)        │  ← generates SQL from question
   │  DemoAgentMemory                │  ← retrieves similar past Q→SQL pairs
   │  ToolRegistry                   │
   │   ├── RunSqlTool                │  ← executes SQL via SqliteRunner
   │   ├── VisualizeDataTool         │  ← generates Plotly charts
   │   ├── SaveQuestionToolArgsTool  │  ← saves successful Q→SQL to memory
   │   └── SearchSavedCorrectTool    │  ← searches memory for similar questions
   └─────────────────────────────────┘
         │
         ▼
   SQL Validator (sql_validator.py)
   ├── SELECT-only enforcement
   ├── Forbidden keyword check
   └── System table protection
         │
         ▼
   SQLite (clinic.db via SqliteRunner)
         │
         ▼
   JSON Response: message + sql + columns + rows + chart
```

### Key Design Decisions

**Vanna 2.0 Agent pattern** – The assignment explicitly requires Vanna 2.0's `Agent`-based
architecture (`DemoAgentMemory`, `RunSqlTool`, `ToolRegistry`). The old `vn.train()` /
`VannaBase` / ChromaDB pattern from Vanna 0.x is not used anywhere.

**SQL validation layer** – All AI-generated SQL is validated before execution. Only `SELECT`
statements are permitted. Dangerous keywords, DML/DDL statements, and system table access
are rejected with a clear error message returned to the caller.

**Memory seeding** – `DemoAgentMemory` is pre-loaded with 15 high-quality question→SQL pairs
via `seed_memory.py`. This gives the agent context for common clinic queries even before any
user interactions have occurred.

**In-process memory** – `DemoAgentMemory` is a lightweight in-memory store suitable for
development and testing. For production, swap it for a persistent implementation backed by
ChromaDB, Qdrant, or another vector database.

---

## Database Schema

```
patients        (id, first_name, last_name, email, phone, date_of_birth, gender, city, registered_date)
doctors         (id, name, specialization, department, phone)
appointments    (id, patient_id→patients, doctor_id→doctors, appointment_date, status, notes)
treatments      (id, appointment_id→appointments, treatment_name, cost, duration_minutes)
invoices        (id, patient_id→patients, invoice_date, total_amount, paid_amount, status)
```

---

## Example Questions to Try

```
How many patients do we have?
List all doctors and their specializations
Which doctor has the most appointments?
What is the total revenue?
Show revenue by doctor
Top 5 patients by spending
Average treatment cost by specialization
Show monthly appointment count for the past 6 months
Which city has the most patients?
List patients who visited more than 3 times
Show unpaid invoices
What percentage of appointments are no-shows?
Show the busiest day of the week for appointments
Revenue trend by month
Compare revenue between departments
Show patient registration trend by month
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `GROQ_API_KEY not set` | Add your key to `.env` and re-run |
| `clinic.db not found` | Run `python setup_database.py` first |
| Agent returns no SQL | Re-run `python seed_memory.py` (memory is reset on restart) |
| `ModuleNotFoundError: vanna` | Run `pip install -r requirements.txt` |
| Port 8000 already in use | Use `uvicorn main:app --port 8001` |


