# SQL Assistant

A guarded agentic database query assistant built with **LangGraph**, SQLite, and FastAPI. It processes natural language database queries, drafts execution plans, compiles them to SQL, retrieves rows, and validates outputs using prompt-based LLM guardrails.

---

## Architecture Overview

This project implements a multi-node state graph to manage query compilation, database retrieval, and safety validations:

```
[START] ──> Plan Draft ──> Plan Safety Audit ──> SQL Compilation ──> SQL Safety Audit ──> DB Query Execution ──> Report Summarization ──> Fact Grounding Audit ──> [END]
```

### Active Guardrails
1. **Plan Safety (LLM Audit)**: Checks the proposed plan against safety rules, blocking privilege bypass or data destruction schemes.
2. **SQL Safety (AST Parser)**: Validates the compiled SQL string to enforce read-only access, ensuring only `SELECT` queries are permitted.
3. **Fact Grounding (LLM Audit)**: Evaluates the compiled summary against raw SQLite database rows, looping back to correct hallucinated facts or blocking execution.

---

## File Structure

* **`api/workflow.py`**: Seed database, setup model choices, define workflow nodes, and compile the LangGraph StateGraph.
* **`api/index.py`**: Clean FastAPI endpoints serving Vercel serverless functions.
* **`src/`**: React Vite frontend source code.
* **`agentic_guardrails.ipynb`**: Interactive Jupyter Notebook demonstrating graph execution on sample questions.

---

## Local Setup

### Prerequisites
* Python 3.10+
* Node.js 18+
* An OpenRouter API Key (configured in your environment variable `OPENROUTER_API_KEY`)

### 1. Run Python Backend
Navigate to the root folder of this project:
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
export OPENROUTER_API_KEY="your_api_key_here"
uvicorn api.index:app --reload --port 8000
```

### 2. Run Frontend
In a new terminal window:
```bash
# Install dependencies
npm install

# Start Vite React server
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## Jupyter Notebook
To run the interactive notebook demo:
```bash
jupyter notebook agentic_guardrails.ipynb
```
The notebook imports the compiled graph directly from `api.workflow` to run validation trace test cases interactively.
