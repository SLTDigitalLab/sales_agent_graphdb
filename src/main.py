from fastapi import FastAPI
from pydantic import BaseModel
import asyncio 

from .agent_graph import app as agent_app

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str

# FastAPI app instance
api = FastAPI(
    title="AI Enterprise Agent API",
    description="API for interacting with the LangGraph agent."
)

@api.post("/chat", response_model=QueryResponse)
async def handle_chat(query: QueryRequest):
    """
    Receives a question and returns the agent's response.
    """
    print(f"Received question: {query.question}")

    final_state = await agent_app.ainvoke({"question": query.question})

    answer = final_state.get("generation", "Sorry, I couldn't generate a response.")

    print(f"Agent answer: {answer}")
    return QueryResponse(answer=answer)

@api.get("/")
async def root():
    return {"message": "AI Enterprise Agent API is running!"}

print("FastAPI app created.")

# If you want to run this file directly using `python src/main.py` (less common for FastAPI)
# you might add this block, but usually we run with uvicorn from the root.
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(api, host="0.0.0.0", port=8000)