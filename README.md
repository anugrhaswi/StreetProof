# StreetProof

StreetProof is an AI-assisted civic infrastructure issue intelligence platform built for a 24-hour hackathon. Citizens can submit geo-located issue reports with photos; the backend stores evidence, creates an incident, runs asynchronous multisignal duplicate detection, and gives admins a review workflow for potential matches and incident management.

> **Status:** Hackathon MVP / prototype. Core reporting, matching, admin moderation, and map flows are implemented in code. Some production hardening and deployment concerns remain partially implemented.

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Core Workflows](#core-workflows)
- [AI / Matching Pipeline](#ai--matching-pipeline)
- [Database / Schema Notes](#database--schema-notes)
- [Environment Variables](#environment-variables)
- [Local Development Setup](#local-development-setup)
- [Database Migration / PostgreSQL Notes](#database-migration--postgresql-notes)
- [Running Tests](#running-tests)
- [Deployment](#deployment)
- [API Overview](#api-overview)
- [Security / Operational Notes](#security--operational-notes)
- [Known Limitations](#known-limitations)
- [Future Improvements](#future-improvements)
- [Hackathon Notes](#hackathon-notes)
- [AI-Assisted Development / Skills Used](#ai-assisted-development--skills-used)
- [License / Team / Acknowledgements](#license--team--acknowledgements)

## Overview

StreetProof provides a citizen reporting flow and an admin moderation flow around the same incident data model:

- **Citizen side:** submit a report with image, description, category, and map-selected coordinates; view reports, report detail, public incidents, incident detail, and an interactive incident map.
- **Admin side:** log in with cookie-based session auth, view dashboard stats, inspect reports, review AI match suggestions, accept/reject matches, view merge history, reverse eligible merges, and manage incident open/closed status.
- **Backend side:** FastAPI REST API, SQLAlchemy models, Alembic migrations, local/Supabase-compatible PostgreSQL configuration, background matching worker, and evidence-preserving merge/audit records.

## Problem Statement

Civic issue reports are often duplicated, noisy, and difficult to triage. Multiple people may report the same pothole, streetlight, or garbage issue with different photos and descriptions. StreetProof addresses this by:

- collecting structured reports with location and image evidence;
- creating an incident record for each report;
- comparing new reports against existing reports using image and text/geographic signals;
- surfacing potential duplicates for admin review;
- preserving original reports and merge history when incidents are consolidated.

## Key Features

### Implemented

| Area | Feature | Status | Notes |
|---|---|---:|---|
| Citizen reporting | Report submission with image, description, category, coordinates | Implemented | `POST /api/reports`, multipart form upload. |
| Citizen UI | Report form with map location picker and image upload | Implemented | MapLibre/OpenFreeMap location picker; no map API key required. |
| Public reports | Paginated report list and report detail | Implemented | `GET /api/reports`, `GET /api/reports/{id}`. |
| Public incidents | Paginated incidents, incident detail, map endpoint | Implemented | `GET /api/incidents`, `GET /api/incidents/{id}`, `GET /api/incidents/map`. |
| Map | Interactive incident map with filters/legend/popups | Implemented | MapLibre GL, OpenFreeMap style, clustering, category/status filtering, Google Maps link from popup/details. |
| Matching | Async DB-backed matching worker | Implemented | Background worker polls pending jobs; sequential processing. |
| Matching | Multisignal duplicate detection | Implemented | SHA-256, pHash, text embedding cosine similarity, geo distance, category match. |
| Matching | Public matching status endpoint | Implemented | Returns minimal status/count/error; no internal evidence exposed. |
| Admin auth | Session cookie login/logout/session check + CSRF | Implemented | Signed session cookie, JS-readable CSRF cookie, `X-CSRF-Token` for state-changing admin routes. |
| Admin dashboard | Stats and recent reports | Implemented | Includes report/incident/job/suggestion counts. |
| Admin reports | List/detail/delete reports | Implemented | Delete blocks merge-history references and preserves merge-linked incidents. |
| Admin match review | List/detail/accept/reject suggestions | Implemented | Accept uses merge service; reject records audit metadata. |
| Admin merges | Merge history and conservative reversal | Implemented | Reversal refuses unsafe state changes. |
| Admin incidents | List/detail and open/closed status update | Implemented | Manual status change to `merged` is blocked. |
| Database | SQLite local dev + PostgreSQL/Supabase compatibility | Implemented | URL normalization, pool settings, Alembic env reads app settings. |
| Migrations | Alembic migration history including PostgreSQL enum fixes | Implemented | Head: `g1b2c3d4e5f6`. |
| Tests | Backend pytest suite | Implemented | Latest verified local run: `101 passed, 1 skipped`. |

### Partially Implemented / Operational Caveats

| Area | Status | Notes |
|---|---:|---|
| Production deployment | Partially implemented | App can be configured for deployment, but Render/Vercel deployment was not executed/verified in this CLI session. |
| Image persistence in production | Implemented in code (Supabase Storage) | `STORAGE_BACKEND=supabase` stores public Supabase Storage URLs in `Report.image_path`; local filesystem remains default for dev. Bucket existence/public-read config must be verified manually before deployment. |
| Background matching worker deployment model | Partially implemented | Worker runs inside FastAPI lifespan. Suitable for single always-on instance; not a separate scalable worker process. |
| Cross-origin admin cookie auth | Implemented (configurable) | Production defaults to `SameSite=None; Secure; HttpOnly` for session cookie and `SameSite=None; Secure` for CSRF cookie, with strict CORS allowlist and credentialed requests. Development defaults to `SameSite=Lax` for local HTTP. |
| Rate limiting | Partially implemented | Admin login rate limiter is in-memory per process; not shared across multiple instances. |
| AI model runtime | Partially implemented | Semantic mode loads SentenceTransformer in background and uses local cache dir; first run may download model unless cached. Lightweight mode disables model load/import. |
| Browser/manual E2E QA | Not verified in this CLI | UI flows, mobile behavior, and live browser console checks were not run here. |

### Not Implemented / Explicitly Not Claimed

- Automatic verification that the Supabase bucket exists and is publicly readable (code does not create/modify bucket settings).
- Automatic merge enabled by default (`AUTO_MERGE_ENABLED` defaults to `false`).
- Fully production-ready deployment.
- Dedicated queue/worker infrastructure (Redis/Celery/etc.).
- Public/admin analytics charts, heatmaps, audit-log UI, or resolution-time dashboards.

## System Architecture

```mermaid
flowchart LR
    U[Citizen Browser] -->|React/Vite UI| FE[Frontend]
    A[Admin Browser] -->|Admin UI + cookies/CSRF| FE
    FE -->|REST /api/*| API[FastAPI Backend]
    API --> DB[(SQLite dev / PostgreSQL Supabase)]
    API --> IMG[Image Storage\nLocal uploads or Supabase Storage]
    API --> MW[Matching Worker\nFastAPI lifespan background task]
    MW --> EMB[EmbeddingService\nSentenceTransformer]
    MW --> MF[Image Fingerprints\nSHA-256 + pHash]
    MW --> ME[Matching Engine\nMultisignal scoring/classification]
    ME --> DB
    MW --> MS[Merge Service / Audit Records]
    MS --> DB
```

### Runtime Components

- **Frontend:** React SPA with public routes and protected admin routes.
- **Backend API:** FastAPI app with routers for health, reports, incidents, matching, admin auth, admin dashboard/reports/incidents/matches/merges.
- **Database:** SQLAlchemy ORM models; SQLite for local dev, PostgreSQL/Supabase supported through normalized `DATABASE_URL`.
- **File storage:** Storage abstraction. Local dev default writes to `UPLOAD_DIR` and serves `/uploads`; production can use Supabase Storage public object URLs. `Report.image_path` stores either legacy `uploads/<file>` or a full public `http(s)` URL.
- **AI/matching:** In-process embedding service + DB-backed matching worker. Full semantic mode is optional; lightweight mode preserves non-semantic matching signals.

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | React 19, Vite 8, TypeScript 7 | SPA with React Router. |
| Styling/UI | Tailwind CSS, Lucide React | No chart library used. |
| Map | MapLibre GL 6.19.0, OpenFreeMap Liberty style | Worker registered via `?worker&url`. |
| Backend | Python, FastAPI, SQLAlchemy, Pydantic, Alembic | REST API and ORM/migrations. |
| Auth | itsdangerous, passlib[argon2], FastAPI cookies | Admin session + CSRF. |
| AI/Matching | ImageHash, Pillow, geo/category logic (default/lightweight); optional sentence-transformers `all-MiniLM-L6-v2` + torch + scikit-learn (`requirements-ai.txt`) | Multisignal duplicate detection; semantic text similarity optional. |
| Database | SQLite (dev), PostgreSQL/Supabase (target) | `psycopg[binary]` for PostgreSQL. |
| Testing | pytest, pytest-asyncio, httpx | Backend tests under `backend/tests`. |

## Project Structure

```text
StreetProof/
├── .env.example                  # Root env template (backend + frontend guidance)
├── AGENTS.md                     # Repository development instructions
├── README.md                     # Project documentation
├── start-streetproof.bat         # Local Windows launcher (backend + frontend)
├── backend/
│   ├── alembic/                  # Migration env + version scripts
│   ├── alembic.ini
│   ├── app/
│   │   ├── api/                  # FastAPI routers
│   │   ├── auth/                 # Admin auth router/dependencies/security
│   │   ├── services/             # Matching, embeddings, merge, image/geo services
│   │   ├── config.py             # Runtime settings + validation
│   │   ├── database.py           # Engine/session setup
│   │   ├── main.py               # App factory/lifespan/router registration
│   │   ├── models.py             # SQLAlchemy models/enums
│   │   └── schemas.py            # Pydantic request/response schemas
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── requirements-cpu.txt
│   ├── requirements-dev.txt
│   └── tests/                    # Backend tests
└── frontend/
    ├── .env.example
    ├── package.json
    ├── src/
    │   ├── components/           # Shared UI, map, admin components
    │   ├── config/               # Map config
    │   ├── contexts/             # Admin auth context
    │   ├── hooks/                # Geolocation/map data hooks
    │   ├── pages/                # Public and admin pages
    │   └── services/api.ts       # API client/types
    └── vite.config.ts
```

## Core Workflows

### 1. Citizen Report Submission

```mermaid
sequenceDiagram
    participant C as Citizen
    participant FE as Frontend
    participant API as FastAPI
    participant IMG as Image Service
    participant DB as Database
    participant W as Matching Worker

    C->>FE: Submit image + description + category + location
    FE->>API: POST /api/reports (multipart/form-data)
    API->>IMG: Validate/save image, compute SHA-256 + pHash
    API->>DB: Create Incident (OPEN)
    API->>DB: Create Report linked to Incident
    API->>DB: Create MatchingJob (PENDING)
    API-->>FE: 201 ReportResponse
    W->>DB: Poll pending jobs
    W->>DB: Compute embedding/signals, store suggestions, mark job completed
```

### 2. Admin Match Review

```mermaid
flowchart TD
    A[Admin Login] --> B[View Match Review Queue]
    B --> C[Inspect suggestion evidence/signals]
    C -->|Reject| D[POST /api/admin/matches/{id}/reject]
    C -->|Accept| E[POST /api/admin/matches/{id}/accept]
    E --> F[Merge service rechecks eligibility/conflicts]
    F -->|Success| G[MergeEvent + AuditLog + suggestion status updated]
    F -->|Conflict/unsafe| H[409 Conflict]
    G --> I[Optional reversal if safe]
    I --> J[POST /api/admin/merges/{id}/reverse]
```

## AI / Matching Pipeline

The matching pipeline is implemented in backend services and runs asynchronously after report creation.

### Signals Used

| Signal | Implementation | Purpose |
|---|---|---|
| SHA-256 | `image_fingerprint.compute_sha256` | Exact image duplicate detection. |
| pHash | `image_fingerprint.compute_phash` + Hamming/similarity | Perceptual image similarity. |
| Text similarity | SentenceTransformer embedding + cosine similarity (semantic mode only) | Description semantic similarity. In lightweight mode this is intentionally unavailable (`None`), not fabricated. |
| Geo distance | Haversine distance | Spatial proximity. |
| Category match | Category equality | Conflict/consistency check. |

### Modes

- **Full semantic (local/dev when enabled):** installs `requirements-ai.txt`, sets `SEMANTIC_MATCHING_ENABLED=true` (or default dev), loads SentenceTransformer in background, computes embeddings/text similarity.
- **Lightweight (Render Free / production default):** installs `requirements.txt`, `SEMANTIC_MATCHING_ENABLED=false` (or production default), does **not** import/load torch/sentence-transformers, keeps SHA-256/pHash/geo/category/matching jobs/suggestions/moderation/audit.

### Classification

The matching engine produces:

- `AUTO_MERGE_CANDIDATE`
- `REVIEW_CANDIDATE`
- `NO_MATCH`

`MatchSuggestion.similarity_score` is a heuristic ranking score (not a probability). The worker stores suggestion evidence and classification; it does not blindly merge on image evidence alone.

### Safety Rules

- Exact SHA-256 reuse, distant matches, or missing coordinates are treated conservatively (review/conflict paths, not unsafe auto-merge).
- `AUTO_MERGE_ENABLED` defaults to `false`.
- Admin accept can reuse merge logic but still blocks contradiction/unsafe cases.
- Merges are transactional/idempotent and create merge/audit records.
- Reversal is conservative and refuses unsafe state changes.

## Database / Schema Notes

### Main Entities

| Table/Model | Purpose |
|---|---|
| `incidents` | Canonical incident record; status `open/closed/merged`; may point to `merged_into_incident_id`. |
| `reports` | Citizen-submitted evidence/report linked to an incident; stores image path, hashes, embedding, coordinates. |
| `matching_jobs` | Async job lifecycle for report matching: `pending/processing/completed/failed`. |
| `match_suggestions` | Candidate duplicate links with evidence and suggestion status. |
| `merge_events` | Immutable merge/reversal event snapshots. |
| `merge_executions` | Merge execution tracking/idempotency/retry state. |
| `admin_audit_logs` | Admin/system action audit records. |

### Enum Notes

- `CategoryEnum`: `pothole, streetlight, garbage, graffiti, sidewalk, signage, drainage, other`
- `StatusEnum`: `open, closed, merged`
- `MatchingJobStatusEnum`: `pending, processing, completed, failed`
- `SuggestionStatusEnum`: `pending, reviewed, dismissed, rejected, auto_merged, superseded`
- `MergeExecutionStatusEnum`: `pending, retrying, succeeded, failed`
- `ActorTypeEnum`: `admin, system`

### Migration Notes

- Alembic config: `backend/alembic.ini`, env: `backend/alembic/env.py`.
- Current migration head in repo: `g1b2c3d4e5f6`.
- PostgreSQL enum handling includes explicit D2 enum creation and corrective D3/G1 enum-label migrations.
- The empty Supabase PostgreSQL project was migrated successfully in the development session; this does not imply full production readiness.

## Environment Variables

Use `.env.example` as the source template. Do not commit real secrets.

### Backend (`backend/.env`)

| Variable | Required | Default / Example | Notes |
|---|---:|---|---|
| `ENVIRONMENT` | Yes in prod | `development` | `development`, `production`, or `test`. |
| `DEBUG` | Yes in prod | `true` | Must be `false` in production. |
| `CORS_ORIGINS` | Yes in prod | `["http://localhost:5173","http://127.0.0.1:5173"]` | JSON array or comma-separated origins. No `*` with credentials. |
| `DATABASE_URL` | Yes | `sqlite:///./data/streetproof.db` | SQLite or PostgreSQL/Supabase. `postgres://` and `postgresql://` normalized to `postgresql+psycopg://`. |
| `DATABASE_POOL_SIZE` | No | `5` | PostgreSQL pool size. |
| `DATABASE_MAX_OVERFLOW` | No | `10` | PostgreSQL pool overflow. |
| `DATABASE_POOL_TIMEOUT_SECONDS` | No | `30` | PostgreSQL pool timeout. |
| `DATABASE_POOL_RECYCLE_SECONDS` | No | `1800` | PostgreSQL pool recycle. |
| `DATABASE_POOL_PRE_PING` | No | `true` | PostgreSQL connection health check. |
| `UPLOAD_DIR` | No | `./uploads` | Local image storage path (used in local backend and legacy local reads). |
| `STORAGE_BACKEND` | No | `local` | `local` or `supabase`. Use `supabase` in production; local filesystem is default for dev/test. |
| `SUPABASE_URL` | Required when `STORAGE_BACKEND=supabase` | empty | Supabase project URL, e.g. `https://<project-ref>.supabase.co`. Backend only. |
| `SUPABASE_SERVICE_ROLE_KEY` | Required when `STORAGE_BACKEND=supabase` | empty | Supabase service-role key for Storage REST API. **Backend only; never expose to frontend/Vercel `VITE_*`.** |
| `SUPABASE_STORAGE_BUCKET` | No | `report-images` | Public Supabase Storage bucket for report images. |
| `SEMANTIC_MATCHING_ENABLED` | No | unset | `true` enables full semantic model; `false` forces lightweight matching; unset defaults to enabled in dev/test and disabled in production. |
| `EMBEDDING_MODEL_NAME` | No | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model (semantic mode). |
| `EMBEDDING_MODEL_REVISION` | No | `c9745ed1d9f207416be6d2e6f8de32d1f16199bf` | Pinned model revision. |
| `EMBEDDING_CACHE_DIR` | No | `./model_cache` | Local model cache (semantic mode). |
| `MATCHING_THRESHOLD` | No | `0.30` | Legacy/semantic threshold config present. |
| `MAX_CANDIDATES` | No | `10` | Max candidate incidents. |
| `MATCHING_WORKER_INTERVAL_SECONDS` | No | `5` | Worker poll interval. |
| `MATCHING_MAX_RETRIES` | No | `3` | Matching job retries. |
| `PHASH_HASH_SIZE` | No | `8` | pHash size. |
| `PHASH_SIMILARITY_THRESHOLD` | No | `0.85` | Strong pHash threshold. |
| `PHASH_REVIEW_THRESHOLD` | No | `0.65` | Review pHash threshold. |
| `MATCHING_RADIUS_METERS` | No | `500` | Review radius. |
| `AUTO_MERGE_RADIUS_METERS` | No | `50` | Auto-merge radius. |
| `TEXT_SIMILARITY_THRESHOLD` | No | `0.75` | Text review threshold. |
| `AUTO_MERGE_TEXT_THRESHOLD` | No | `0.85` | Auto-merge text threshold. |
| `AUTO_MERGE_ENABLED` | No | `false` | Keep disabled unless deliberately changing behavior. |
| `AUTO_MERGE_MIN_SCORE_MARGIN` | No | `0.15` | Ambiguity margin. |
| `AUTO_MERGE_REQUIRE_GEO` | No | `true` | Geo requirement for auto-merge. |
| `AUTO_MERGE_REQUIRE_CATEGORY` | No | `true` | Category requirement. |
| `AUTO_MERGE_REQUIRE_TEXT_SUPPORT` | No | `true` | Text support requirement. |
| `MERGE_MAX_RETRIES` | No | `3` | Merge retry attempts. |
| `MERGE_RETRY_BASE_DELAY_SECONDS` | No | `30` | Merge retry base delay. |
| `MERGE_RETRY_MAX_DELAY_SECONDS` | No | `300` | Merge retry max delay. |
| `SECRET_KEY` | Yes in prod | placeholder | Must be strong/non-default, >=32 chars in production. |
| `ADMIN_USERNAME` | Yes in prod | placeholder | Must be non-default in production. |
| `ADMIN_PASSWORD` | Yes in prod | placeholder | Must be strong/non-default, >=12 chars in production. |
| `ADMIN_SESSION_EXPIRE_MINUTES` | No | `60` | Session expiry. |
| `ADMIN_LOGIN_RATE_LIMIT` | No | `5` | Login attempts/window. |
| `ADMIN_LOGIN_RATE_WINDOW_SECONDS` | No | `60` | Rate-limit window. |

### Frontend (`frontend/.env` / `frontend/.env.local`)

| Variable | Required | Default / Example | Notes |
|---|---:|---|---|
| `VITE_API_BASE_URL` | Recommended | `http://localhost:8000` | Backend base URL. Leave compatible with Vite proxy/local dev as needed. |
| `VITE_MAP_DEFAULT_LAT` | No | `26.7271` | Default map center latitude. |
| `VITE_MAP_DEFAULT_LNG` | No | `88.3953` | Default map center longitude. |
| `VITE_MAP_STYLE_URL` | No | `https://tiles.openfreemap.org/styles/liberty` | OpenFreeMap style URL. |

## Local Development Setup

### Prerequisites

- Python 3.12+ recommended (project has been used with Python 3.12 in local venv).
- Node.js 20+ recommended for current Vite/React toolchain.
- npm.
- Git.

### 1. Clone and configure

```bash
git clone https://github.com/anugrhaswi/StreetProof.git
cd StreetProof
```

Create backend env:

```bash
# Windows PowerShell
Copy-Item .env.example backend\.env

# macOS/Linux
cp .env.example backend/.env
```

Create frontend env (optional but recommended):

```bash
# Windows PowerShell
Copy-Item frontend\.env.example frontend\.env

# macOS/Linux
cp frontend/.env.example frontend/.env
```

### 2. Backend setup

```bash
cd backend
python -m venv venv
```

Activate venv:

```bash
# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Windows cmd
.\venv\Scripts\activate.bat

# macOS/Linux
source venv/bin/activate
```

Install dependencies:

```bash
# Lightweight backend (Render/default production-safe)
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Full local AI (semantic matching)
pip install -r requirements-ai.txt
```

For CPU-only torch installs, follow `backend/requirements-cpu.txt` (install CPU torch first, then `requirements-ai.txt`).

Run migrations:

```bash
# from backend/
alembic upgrade head
```

Start backend:

```bash
# from backend/
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend default: `http://localhost:8000`

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend default: `http://localhost:5173`

Vite dev server proxies `/api` and `/uploads` to `http://localhost:8000`.

### 4. Windows convenience launcher

`start-streetproof.bat` exists at repo root. It checks ports 8000/5173, starts backend/frontend in new cmd windows, runs `alembic upgrade head`, and uses `uvicorn --reload`. Use it only after backend venv and frontend dependencies are installed.

## Database Migration / PostgreSQL Notes

### SQLite (local default)

- Default `DATABASE_URL=sqlite:///./data/streetproof.db`.
- SQLite foreign keys are enabled on connect.
- Good for local development and tests.

### PostgreSQL / Supabase

- Set `DATABASE_URL` to a PostgreSQL URL. The app normalizes:
  - `postgres://...` -> `postgresql+psycopg://...`
  - `postgresql://...` -> `postgresql+psycopg://...`
- Alembic reads the same configured URL via `backend/alembic/env.py`.
- PostgreSQL pool settings are configurable through env vars.
- For Supabase, SSL is typically required (`sslmode=require`) depending on connection mode.

Example (placeholder only):

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres?sslmode=require
```

### Migration commands

```bash
# from backend/
alembic upgrade head
alembic current
alembic history
```

### Supabase verification note

During Stage 2, an empty Supabase PostgreSQL project was migrated and verified through the migration head. This confirms migration compatibility on that empty project; it does **not** by itself prove full production deployment, persistent image storage, or multi-instance worker safety.

## Running Tests

Backend tests:

```bash
# from backend/
pytest tests -q --tb=short
```

Postgres compatibility smoke (requires `TEST_DATABASE_URL` / reachable PostgreSQL; otherwise test may skip/fail depending on marker/environment):

```bash
# from backend/
pytest tests/test_postgres_compat.py -q --tb=short
```

Frontend build/lint checks:

```bash
# from frontend/
npm run lint
npm run build
```

### Latest verified local results (this CLI session)

- `pytest tests/test_semantic_lightweight_mode.py -q --tb=short` -> **6 passed**
- `pytest tests -q --tb=short` -> **107 passed, 1 skipped**
- `npm run build` (frontend) -> **passed** (Vite build completed; chunk-size warning only)

## Deployment

Deployment is **partially implemented / prepared**, not fully production-verified.

### Backend (Render-style deployment target)

- Run as a single FastAPI web service.
- Set production env vars/secrets in the host platform; never commit them.
- Required production checks enforced by config validation:
  - `ENVIRONMENT=production`
  - `DEBUG=false`
  - strong `SECRET_KEY`
  - non-default `ADMIN_USERNAME`
  - strong `ADMIN_PASSWORD`
  - explicit `CORS_ORIGINS` allowlist
- Use PostgreSQL/Supabase `DATABASE_URL`.
- Run `alembic upgrade head` during deploy/release.

**Important deployment caveats:**

- **Configure persistent images for Render.** Set `STORAGE_BACKEND=supabase` with backend-only Supabase Storage credentials and a public `report-images` bucket. Local `UPLOAD_DIR` storage is ephemeral on Render and should be dev-only.
- **Matching worker is embedded in FastAPI lifespan.** Run one always-on instance unless/until worker is extracted.
- **In-memory login rate limiter** is not shared across instances.
- **Model cache/download** may affect cold start in semantic mode; configure persistent cache/storage as needed. For Render Free, keep `SEMANTIC_MATCHING_ENABLED=false` and use lightweight `requirements.txt`.

### Frontend (Vercel-style deployment target)

- Vercel Root Directory should be `frontend`.
- Build command: `npm run build` (from frontend/root config as appropriate).
- Set `VITE_API_BASE_URL` to deployed backend URL.
- Redeploy after env changes.

### Cross-origin admin auth note

Production admin cookie auth defaults to `SameSite=None; Secure` (with strict explicit CORS allowlist and `allow_credentials=true`) for cross-site Vercel -> Render deployments. Development/test default to `SameSite=Lax` for local HTTP workflows. `ADMIN_COOKIE_SAMESITE` can override when needed.

## API Overview

Base URL defaults to `http://localhost:8000`.

### Public / Citizen

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Service health. |
| GET | `/api/health/ai` | AI/semantic matching status (`ready/loading/failed/disabled` + `semantic_matching_enabled`). |
| POST | `/api/reports` | Submit report (multipart image + fields). |
| GET | `/api/reports` | List reports (paginated). |
| GET | `/api/reports/{report_id}` | Report detail. |
| GET | `/api/incidents` | List incidents (paginated). |
| GET | `/api/incidents/{incident_id}` | Incident detail. |
| GET | `/api/incidents/map` | Map-friendly active incidents (excludes merged). |
| GET | `/api/matching/reports/{report_id}` | Minimal public matching status. |

### Admin

Admin routes require authenticated admin session; state-changing routes also require CSRF token/header.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/admin/login` | Admin login, sets session + CSRF cookies. |
| POST | `/api/admin/logout` | Admin logout (CSRF required). |
| GET | `/api/admin/session` | Session check. |
| GET | `/api/admin/dashboard/stats` | Dashboard statistics. |
| GET | `/api/admin/dashboard/recent-reports` | Recent reports. |
| GET | `/api/admin/reports` | List/search/filter reports. |
| GET | `/api/admin/reports/{report_id}` | Admin report detail. |
| DELETE | `/api/admin/reports/{report_id}` | Delete report with safety checks. |
| GET | `/api/admin/incidents` | List incidents. |
| GET | `/api/admin/incidents/{incident_id}` | Incident detail. |
| PATCH | `/api/admin/incidents/{incident_id}/status` | Open/closed status update. |
| GET | `/api/admin/matches` | Match suggestion queue. |
| GET | `/api/admin/matches/{suggestion_id}` | Match suggestion detail. |
| POST | `/api/admin/matches/{suggestion_id}/accept` | Accept suggestion / merge. |
| POST | `/api/admin/matches/{suggestion_id}/reject` | Reject suggestion. |
| GET | `/api/admin/merges` | Merge event history. |
| GET | `/api/admin/merges/{merge_event_id}` | Merge event detail. |
| POST | `/api/admin/merges/{merge_event_id}/reverse` | Conservative merge reversal. |

## Security / Operational Notes

- **No secrets in repo:** `.env` files are gitignored; use `.env.example` placeholders.
- **Production config validation:** startup validates unsafe production defaults (debug, secret key, admin credentials, CORS).
- **CORS:** explicit allowlist; no wildcard with credentials.
- **Admin auth:** signed HttpOnly session cookie + JS-readable CSRF cookie + double-submit CSRF validation.
- **Rate limiting:** in-memory admin login rate limiter (per process).
- **Uploads:** image type/size/content validation; SHA-256/pHash fingerprinting preserved; local filesystem storage in dev or Supabase Storage public URLs in production; legacy `/uploads/...` paths still supported.
- **Evidence preservation:** original reports/images are not deleted by merge; merge creates immutable event/audit records.
- **Conservative merging:** uncertain matches remain reviewable; merge/reversal paths check conflicts.
- **No destructive DB operations** are part of normal app flow; migrations should be reviewed before production use.

## Known Limitations

- Supabase Storage requires manual bucket verification/public-read policy check before deployment; code does not create or alter bucket configuration.
- Matching worker is embedded in the API process and not horizontally scalable as-is.
- Admin login rate limiting is in-memory and not shared across instances.
- Cross-site admin auth requires HTTPS, `SameSite=None; Secure` cookies, strict CORS allowlist, and frontend `credentials: "include"`.
- Semantic AI model loading can be heavy on first run/cold start depending on cache availability; lightweight mode avoids this but has no text-semantic signal.
- No automated browser E2E suite in this CLI verification; manual UI QA is still needed.
- Vercel/Render deployment configuration and live production smoke tests were not executed in this CLI session.
- Supabase migration was verified on an empty project; existing production data migration scenarios require separate planning.

## Future Improvements

- Verify Supabase Storage bucket/public policy and add signed URL/private bucket option if needed.
- Extract matching worker into a separate process/queue with shared state.
- Add Redis/shared rate limiting and session/security hardening for multi-instance deployments.
- Add end-to-end browser tests (Playwright/Cypress) and deployment smoke checks.
- Add observability: structured logs, metrics, job dashboards, alerting.
- Improve geocoding/address normalization and duplicate explanation UX.
- Add role-based admin permissions and audit-log UI.

## Hackathon Notes

- **24-hour constraint:** The project prioritizes a working, demonstrable MVP over exhaustive production hardening.
- **What was prioritized:** report submission, evidence storage, async matching, admin review/merge controls, map visualization, and basic deployment/config readiness.
- **What was intentionally constrained:** no chart/analytics bloat, no fake integrations, no destructive schema shortcuts, no claim of full production readiness.
- **Pragmatic decisions:** SQLite for local speed, storage abstraction with local-dev default and Supabase Storage for production persistence, embedded worker for simple operation, and conservative merge behavior to avoid bad automatic merges.

## AI-Assisted Development / Skills Used

This project was developed with AI-assisted coding workflows. Repository-visible skill/instruction artifacts in this workspace include:

- `AGENTS.md` - project rules and hackathon constraints.
- `.agents/skills/supabase-postgres-best-practices` - Supabase/Postgres guidance skill installed in workspace (untracked artifact).
- `skills-lock.json` - local skills lock metadata (untracked artifact).

AI assistance was used to accelerate implementation, debugging, and documentation, but behavior documented here is based on repository inspection and verified command/test results where noted.

## License / Team / Acknowledgements

- **License:** No `LICENSE` file was found in the repository at the time of writing. Add one before public/open-source distribution.
- **Team:** Team/contributor metadata is not fully specified in-repo. Git remote points to `https://github.com/anugrhaswi/StreetProof.git`.
- **Acknowledgements:** OpenFreeMap/MapLibre for map rendering, Photon for geocoding/location search, FastAPI/SQLAlchemy/Alembic ecosystem, and Sentence Transformers/ImageHash/Pillow/scikit-learn for matching components.