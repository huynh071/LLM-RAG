"""Convert a PDF document to Markdown with MarkItDown."""

import numpy as np
from pathlib import Path
from markitdown import MarkItDown
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from sentence_transformers import SentenceTransformer
import faiss


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_PDF = PROJECT_ROOT / "resources" / "file1.pdf"

# TODO: compare the performance with docling
def convert_to_markdown(pdf_path: Path) -> str:
    """Return the contents of a PDF as Markdown text."""
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, received: {pdf_path}")

    result = MarkItDown().convert(pdf_path)
    return result.text_content

def chunk_markdown(
    markdown: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
):
    headers_to_split_on = [
        ("#", "title"),
        ("##", "section"),
        ("###", "subsection"),
        ("####", "topic"),
    ]

    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,
    )

    sections = header_splitter.split_text(markdown)

    size_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=[
            "\n\n",  # Prefer paragraph boundaries
            "\n",    # Then line boundaries
            ". ",    # Then sentence-like boundaries
            " ",     # Then words
            "",      # Finally individual characters
        ],
        add_start_index=True,
    )

    chunks = size_splitter.split_documents(sections)

    for index, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = index

    return chunks


def format_chunk_for_embedding(chunk: any) -> str:
    """
    Include headings in the embedded text.

    This can improve retrieval when the user's question contains
    terminology that appears in the section heading.
    """

    metadata = chunk.metadata

    heading_parts = [
        metadata.get("title"),
        metadata.get("section"),
        metadata.get("subsection"),
        metadata.get("topic"),
    ]

    heading = " > ".join(
        str(item) for item in heading_parts if item
    )

    if heading:
        return f"Document section: {heading}\n\n{chunk.page_content}"

    return chunk.page_content


def build_index(chunks):
    """
    Create a simple in-memory vector index.

    For a production system, replace the NumPy array with
    FAISS, Chroma, Qdrant, Pinecone, Weaviate, or another
    persistent vector database.
    """

    model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    texts = [
        format_chunk_for_embedding(chunk)
        for chunk in chunks
    ]

    embeddings = model.encode_document(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    embeddings = np.ascontiguousarray(
        embeddings,
        dtype=np.float32,
    )

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    return model, index

def retrieve(
    question: str,
    chunks,
    index,
    model: SentenceTransformer,
    top_k: int = 3,
):
    """Return the top-k chunks ranked by cosine similarity."""

    if not question.strip():
        raise ValueError("The question cannot be empty.")

    query_embedding = model.encode_query(
        question,
        normalize_embeddings=True,
    )

    query_embedding = np.ascontiguousarray(
        query_embedding.reshape(1, -1),
        dtype=np.float32,
    )

    top_k = min(top_k, index.ntotal)
    scores, indices = index.search(query_embedding, top_k)

    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []

    for score, chunk_index in zip(scores[0], indices[0]):
        if chunk_index < 0:
            continue

        results.append({
            "score": float(score),
            "content": chunks[chunk_index].page_content,
            "metadata": chunks[chunk_index].metadata,
        })

    return results

def retrieved_chunks(question: str):
    markdown = convert_to_markdown(DEFAULT_PDF)
    chunks = chunk_markdown(
        markdown=markdown,
        chunk_size=1000,
        chunk_overlap=150,
    )

    embedding_model, index = build_index(chunks)

    retrieved_chunks = retrieve(
        question=question,
        chunks=chunks,
        index=index,
        model=embedding_model,
        top_k=3,
    )

    return retrieved_chunks

