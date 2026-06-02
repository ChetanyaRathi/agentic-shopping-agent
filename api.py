from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime

import json
from fastapi.responses import StreamingResponse

from shopping_agent.pipeline import run, run_stream

app = FastAPI(title="Shopping Agent API")

# Allow React frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for recent searches
history_store = []

class SearchRequest(BaseModel):
    query: str
    budget: float = 0.10

class SearchResult(BaseModel):
    id: str
    query: str
    timestamp: str
    results: List[dict]
    cost_report: dict

@app.post("/api/search", response_model=SearchResult)
async def search(req: SearchRequest):
    # Run the shopping agent pipeline
    results, cost_report = await run(req.query, headless=True, verbose=True, budget=req.budget)
    
    # Format the results
    formatted_results = []
    for r in results:
        p = r.product
        formatted_results.append({
            "title": p.title,
            "price": f"{p.currency or ''}{p.price}" if p.price is not None else "N/A",
            "url": p.url,
            "color": p.color
        })
    
    # Store in history
    search_entry = {
        "id": str(uuid.uuid4()),
        "query": req.query,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "results": formatted_results,
        "cost_report": cost_report
    }
    history_store.insert(0, search_entry)
    
    return search_entry

@app.post("/api/search/stream")
async def search_stream(req: SearchRequest):
    async def event_generator():
        search_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        async for event in run_stream(req.query, headless=True, verbose=True, budget=req.budget):
            if event["type"] == "product":
                r = event["data"]
                p = r.product
                formatted_product = {
                    "title": p.title,
                    "price": f"{p.currency or ''}{p.price}" if p.price is not None else "N/A",
                    "url": p.url,
                    "color": p.color,
                    "score": r.score
                }
                data = json.dumps({"type": "product", "product": formatted_product})
                yield f"data: {data}\n\n"
                
            elif event["type"] == "done":
                formatted_results = []
                for r in event["ranked"]:
                    p = r.product
                    formatted_results.append({
                        "title": p.title,
                        "price": f"{p.currency or ''}{p.price}" if p.price is not None else "N/A",
                        "url": p.url,
                        "color": p.color,
                        "score": r.score
                    })
                
                final_data = {
                    "type": "done",
                    "id": search_id,
                    "query": req.query,
                    "timestamp": timestamp,
                    "results": formatted_results,
                    "cost_report": event["cost_report"]
                }
                data = json.dumps(final_data)
                yield f"data: {data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/history")
async def get_history():
    return [
        {
            "id": h["id"],
            "query": h["query"],
            "timestamp": h["timestamp"]
        } for h in history_store
    ]
