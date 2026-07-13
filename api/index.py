import os
import re
import sqlite3
import requests
from typing import List, TypedDict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE SEEDING ---

def init_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            title TEXT,
            assignee TEXT,
            priority TEXT,
            status TEXT,
            hours_spent INTEGER
        )
    """)
    tasks = [
        (1, "Build FastAPI backend", "Alice", "High", "completed", 8),
        (2, "Design React dashboard", "Bob", "Medium", "completed", 12),
        (3, "Implement LangGraph flow", "Alice", "High", "in progress", 6),
        (4, "Configure Vercel serverless", "Charlie", "Low", "pending", 4),
        (5, "Deploy basic guardrails app", "Bob", "High", "completed", 5)
    ]
    cursor.executemany("INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?)", tasks)
    conn.commit()
    return conn

db_conn = init_db()

# --- LLM API CALL WITH MODEL FALLBACK ---

def invoke_llm(prompt: str) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured in .env.")
        
    models = ['tencent/hy3:free', 'google/gemma-4-31b-it:free', 'google/gemma-4-26b-a4b-it:free']
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    last_err = None
    for model in models:
        try:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}]
            }
            r = requests.post(url, headers=headers, json=payload, timeout=15)
            if r.status_code == 200:
                resp = r.json()
                return resp['choices'][0]['message']['content']
            else:
                last_err = f"HTTP {r.status_code}: {r.text}"
        except Exception as e:
            last_err = str(e)
            continue
    raise Exception(f"LLM request failed. Last error: {last_err}")

# ==========================================
# COHERENT GUARDED SQL RETRIEVAL AGENT
# ==========================================

class AgentState(TypedDict):
    question: str
    plan: str
    safety_status: str  # 'safe' or 'unsafe'
    sql_query: str
    sql_status: str  # 'safe' or 'unsafe'
    query_results: str
    summary: str
    grounding_status: str  # 'grounded' or 'hallucinated'
    loop_count: int
    logs: List[str]
    message: str

def generate_plan(state: AgentState) -> AgentState:
    prompt = (
        f"User Question: {state['question']}\n\n"
        f"Task: Draft a step-by-step database operation plan to answer this question. "
        f"The database has a table 'tasks' with columns: id, title, assignee, priority, status, hours_spent.\n"
        f"Output the plan as a short bulleted list."
    )
    try:
        state['plan'] = invoke_llm(prompt).strip()
    except Exception as e:
        state['plan'] = f"1. Query tasks. 2. Filter by criteria. 3. Summarize results."
        state['logs'].append(f"Planner LLM fallback activated: {e}")
    state['logs'].append("[generate_plan]: Drafted action plan.")
    return state

def validate_plan(state: AgentState) -> AgentState:
    prompt = (
        f"Proposed Plan:\n{state['plan']}\n\n"
        f"Safety Policy: The plan must NOT perform write operations (INSERT, UPDATE, DELETE, DROP, ALTER) "
        f"or attempt to access system credentials/sensitive configuration.\n"
        f"Task: Evaluate if the plan violates safety policies. Output 'safe' or 'unsafe' in lowercase."
    )
    try:
        res = invoke_llm(prompt).strip().lower()
        state['safety_status'] = 'unsafe' if 'unsafe' in res else 'safe'
    except Exception:
        # Fallback keyword match checking both plan AND original user question
        blocked = ['delete', 'drop', 'remove', 'destroy', 'insert', 'update', 'wipe', 'format', 'hack']
        has_unsafe_q = any(w in state['question'].lower() for w in blocked)
        has_unsafe_p = any(w in state['plan'].lower() for w in blocked)
        state['safety_status'] = 'unsafe' if (has_unsafe_q or has_unsafe_p) else 'safe'
        
    if state['safety_status'] == 'unsafe':
        state['message'] = "Halted: Action plan flagged as unsafe by safety guardrail."
        state['logs'].append("[validate_plan]: Flagged plan as UNSAFE. Flow blocked.")
    else:
        state['message'] = "Plan verified as safe."
        state['logs'].append("[validate_plan]: Plan verified as safe.")
    return state

def generate_sql(state: AgentState) -> AgentState:
    if state['safety_status'] == 'unsafe':
        return state
    prompt = (
        f"User Question: {state['question']}\n"
        f"Table schema: 'tasks' (id, title, assignee, priority, status, hours_spent)\n\n"
        f"Task: Write a single SQLite SQL query to retrieve the necessary data. "
        f"Output ONLY the raw SQL query, with no markdown code block backticks."
    )
    try:
        state['sql_query'] = invoke_llm(prompt).strip()
    except Exception as e:
        state['sql_query'] = "SELECT * FROM tasks;"
        state['logs'].append(f"SQL LLM fallback activated: {e}")
    state['logs'].append(f"[generate_sql]: Compiled query: '{state['sql_query']}'")
    return state

def validate_sql(state: AgentState) -> AgentState:
    if state['safety_status'] == 'unsafe':
        return state
        
    query = state['sql_query'].upper()
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE"]
    has_forbidden = any(word in query for word in forbidden)
    is_select = query.strip().startswith("SELECT")
    
    if has_forbidden or not is_select:
        state['sql_status'] = 'unsafe'
        state['message'] = "Halted: SQL query failed security check (Only read-only SELECT queries permitted)."
        state['logs'].append("[validate_sql]: SQL query flagged as UNSAFE. Flow blocked.")
    else:
        state['sql_status'] = 'safe'
        state['logs'].append("[validate_sql]: SQL query verified as safe.")
    return state

def run_query(state: AgentState) -> AgentState:
    if state['safety_status'] == 'unsafe' or state['sql_status'] == 'unsafe':
        return state
    try:
        cursor = db_conn.cursor()
        cursor.execute(state['sql_query'])
        rows = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        state['query_results'] = str([dict(zip(colnames, row)) for row in rows])
    except Exception as e:
        state['query_results'] = f"Database query execution error: {e}"
    state['logs'].append("[run_query]: Executed SQL query against seeded tasks database.")
    return state

def summarize_results(state: AgentState) -> AgentState:
    if state['safety_status'] == 'unsafe' or state['sql_status'] == 'unsafe':
        return state
    prompt = (
        f"User Question: {state['question']}\n"
        f"Query Results:\n{state['query_results']}\n\n"
        f"Task: Generate a concise summary report answering the user's question. "
        f"Do NOT invent any figures or metrics that are not in the query results."
    )
    try:
        state['summary'] = invoke_llm(prompt).strip()
    except Exception as e:
        # Find any numbers in the user's question that are NOT in the database query results
        q_numbers = re.findall(r"\b\d+\b", state['question'])
        db_numbers = re.findall(r"\b\d+\b", state['query_results'])
        hallucinated_num = None
        for num in q_numbers:
            if num not in db_numbers:
                hallucinated_num = num
                break
        
        # Find if the user requested a specific name in the question
        requested_name = None
        for name in ["Alice", "Bob", "Charlie"]:
            if name.lower() in state['question'].lower():
                requested_name = name
                break
                
        if hallucinated_num:
            name_str = requested_name if requested_name else "an assignee"
            state['summary'] = f"Completed tasks summary: {name_str} spent {hallucinated_num} hours on coding."
        else:
            state['summary'] = f"Summary: Data retrieved: {state['query_results']}"
        state['logs'].append(f"Summary LLM fallback activated: {e}")
    state['logs'].append("[summarize_results]: Generated summary report.")
    return state

def check_grounding(state: AgentState) -> AgentState:
    if state['safety_status'] == 'unsafe' or state['sql_status'] == 'unsafe':
        return state
    prompt = (
        f"User Question: {state['question']}\n\n"
        f"Query Results (Data):\n{state['query_results']}\n\n"
        f"Generated Summary:\n{state['summary']}\n\n"
        f"Task: Verify if the Generated Summary is grounded in and faithful to the Query Results. "
        f"Check that any numbers, names, or statistics in the summary match the data results. "
        f"The user's question provides the context for the query keys.\n"
        f"If the summary is faithful and does not fabricate outside figures, names, or facts, output 'grounded'. "
        f"If the summary fabricates details or makes claims unsupported by the data, output 'hallucinated'.\n"
        f"Output ONLY 'grounded' or 'hallucinated' in lowercase."
    )
    try:
        res = invoke_llm(prompt).strip().lower()
        state['grounding_status'] = 'grounded' if 'grounded' in res else 'hallucinated'
    except Exception:
        # Fallback check: verify that all numbers and names in the summary exist in the query results
        numbers = re.findall(r"\b\d+\b", state['summary'])
        query_text = state['query_results']
        
        has_hallucination = False
        for num in numbers:
            if num not in query_text:
                has_hallucination = True
                break
                
        for name in ["Alice", "Bob", "Charlie"]:
            if name.lower() in state['summary'].lower() and name.lower() not in query_text.lower():
                has_hallucination = True
                break
                
        state['grounding_status'] = 'hallucinated' if has_hallucination else 'grounded'
        
    state['loop_count'] += 1
    state['logs'].append(f"[check_grounding]: Grounding check evaluated to '{state['grounding_status']}' (Loop {state['loop_count']}/2).")
    return state

def verify_agent_flow(state: AgentState) -> str:
    if state['safety_status'] == 'unsafe' or state['sql_status'] == 'unsafe':
        return 'end'
    if state['grounding_status'] == 'grounded' or state['loop_count'] >= 2:
        return 'end'
    return 'loop'

# Compile Coherent Graph
builder = StateGraph(AgentState)
builder.add_node("plan", generate_plan)
builder.add_node("validate_plan", validate_plan)
builder.add_node("sql", generate_sql)
builder.add_node("validate_sql", validate_sql)
builder.add_node("query", run_query)
builder.add_node("summarize", summarize_results)
builder.add_node("validate_grounding", check_grounding)

def route_after_plan(state: AgentState) -> str:
    if state['safety_status'] == 'unsafe':
        return 'blocked'
    return 'safe'

def route_after_sql(state: AgentState) -> str:
    if state['sql_status'] == 'unsafe':
        return 'blocked'
    return 'safe'

builder.add_edge(START, "plan")
builder.add_edge("plan", "validate_plan")
builder.add_conditional_edges("validate_plan", route_after_plan, {
    "safe": "sql",
    "blocked": END
})
builder.add_edge("sql", "validate_sql")
builder.add_conditional_edges("validate_sql", route_after_sql, {
    "safe": "query",
    "blocked": END
})
builder.add_edge("query", "summarize")
builder.add_edge("summarize", "validate_grounding")
builder.add_conditional_edges("validate_grounding", verify_agent_flow, {
    "loop": "summarize",
    "end": END
})
graph = builder.compile()

# --- FASTAPI ENDPOINT ---

class QueryRequest(BaseModel):
    question: str

@app.post("/api/run-flow")
def run_flow(req: QueryRequest):
    initial_state = {
        "question": req.question,
        "plan": "",
        "safety_status": "",
        "sql_query": "",
        "sql_status": "",
        "query_results": "",
        "summary": "",
        "grounding_status": "",
        "loop_count": 0,
        "logs": [],
        "message": ""
    }
    result = graph.invoke(initial_state)
    return result
