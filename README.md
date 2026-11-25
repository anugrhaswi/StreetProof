# StreetProof

AI-powered civic infrastructure issue intelligence platform.

## Phase 2: Persistent Reports

Phase 2 adds persistent report submission with image uploads, SQLite storage, Alembic migrations, and report listing/detail pages.

### Project Structure

```
streetproof/
├── frontend/   React + Vite + TypeScript + Tailwind CSS
├── backend/    FastAPI + SQLAlchemy + Alembic
├── AGENTS.md   Development rules
├── README.md
├── .gitignore
└── .env.example
```

## Prerequisites

- Node.js 18+ and npm
- Python 3.10+

## Backend Setup

### Standard (local development)
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

### CPU-only (Render, CI, or no GPU)
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```
The CPU-only variant avoids downloading large CUDA wheels. Install torch from the CPU index first, then install remaining requirements from PyPI.

Run migrations:

```bash
alembic upgrade head
```

Run the backend:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API: http://localhost:8000/api/health  
Docs: http://localhost:8000/docs

### Backend Config (`backend/.env`)

- `DATABASE_URL` (default `sqlite:///./data/streetproof.db`)
- `UPLOAD_DIR` (default `./uploads`)
- `CORS_ORIGINS`
- `SECRET_KEY` (required for admin sessions; use a long random value in deployment)
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` (single admin account, env-configured)
- `ADMIN_SESSION_EXPIRE_MINUTES` (default `60`)
- `ADMIN_LOGIN_RATE_LIMIT` / `ADMIN_LOGIN_RATE_WINDOW_SECONDS` (login rate limiting)

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

Frontend config: `VITE_API_BASE_URL` in `frontend/.env`.

## API Endpoints

- `POST /api/reports` (multipart: description, category, latitude, longitude, image)
- `GET /api/reports?page=1&page_size=20`
- `GET /api/reports/{id}`
- `GET /api/incidents?page=1&page_size=20`
- `GET /api/incidents/{id}`
- `GET /api/health`
- `GET /api/health/ai` (AI model readiness: not_loaded/loading/ready/failed)
- `GET /api/matching/reports/{report_id}` (matching job status + suggestions)
- `GET /api/matching/suggestions/{report_id}`
- `POST /api/admin/login` (admin login, sets HTTP-only session + CSRF cookie)
- `POST /api/admin/logout` (requires authenticated session + CSRF header)
- `GET /api/admin/session` (current admin auth status)
- Static uploads: `/uploads/*`

Categories: `pothole, streetlight, garbage, graffiti, sidewalk, signage, drainage, other`

## Testing

### Automated Backend Tests
```bash
cd backend
venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pytest tests -v
```
Automated tests use mocked embeddings and a temporary file-based SQLite database; they do not download the real embedding model.

### Manual / End-to-End
1. `cd backend && venv\Scripts\activate && alembic upgrade head`
2. Start backend: `uvicorn app.main:app --reload --port 8000`
3. Start frontend: `cd frontend && npm run dev`
4. Submit a report at `/report` with photo, description, category, coords (or use geolocation).
5. Verify record in `/reports` and detail at `/reports/:id`.
6. Check Potential Matches section on report detail (requires model download on first run).
7. Restart backend and confirm reports persist.

## Commands

| Action | Command |
|--------|---------|
| Migrate DB | `cd backend && venv\Scripts\activate && alembic upgrade head` |
| Run backend | `cd backend && venv\Scripts\activate && uvicorn app.main:app --reload --port 8000` |
| Run frontend | `cd frontend && npm run dev` |
| Build frontend | `cd frontend && npm run build` |
| Backend tests | `cd backend && venv\Scripts\activate && python -m pytest tests -v` |
| Install CPU deps | `cd backend && venv\Scripts\activate && pip install torch --index-url https://download.pytorch.org/whl/cpu && pip install -r requirements.txt` |
