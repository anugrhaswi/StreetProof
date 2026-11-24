# StreetProof

AI-powered civic infrastructure issue intelligence platform.

## Phase 1: Foundation

This phase establishes the project structure, frontend, backend, and working
communication between them. No reporting, AI, database, or map features yet.

### Project Structure

```
streetproof/
├── frontend/   React + Vite + TypeScript + Tailwind CSS
├── backend/    FastAPI REST API
├── AGENTS.md   Development rules
├── README.md   This file
├── .gitignore
└── .env.example
```

## Prerequisites

- Node.js 18+ and npm
- Python 3.10+
- pip

## Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

Run the backend:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify the health endpoint:

```bash
curl http://localhost:8000/api/health
# {"status":"ok","service":"streetproof-api"}
```

API docs: http://localhost:8000/docs

### Backend Configuration

Copy `.env.example` values to `backend/.env` to override defaults:

- `CORS_ORIGINS` — JSON list of allowed origins (defaults to localhost:5173)

## Frontend Setup

```bash
cd frontend
npm install
```

Copy `.env.example` to `.env` then run:

```bash
npm run dev
```

Open http://localhost:5173

### Frontend Configuration

- `VITE_API_BASE_URL` — Backend base URL (default: `http://localhost:8000`)

## Testing the Connection

1. Start the backend (see above).
2. Confirm `curl http://localhost:8000/api/health` returns JSON.
3. Start the frontend (see above) and open http://localhost:5173.
4. The homepage shows a green **Connected** badge when the API responds.
5. Stop the backend — the badge turns red **Disconnected** within ~10 seconds.
6. Restart the backend — the badge returns to **Connected** automatically.

## Commands Summary

| Action | Command |
|--------|---------|
| Run backend | `cd backend && venv\Scripts\activate && uvicorn app.main:app --reload --port 8000` |
| Run frontend | `cd frontend && npm run dev` |
| Frontend build | `cd frontend && npm run build` |
| Frontend typecheck | `cd frontend && npx tsc --noEmit` |
