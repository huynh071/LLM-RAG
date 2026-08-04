
import os
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from read_pdf import retrieved_chunks
from pathlib import Path
load_dotenv()

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://127.0.0.1:11434",
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen3:0.6b",
)

app = FastAPI(title="RAG API")


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]



# Step 5: RAG function
def rag_query(question: str) -> tuple[str, list[str]]:
    # Retrieve relevant docs
    results = retrieved_chunks(question)
    context = [item["content"] for item in results]
    # Create prompt
    prompt = f"""Answer the question based only on this context:

Context:
{chr(10).join(context)}

Question: {question}

Answer:"""

    # Generate response
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "max_tokens": 1000,
            "temperature": 0.2,
        },
    )

    return response.json()["message"]["content"], context

@app.get("/api/health")
def health():
    return {"status": "healthy"}

@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        answer, sources = rag_query(request.prompt)
        return ChatResponse(answer=answer, sources=sources)
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama request failed: {exc}",
        ) from exc
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Ollama returned an unexpected response.",
        ) from exc
