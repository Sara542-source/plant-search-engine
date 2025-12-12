# backend/models/lsa/app.py
from fastapi import FastAPI
from pydantic import BaseModel

import lsa_search

app = FastAPI(title="Plant Search Engine API")

class QueryRequest(BaseModel):
    query: str

@app.post("/search")
def search(query_request: QueryRequest):
    query = query_request.query
    results="HELLO I AM FASTAPI AND I AM WORKING"
    return {"query": query, "results": results}
