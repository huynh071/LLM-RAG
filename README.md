# LLM-RAG

A small, fully containerized Retrieval-Augmented Generation (RAG) application.
It provides a browser-based chat interface, retrieves relevant knowledge with
Sentence Transformers and FAISS, and asks a local Ollama model to generate the
answer.

The default stack runs on CPU and is designed to work on macOS, Windows, and
Linux through Docker Compose.

## Features

- Responsive chat-style web interface with light and dark themes
- Nginx static-file server and reverse proxy
- FastAPI JSON API with request and response validation
- Local embeddings from `sentence-transformers/all-MiniLM-L6-v2`
- In-memory FAISS similarity search
- Local answer generation through Ollama
- Automatic Ollama model download during initial startup
- Persistent Docker volumes for downloaded Ollama and Hugging Face models
- No Ollama or RAG API ports exposed directly to the host

## Architecture

```text
Browser
   |
   | http://localhost:8080
   v
+---------------------------+
| web                       |
| Nginx                     |
|                           |
| /          -> static GUI  |
| /api/*     -> rag:8000    |
+-------------+-------------+
              |
              | Docker network
              v
+---------------------------+
| rag                       |
| FastAPI + FAISS           |
| Sentence Transformers     |
+-------------+-------------+
              |
              | http://ollama:11434
              v
+---------------------------+
| ollama                    |
| Local language model      |
+---------------------------+
```

Docker Compose creates an internal network for the application. Service names
act as DNS names on that network, so Nginx reaches the API at `rag:8000`, and
the RAG API reaches Ollama at `ollama:11434`.

Only the Nginx port is published:

```text
Host port 8080 -> web container port 80
```

The browser must use `/api/chat`; it cannot resolve Docker-only hostnames such
as `rag` or `ollama`.

## Services

| Service | Purpose | Lifecycle |
| --- | --- | --- |
| `web` | Serves HTML, CSS, and JavaScript through Nginx and proxies `/api/*` to FastAPI | Long-running |
| `rag` | Embeds questions, retrieves knowledge with FAISS, and calls Ollama | Long-running |
| `ollama` | Hosts the local language model API | Long-running |
| `ollama-pull` | Downloads the configured model after Ollama becomes healthy | Runs once, then exits successfully |

The `web` service waits for the `rag` health check. The `rag` service waits for
`ollama-pull`, and `ollama-pull` waits for Ollama to become healthy.

## Technology stack

### Backend

- Python 3.12
- FastAPI and Uvicorn
- Pydantic
- Sentence Transformers
- FAISS CPU
- NumPy
- Requests

### Model runtime

- Ollama
- Default model: `qwen3:0.6b`
- Default embedding model: `sentence-transformers/all-MiniLM-L6-v2`

### Frontend

- HTML
- CSS
- Vanilla JavaScript
- Nginx

## Project structure

```text
LLM-RAG/
├── .dockerignore          # Files excluded from the backend build context
├── .env.example           # Example model configuration
├── compose.yaml           # Complete multi-container application
├── Dockerfile             # RAG/FastAPI image
├── pyproject.toml         # Python project and dependencies
├── README.md
├── simple_RAG.py          # Retrieval pipeline and FastAPI endpoints
├── uv.lock                # Locked Python dependency versions
└── web/
    ├── Dockerfile         # Nginx frontend image
    ├── app.js             # Chat behavior and API calls
    ├── index.html         # Application structure
    ├── nginx.conf         # Static hosting and /api reverse proxy
    └── styles.css         # Responsive light/dark design
```

## Prerequisites

You need:

- Git
- Docker with the Compose v2 plugin
- An internet connection for the first build and model downloads
- Enough free disk space for Docker images, Python packages, the embedding
  model, and the selected Ollama model
- At least 8 GB of system memory recommended for the default small model

Verify the installation:

```sh
docker --version
docker compose version
docker info
```

The command used by this project is `docker compose` with a space. The older
standalone `docker-compose` command is not recommended.

## Platform setup

### macOS

1. Install
   [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/).
   Choose the Apple silicon or Intel download that matches the Mac.
2. Start Docker Desktop and wait until the Docker engine reports that it is
   running.
3. Open Terminal and verify Docker:

   ```sh
   docker --version
   docker compose version
   docker info
   ```

4. Continue with [Run the project](#run-the-project).

The current Compose configuration runs Ollama inside Docker without Apple GPU
acceleration. It works on CPU, but generation can be slower than native Ollama
on Apple silicon.

### Windows 10 or Windows 11

1. Install
   [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/).
2. Use the WSL 2 backend and Linux containers. This project builds Linux
   container images.
3. Start Docker Desktop and wait for the engine to become ready.
4. Open PowerShell and verify Docker:

   ```powershell
   docker --version
   docker compose version
   docker info
   ```

5. Continue with [Run the project](#run-the-project).

The commands in this README work in PowerShell. They also work in a WSL 2
terminal when Docker Desktop WSL integration is enabled. For better bind-mount
performance in a WSL workflow, keep the repository in the Linux filesystem,
for example under `~/projects`, rather than under `/mnt/c`.

If WSL needs updating, run this from an administrator PowerShell:

```powershell
wsl --update
```

### Linux

Install Docker Engine for the Linux distribution and include the Docker
Compose plugin. Use Docker's
[official Engine installation instructions](https://docs.docker.com/engine/install/)
instead of an unofficial or legacy Compose package.

For Ubuntu, the official Docker repository provides these packages:

```sh
sudo apt install docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
```

Start and verify Docker:

```sh
sudo systemctl enable --now docker
sudo docker run --rm hello-world
sudo docker compose version
```

If the user account is configured to access Docker without `sudo`, use the
commands in the rest of this README exactly as written. Otherwise, prefix
Docker commands with `sudo`, for example:

```sh
sudo docker compose up --build
```

## Run the project

### 1. Clone the repository

macOS, Linux, WSL, or Git Bash:

```sh
git clone https://github.com/huynh071/LLM-RAG.git
cd LLM-RAG
```

PowerShell:

```powershell
git clone https://github.com/huynh071/LLM-RAG.git
Set-Location LLM-RAG
```

If the repository is already downloaded, open a terminal in its root
directory. The directory must contain `compose.yaml`.

### 2. Optionally configure the model

The project works without a `.env` file and defaults to `qwen3:0.6b`.

On macOS, Linux, WSL, or Git Bash:

```sh
cp .env.example .env
```

On PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env` if a different Ollama model is wanted:

```dotenv
OLLAMA_MODEL=qwen3:0.6b
```

The model name is passed to both `ollama-pull` and `rag`. The model must be
available from the [Ollama model library](https://ollama.com/library).

### 3. Validate the Compose configuration

```sh
docker compose config
```

This resolves environment variables and checks that `compose.yaml` is valid.

### 4. Build and start the stack

Foreground mode, recommended for the first run:

```sh
docker compose up --build
```

Detached/background mode:

```sh
docker compose up --build -d
```

The first run is slower because it downloads:

- Base Docker images
- Python dependencies
- `sentence-transformers/all-MiniLM-L6-v2`
- The configured Ollama language model

Downloaded Ollama and Hugging Face models are cached in named volumes, so
later starts are faster.

### 5. Open the application

Open:

```text
http://localhost:8080
```

The status badge should change to `RAG online` after the backend health check
succeeds.

### 6. Stop the application

If Compose is running in the foreground, press `Ctrl+C`, then run:

```sh
docker compose down
```

If Compose is running in the background:

```sh
docker compose down
```

This removes the containers and project network but preserves downloaded
models.

## Verify the API

All public API requests go through Nginx on port `8080`.

### Health check

macOS, Linux, WSL, or Git Bash:

```sh
curl http://localhost:8080/api/health
```

Expected response:

```json
{"status":"healthy"}
```

PowerShell:

```powershell
Invoke-RestMethod -Uri http://localhost:8080/api/health
```

### Ask a question

macOS, Linux, WSL, or Git Bash:

```sh
curl -X POST http://localhost:8080/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"How can I contact customer support?"}'
```

PowerShell:

```powershell
$body = @{
  prompt = "How can I contact customer support?"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri http://localhost:8080/api/chat `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

Example response:

```json
{
  "answer": "You can contact customer support by email or phone.",
  "sources": [
    "Customer support: support@example.com or call 1-800-HELP",
    "Our refund policy: 30 days, full refund with receipt."
  ]
}
```

The exact answer can vary because it is generated by the language model.

## API contract

### `GET /api/health`

Reports whether the FastAPI process is ready:

```json
{
  "status": "healthy"
}
```

This endpoint confirms that FastAPI and the in-memory FAISS index loaded. It
does not currently make a separate Ollama request.

### `POST /api/chat`

Request:

```json
{
  "prompt": "What is the refund policy?"
}
```

Validation rules:

- `prompt` is required
- `prompt` must be a string
- Length must be between 1 and 4,000 characters

Successful response:

```json
{
  "answer": "The generated answer",
  "sources": [
    "Retrieved knowledge item one",
    "Retrieved knowledge item two"
  ]
}
```

FastAPI returns status `422` when the request does not match the schema. It
returns status `502` when the RAG service cannot obtain a usable response from
Ollama.

## How retrieval works

At RAG service startup:

1. The sample knowledge strings in `simple_RAG.py` are loaded.
2. `all-MiniLM-L6-v2` converts each string into a 384-dimensional vector.
3. The vectors are inserted into a FAISS `IndexFlatL2` index.

For each question:

1. The question is converted into an embedding with the same model.
2. FAISS finds the two knowledge vectors with the smallest L2 distance.
3. The matching knowledge strings are placed in the Ollama prompt as context.
4. Ollama generates an answer from that context.
5. FastAPI returns the generated answer and retrieved strings to the GUI.

The index is in memory. It is rebuilt every time the `rag` service starts.

## Current knowledge base

The current version does not load PDFs or an external database. Its knowledge
is the `documents` list in `simple_RAG.py`:

```python
documents = [
    "Our refund policy: 30 days, full refund with receipt.",
    "Shipping takes 3-5 business days for domestic orders.",
    "We accept Visa, Mastercard, and PayPal.",
    "Customer support: support@example.com or call 1-800-HELP"
]
```

After changing the list, rebuild and recreate the RAG service:

```sh
docker compose up -d --build rag
```

PDF ingestion requires additional extraction, chunking, metadata, and indexing
logic and is not part of the current checked-in implementation.

## Configuration

| Variable | Default | Used by | Purpose |
| --- | --- | --- | --- |
| `OLLAMA_MODEL` | `qwen3:0.6b` | `ollama-pull`, `rag` | Ollama model to download and use |
| `OLLAMA_BASE_URL` | `http://ollama:11434` in Compose | `rag` | Internal Ollama API address |
| `HF_HOME` | `/home/app/.cache/huggingface` in Compose | `rag` | Hugging Face model-cache directory |

Do not change `OLLAMA_BASE_URL` to `127.0.0.1` inside the RAG container.
Container-local `127.0.0.1` refers to the RAG container itself, not to Ollama.

### Change the Ollama model

Update `.env`:

```dotenv
OLLAMA_MODEL=another-model-name
```

Then recreate the affected services:

```sh
docker compose up -d --build ollama-pull rag web
```

Monitor the download:

```sh
docker compose logs -f ollama-pull
```

Larger models need more RAM, disk space, and generation time.

## Common development commands

Start or update everything:

```sh
docker compose up -d --build
```

Show service state:

```sh
docker compose ps
```

Follow all logs:

```sh
docker compose logs -f
```

Follow selected services:

```sh
docker compose logs -f web rag ollama
```

Rebuild only the frontend:

```sh
docker compose up -d --build web
```

Rebuild only the RAG API:

```sh
docker compose up -d --build rag
```

Restart a service without rebuilding:

```sh
docker compose restart rag
```

Inspect the models stored by Ollama:

```sh
docker compose exec ollama ollama list
```

Validate the Nginx configuration:

```sh
docker compose exec web nginx -t
```

Test connectivity from Nginx to FastAPI:

```sh
docker compose exec web wget -qO- http://rag:8000/api/health
```

## Persistent data

Compose creates two named volumes:

| Volume | Contents |
| --- | --- |
| `ollama_data` | Downloaded Ollama models |
| `huggingface_cache` | Downloaded Sentence Transformer files |

Normal shutdown preserves both:

```sh
docker compose down
```

To deliberately remove containers and downloaded model data:

```sh
docker compose down --volumes
```

The `--volumes` operation is destructive. The next start will download the
models again.

## CPU and GPU behavior

The checked-in Compose configuration is CPU-only and does not request a GPU.
This provides the most portable default across macOS, Windows, and Linux.

- macOS Docker containers do not use the Apple GPU for this Ollama service.
- Windows Docker GPU acceleration requires a supported GPU and the WSL 2
  backend.
- Linux NVIDIA or AMD acceleration requires the appropriate host drivers,
  container runtime configuration, and Compose device settings.

See the official [Ollama Docker documentation](https://docs.ollama.com/docker)
before modifying the Compose service for GPU access.

## Troubleshooting

### The page does not open

Check service status:

```sh
docker compose ps
```

Check logs:

```sh
docker compose logs web rag ollama-pull ollama
```

The `web` service will not start until `rag` passes its health check.

### Port 8080 is already in use

Change the host-side port in `compose.yaml`:

```yaml
web:
  ports:
    - "8081:80"
```

Recreate the service and open `http://localhost:8081`:

```sh
docker compose up -d web
```

### The GUI reports `RAG offline`

Check the API through Nginx:

```sh
curl http://localhost:8080/api/health
```

Then inspect the backend:

```sh
docker compose logs rag
docker compose ps
```

On Windows PowerShell, use:

```powershell
Invoke-RestMethod -Uri http://localhost:8080/api/health
```

### Nginx returns `502 Bad Gateway`

Test the internal connection:

```sh
docker compose exec web wget -qO- http://rag:8000/api/health
```

If it fails, inspect the RAG logs:

```sh
docker compose logs rag
```

### The first startup takes a long time

This is normally caused by image or model downloads. Follow the setup logs:

```sh
docker compose logs -f ollama-pull rag
```

Do not remove the named volumes if the downloads should be reused.

### The model download fails

Check the Ollama and pull-service logs:

```sh
docker compose logs ollama ollama-pull
```

Verify that Docker has internet access and that the model name in `.env` is
valid.

Retry the one-time pull service:

```sh
docker compose up ollama-pull
```

### A request is slow

Generation speed depends on the selected model, available CPU and memory, and
platform. The Nginx configuration allows up to 300 seconds for a RAG response.
Try the default small model first before choosing a larger model.

### The frontend still shows old CSS or JavaScript

Rebuild the web image:

```sh
docker compose up -d --build web
```

Then force-refresh the browser:

- macOS: `Command+Shift+R`
- Windows/Linux: `Ctrl+Shift+R`

### Docker commands require permission on Linux

Either prefix the commands with `sudo`, or follow Docker's
[Linux post-installation instructions](https://docs.docker.com/engine/install/linux-postinstall/)
to configure non-root access. Membership in the Docker group grants
root-equivalent privileges and should be treated accordingly.

### Start again from a clean container state

Recreate containers without deleting model caches:

```sh
docker compose down
docker compose up --build
```

Only if cached models should also be deleted:

```sh
docker compose down --volumes
docker compose up --build
```

## Security notes

- Only port `8080` is published by default.
- Ollama and FastAPI are reachable only on the internal Docker network.
- Nginx limits request bodies to 1 MB.
- FastAPI limits prompts to 4,000 characters.
- The application does not currently provide authentication or rate limiting.
- Do not expose this development configuration directly to the public
  internet. Add HTTPS, authentication, rate limiting, and appropriate network
  controls before a public deployment.

## License

No license file is currently included. Add a license before redistributing the
project if redistribution terms need to be explicit.
