
import os
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from read_pdf import read_pdf
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

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_PDF = PROJECT_ROOT / "resources" / "file1.pdf"

# Step 1: Prepare documents
# documents = [
#     "Our refund policy: 30 days, full refund with receipt.",
#     "Shipping takes 3-5 business days for domestic orders.",
#     "We accept Visa, Mastercard, and PayPal.",
#     "Customer support: support@example.com or call 1-800-HELP"
# ]

documents = [read_pdf(DEFAULT_PDF)]

# Step 2: Create embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')  # 384-dim embeddings
embeddings = model.encode(documents)

# Step 3: Build FAISS index
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(np.array(embeddings))

app = FastAPI(title="RAG API")


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]


# Step 4: Retrieval function
def retrieve(query: str, k: int = 2) -> list[str]:
    query_embedding = model.encode([query])
    k = min(k, len(documents))
    _, indices = index.search(query_embedding, k)
    return [documents[i] for i in indices[0]]

# Step 5: RAG function
def rag_query(question: str) -> tuple[str, list[str]]:
    # Retrieve relevant docs
    context = retrieve(question)
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
