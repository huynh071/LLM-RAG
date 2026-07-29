# LLM-RAG: Simple Example

## Run with Docker Compose

The Compose stack contains:

- `rag`: the Python RAG example
- `ollama`: the local LLM server
- `ollama-pull`: a one-time setup container that downloads the configured model

Docker Desktop (or Docker Engine with Compose) is required.

Start the full stack:

```sh
docker compose up --build
```

The first run downloads the Python dependencies, the
`sentence-transformers/all-MiniLM-L6-v2` embedding model, and the Ollama model.
When the `rag` service prints its answer and exits, press `Ctrl+C` to stop the
Ollama service.

Run the RAG script again without rebuilding:

```sh
docker compose run --rm rag
```

Stop and remove the containers:

```sh
docker compose down
```

The downloaded models remain in named volumes. To remove those models as well:

```sh
docker compose down --volumes
```

### Choose another Ollama model

Copy the example environment file and edit `OLLAMA_MODEL`:

```sh
cp .env.example .env
docker compose up --build
```

Inside Compose, the Python container reaches Ollama at
`http://ollama:11434`. `127.0.0.1` would point back to the Python container
itself, not to the Ollama container.

### macOS performance note

Ollama in Docker Desktop on macOS runs without GPU acceleration. For faster
inference on Apple Silicon, run Ollama natively on macOS and point a
containerized `rag` service at `http://host.docker.internal:11434` instead.
