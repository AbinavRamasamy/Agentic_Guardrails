from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from api.workflow import graph

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
