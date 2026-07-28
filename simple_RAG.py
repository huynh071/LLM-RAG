from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import openai
import requests


# Step 1: Prepare documents
documents = [
    "Our refund policy: 30 days, full refund with receipt.",
    "Shipping takes 3-5 business days for domestic orders.",
    "We accept Visa, Mastercard, and PayPal.",
    "Customer support: support@example.com or call 1-800-HELP"
]

# Step 2: Create embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')  # 384-dim embeddings
embeddings = model.encode(documents)

# Step 3: Build FAISS index
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(np.array(embeddings))

# Step 4: Retrieval function
def retrieve(query, k=2):
    query_embedding = model.encode([query])
    distances, indices = index.search(query_embedding, k)
    return [documents[i] for i in indices[0]]

# Step 5: RAG function
def rag_query(question):
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
        "http://127.0.0.1:11434/v1/chat/completions",
        json={
            "model": "qwen3.6",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.2,
        },
    )

    return response.json()["choices"][0]["message"]["content"]

# Test it
print(rag_query("What payment methods are acceptable?"))