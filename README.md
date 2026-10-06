# CrimeGraph AI

CrimeGraph AI is a beginner-friendly full-stack investigation-support demo. It takes investigator notes, sample network flows, and hexadecimal file samples; extracts or classifies information; and displays the resulting entities and relationships in an interactive graph.

> **Demo and safety notice:** This project is for learning and synthetic/sample data only. It is not a law-enforcement product, does not establish guilt, and must not be used to make decisions about people. Model scores and extracted links are fallible leads that require independent human review. Do not submit real personal, investigative, or confidential data. If a Gemini API key is configured, narrative text is sent to Google's Gemini API.

## What works

- Create cases and switch between them in the React workspace.
- Browse, search, filter, select, and export case graphs as JSON.
- Extract people, phone numbers, IP addresses, and locations from case notes. The local pattern extractor works without credentials; Gemini is optional.
- Classify network flows with the included CNN-LSTM model and file-byte samples with the included TF-IDF + MLP model.
- Add extraction and classification results to the selected case graph.
- Persist cases, graph nodes, relationships, and model results in a local SQLite database. The first run seeds a sample case.
- Inspect backend status and model readiness in the interface and at `/api/v1/health`.

The local database is created at `data/crimegraph.sqlite3` and is ignored by Git. Set `CRIMEGRAPH_DATABASE_PATH` to use another location.

## Stack and request flow

```text
React + Vite + Cytoscape
        │ /api (Vite development proxy)
        ▼
FastAPI + Pydantic ──► SQLite case/graph storage
        ├────────────► local narrative pattern extractor (or optional Gemini)
        └────────────► included PyTorch / scikit-learn model artifacts
```

The frontend calls FastAPI; FastAPI validates requests, calls the extraction or inference services, and writes graph changes to SQLite. SQLite and the local pattern extractor need no external service.

## Run locally (Windows PowerShell)

### 1. Backend

Use **Python 3.12** (or another Python version supported by the installed PyTorch wheels). Python prereleases may not have binary wheels for native dependencies.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
$env:PYTHONPATH = "backend"
python -m uvicorn app.main:app --reload --port 8000
```

The API starts at `http://127.0.0.1:8000`; interactive API documentation is at `http://127.0.0.1:8000/docs`. The app seeds its sample case on first startup. If model files are missing or fail to load, health reports them as unavailable and the matching inference endpoint returns `503` rather than a fabricated result.

### 2. Frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`). Vite forwards `/api` requests to the backend on port `8000`.

## Deploy: GitHub Pages + Render

This repository includes a GitHub Actions workflow for the frontend and a Render Blueprint for the API. The expected public URLs are:

- Frontend: `https://rithikaraj21.github.io/crimegraph-ai/`
- Backend: `https://crimegraph-ai-api.onrender.com`

1. Commit and push the project to the `main` branch of `rithikaraj21/crimegraph-ai`.
2. In GitHub, open **Settings → Pages**, choose **GitHub Actions** as the build and deployment source, then open **Actions** and confirm **Deploy frontend to GitHub Pages** succeeds. The workflow builds the frontend with the Pages subpath and the Render API URL.
3. In Render, choose **New → Blueprint**, connect `rithikaraj21/crimegraph-ai`, and deploy the repository's `render.yaml`. The Blueprint creates `crimegraph-ai-api`, installs the CPU-only PyTorch wheel and backend dependencies, and attaches a 1 GB persistent disk for SQLite.
4. Wait for Render's `/api/v1/health` check to pass, then reload the Pages site and verify the API status and model readiness indicators.
5. If the Render URL or GitHub Pages owner/repository differs, update `VITE_API_BASE_URL` in `.github/workflows/deploy-pages.yml` and `ALLOWED_ORIGINS` in `render.yaml`, then push a new commit.

The Render persistent disk and Starter web service are paid resources; check Render's current pricing before creating them. The GitHub Actions workflow publishes the static frontend whenever frontend files change on `main`; Render auto-deploys backend/configuration changes from the connected branch. Never add API keys to the GitHub Pages build: Pages files are public. If Gemini is needed, set `GEMINI_API_KEY` in the Render service's environment instead.

The deployed demo API is public and has no sign-in. Use synthetic examples only; do not enter real personal, confidential, or investigative information. GitHub Pages and Render account authorization is required to activate deployment.

### Optional Gemini extraction

Local pattern extraction is the default and requires no API key. To enable Gemini, set `GEMINI_API_KEY` in the backend process environment before starting the API. Never commit the key. With Gemini enabled, narrative text is sent to the configured Google API; the UI reports which extractor is active.

## API at a glance

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/health` | Storage, extractor, and model readiness |
| `GET` | `/api/v1/cases` | List cases and graph sizes |
| `POST` | `/api/v1/cases` | Create a case |
| `GET` | `/api/v1/cases/{case_id}/graph` | Fetch a Cytoscape-compatible graph |
| `POST` | `/api/v1/cases/extract-narrative` | Extract entities and relationships |
| `POST` | `/api/v1/models/botnet/predict` | Classify and attach a network flow |
| `POST` | `/api/v1/models/file-classifier/predict` | Classify and attach a hexadecimal sample |

Request and response schemas are documented by FastAPI at `/docs`.

## Tests and checks

From the repository root:

```powershell
$env:PYTHONPATH = "backend"
python -m unittest discover -s backend\tests
npm --prefix frontend run lint
npm --prefix frontend run build
```

The backend tests use a temporary SQLite database and do not modify the sample database.

## Project layout

```text
backend/app/
  api/          FastAPI routes
  core/         Settings
  schemas/      Request and graph validation
  services/     Graph storage, narrative extraction, and model inference
backend/tests/  SQLite graph-service tests
frontend/src/   React dashboard and Cytoscape graph
models/         Model code and saved inference artifacts
data/processed/ Prepared training/evaluation data
scripts/        Dataset generation and model training helpers
```
