# LLM-RAG

LLM-RAG is a small, local Retrieval-Augmented Generation (RAG) application for
asking questions about a PDF. It converts the document to Markdown, retrieves
the most relevant passages with Sentence Transformers and FAISS, and gives
those passages to an Ollama model to generate an answer.

The complete application runs with Docker Compose and provides a browser-based
chat interface at `http://localhost:8080`. The language model, embedding model,
and document content remain local to the machine running the containers.

## Features

- Browser chat interface served by Nginx
- FastAPI JSON API
- PDF-to-Markdown extraction with MarkItDown
- Heading-aware and overlapping text chunks
- Local embeddings with `sentence-transformers/all-MiniLM-L6-v2`
- In-memory cosine-similarity search with FAISS
- Local answer generation with Ollama
- Persistent Docker volumes for downloaded Ollama and Hugging Face models
- Configurable Ollama generation model

## How it works

```text
resources/file1.pdf
        |
        v
MarkItDown PDF extraction
        |
        v
Markdown header split + 1,000-character chunks (150-character overlap)
        |
        v
all-MiniLM-L6-v2 normalized embeddings
        |
        v
FAISS inner-product search (up to 3 chunks)
        |
        v
Question + retrieved context -> Ollama -> answer
```

For each chat request, the backend:

1. Reads `resources/file1.pdf` and converts it to Markdown.
2. Splits the Markdown by headings and then into smaller overlapping chunks.
3. Embeds the chunks and builds an in-memory FAISS index.
4. Retrieves up to three chunks most similar to the question.
5. Instructs Ollama to answer using only those chunks.
6. Returns the generated answer and the retrieved chunk text to the browser.

The index is currently rebuilt for every question. This keeps the example
simple and reprocesses the configured document on each request, but it is less
efficient than building and persisting the index once.

## Architecture

```text
Browser -> http://localhost:8080
             |
             v
        Nginx (`web`)
          |       |
          |       +-- serves HTML, CSS, and JavaScript
          |
          +-- /api/* -> FastAPI (`rag`:8000)
                            |
                            +-- PDF + Sentence Transformers + FAISS
                            |
                            +-- Ollama (`ollama`:11434)
```

Only port `8080` is published to the host. FastAPI and Ollama communicate on
the internal Compose network.

## Project structure

```text
LLM-RAG/
├── .env.example           # Optional Ollama model configuration
├── compose.yaml           # Web, RAG API, Ollama, and model-pull services
├── Dockerfile             # Python/FastAPI backend image
├── pyproject.toml         # Python metadata and dependencies
├── read_pdf.py            # PDF extraction, chunking, embedding, and retrieval
├── resources/
│   └── file1.pdf          # Default knowledge document
├── simple_RAG.py          # FastAPI endpoints and Ollama prompt
├── uv.lock                # Locked Python dependencies
└── web/
    ├── Dockerfile
    ├── app.js
    ├── index.html
    ├── nginx.conf
    └── styles.css
```

## Prerequisites

For the recommended setup, install:

- Docker Desktop, or Docker Engine with the Compose v2 plugin
- Git, if cloning the repository
- An internet connection for the initial image, dependency, and model downloads
- Enough free memory and disk space for the selected Ollama model

Verify Docker is ready:

```sh
docker --version
docker compose version
docker info
```

Use `docker compose` with a space; the older `docker-compose` command is not
required.

## Quick start with Docker

### 1. Get the project

```sh
git clone https://github.com/huynh071/LLM-RAG.git
cd LLM-RAG
```

If the project is already downloaded, open a terminal in the directory that
contains `compose.yaml`.

### 2. Choose the Ollama model (optional)

The default model is `qwen3:0.6b`. To configure another model, copy the example
environment file:

macOS, Linux, WSL, or Git Bash:

```sh
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

Then set a valid Ollama model name in `.env`:

```dotenv
OLLAMA_MODEL=qwen3:0.6b
```

Larger models generally require more memory, disk space, and response time.

### 3. Start the application

For the first run, foreground mode makes the download progress easy to see:

```sh
docker compose up --build
```

To run it in the background instead:

```sh
docker compose up --build -d
```

Compose starts four services:

| Service | Purpose |
| --- | --- |
| `web` | Serves the chat UI and proxies `/api/*` to FastAPI |
| `rag` | Extracts and retrieves PDF content and exposes the API |
| `ollama` | Runs the local language model server |
| `ollama-pull` | Downloads the configured Ollama model once, then exits |

The first start can take several minutes. The Ollama model is downloaded before
the RAG service starts, and the embedding model is downloaded when the first
question is processed. Both model caches are preserved in Docker volumes.

### 4. Open and use the chat

Open [http://localhost:8080](http://localhost:8080), wait for the status badge
to show `RAG online`, and ask a question whose answer should be in the PDF.

The first question may be slower while the embedding model is downloaded and
the first index is built. Expand the retrieved-sources section under an answer
to inspect the passages sent to Ollama.

### 5. Stop the application

If it is running in the foreground, press `Ctrl+C`. Then run:

```sh
docker compose down
```

This removes the containers and network but keeps downloaded models. Avoid
`docker compose down --volumes` unless the model caches should also be deleted.

## Use a different PDF

The current implementation reads one PDF from `resources/file1.pdf`. There is
no upload screen yet, so select the document before building the RAG image.

### Option A: replace the default file

Copy a new PDF over `resources/file1.pdf`.

macOS, Linux, WSL, or Git Bash:

```sh
cp /path/to/your-document.pdf resources/file1.pdf
```

PowerShell:

```powershell
Copy-Item C:\path\to\your-document.pdf resources\file1.pdf
```

Rebuild the backend so Docker copies the new file into the image:

```sh
docker compose up -d --build rag
```

If the stack is not running, start the complete application instead:

```sh
docker compose up --build
```

The next question will use the replacement PDF.

### Option B: keep the PDF's filename

1. Put the PDF in `resources/`, for example `resources/employee-handbook.pdf`.
2. Change `DEFAULT_PDF` in `read_pdf.py`:

   ```python
   DEFAULT_PDF = PROJECT_ROOT / "resources" / "employee-handbook.pdf"
   ```

3. Rebuild the backend:

   ```sh
   docker compose up -d --build rag
   ```

The path is resolved relative to the project, so it works both locally and at
`/app/resources/...` inside the backend container.

### Local-development behavior after a PDF change

When FastAPI is running directly on the host rather than in Docker, the PDF is
read from disk for every request. Replacing the configured file does not
require an application rebuild or restart; ask the next question after the
copy finishes.

### PDF recommendations

- Use a valid `.pdf` file; `convert_to_markdown` rejects other extensions.
- Text-based PDFs produce better results than image-only scans. Scanned files
  need OCR before this pipeline can retrieve their text reliably.
- Keep headings in source documents when possible. Heading text is included in
  the embedding input and can improve retrieval.
- Ask specific questions using terminology that appears in the document.
- Do not place sensitive documents in a deployment that untrusted users can
  access. Retrieved text is returned by the API and displayed in the UI.

## Use multiple PDFs or other knowledge resources

The checked-in code supports one PDF at a fixed path. It does not currently
include multi-file discovery, a file uploader, URL crawling, a database
connector, or a persistent vector store.

For a quick no-code workaround, combine the source material into one PDF and
use that file as `resources/file1.pdf`.

To extend the application properly, keep the retrieval pipeline's input
contract simple: every source should become one or more LangChain `Document`
chunks before `build_index(chunks)` is called.

For multiple PDFs:

1. Discover the files with `Path("resources").glob("*.pdf")`.
2. Run `convert_to_markdown` and `chunk_markdown` for each file.
3. Add the filename to each chunk's metadata, for example
   `chunk.metadata["source"] = pdf_path.name`.
4. Combine all chunks and build one FAISS index.
5. Return the source metadata from the API if filename-level citations are
   needed in the UI.

For Markdown, text, web pages, object storage, or database records:

1. Add an appropriate loader in `read_pdf.py` or a separate ingestion module.
2. Normalize the loaded content to Markdown or plain text.
3. Split it into chunks and attach metadata such as source name, URL, page,
   record ID, or last-updated time.
4. Pass the combined chunks through the existing `build_index` and `retrieve`
   functions.

`MarkItDown` can convert more than PDFs, but this project installs its PDF
extras and explicitly validates `.pdf` input. Other file types therefore need
both an appropriate dependency/loader and a change to the current validation
logic.

For a larger or frequently updated knowledge base, build the embeddings during
an ingestion step and store them in a persistent vector database instead of
re-extracting and re-embedding every source for every question.

## Run the API locally for development

Docker Compose is the easiest way to run the full web application. To run only
the Python API on the host, install:

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/) running on the host

Install the locked dependencies and pull the default model:

```sh
uv sync --frozen
ollama pull qwen3:0.6b
```

Start Ollama if the platform does not already run it as a background service,
then start FastAPI:

```sh
uv run uvicorn simple_RAG:app --reload --host 127.0.0.1 --port 8000
```

By default, the local API calls Ollama at `http://127.0.0.1:11434`. Environment
variables can override the model or server:

```sh
OLLAMA_MODEL=qwen3:0.6b \
OLLAMA_BASE_URL=http://127.0.0.1:11434 \
uv run uvicorn simple_RAG:app --reload --port 8000
```

This starts the API only; the checked-in Nginx frontend is wired for the Docker
Compose network. Use `http://127.0.0.1:8000/docs` for FastAPI's interactive API
documentation during local development.

## API usage

All public requests in the Compose setup go through Nginx on port `8080`.

### Health check

```sh
curl http://localhost:8080/api/health
```

Expected response:

```json
{"status":"healthy"}
```

This confirms the FastAPI process is responding. It does not validate the PDF,
build the FAISS index, or make a test request to Ollama.

### Ask a question

```sh
curl -X POST http://localhost:8080/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"What does the document say about this topic?"}'
```

Example response shape:

```json
{
  "answer": "An answer generated from the retrieved context.",
  "sources": [
    "The first retrieved PDF passage...",
    "The second retrieved PDF passage...",
    "The third retrieved PDF passage..."
  ]
}
```

The exact answer and passages depend on the PDF and the selected model.

The `prompt` field is required and must contain between 1 and 4,000 characters.
Invalid requests return HTTP `422`; failures while contacting or decoding an
Ollama response return HTTP `502`.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_MODEL` | `qwen3:0.6b` | Ollama model downloaded and used for answers |
| `OLLAMA_BASE_URL` | `http://ollama:11434` in Compose; `http://127.0.0.1:11434` otherwise | Ollama API address used by FastAPI |
| `HF_HOME` | `/home/app/.cache/huggingface` in Compose | Embedding-model cache directory |

Do not set `OLLAMA_BASE_URL` to `127.0.0.1` in the `rag` container. There,
`127.0.0.1` refers to the RAG container itself; the Ollama service is available
at `http://ollama:11434`.

After changing `OLLAMA_MODEL` in `.env`, recreate the relevant services:

```sh
docker compose up -d ollama-pull
docker compose up -d --build rag
```

Monitor the model download with:

```sh
docker compose logs -f ollama-pull
```

## Useful commands

```sh
# Show service state
docker compose ps

# Follow application logs
docker compose logs -f web rag ollama ollama-pull

# Rebuild the backend after Python or resource changes
docker compose up -d --build rag

# Rebuild the frontend after web changes
docker compose up -d --build web

# List locally cached Ollama models
docker compose exec ollama ollama list

# Validate the resolved Compose configuration
docker compose config
```

## Troubleshooting

### The first question is very slow

The first request downloads the Sentence Transformer model if it is not cached,
then converts the PDF, embeds all chunks, and builds the FAISS index. Follow the
backend logs:

```sh
docker compose logs -f rag
```

Subsequent questions avoid the model download but still rebuild the document
index with the current implementation.

### The page does not open or says `RAG offline`

```sh
docker compose ps
docker compose logs web rag ollama-pull ollama
curl http://localhost:8080/api/health
```

The web service waits for the RAG health check, and the RAG service waits for
the Ollama model-pull job to finish.

### A different PDF is not being used

The PDF is copied into the backend image; it is not bind-mounted. Confirm the
path in `read_pdf.py`, then rebuild the RAG image:

```sh
docker compose up -d --build rag
```

If Docker still reuses an unexpected layer, force a one-time clean rebuild:

```sh
docker compose build --no-cache rag
docker compose up -d rag
```

### PDF extraction fails or returns poor context

- Confirm the configured file exists and has a `.pdf` extension.
- Try extracting text from the PDF with another viewer to determine whether it
  contains selectable text.
- Run OCR on image-only scans before using them.
- Inspect `docker compose logs rag` for the MarkItDown error.

### The model download fails

Confirm the model name in `.env`, Docker's internet access, and the pull logs:

```sh
docker compose logs ollama ollama-pull
docker compose up ollama-pull
```

### Port 8080 is already in use

Change the host side of the mapping in `compose.yaml`, for example from
`"8080:80"` to `"8081:80"`, recreate `web`, and open
`http://localhost:8081`.

## Current limitations

- One PDF at a fixed path
- No browser upload or knowledge-source management
- Index rebuilt in memory for every request
- No conversation history; each request is independent
- Returned sources contain chunk text, not filenames or page-number citations
- CPU-only Compose configuration
- No authentication, authorization, rate limiting, or HTTPS

This is a learning and local-development project. Add persistent indexing,
source-aware citations, access controls, and operational safeguards before
using it as a public or production service.

## License

No license file is currently included.
