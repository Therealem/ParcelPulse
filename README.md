# ParcelPulse

ParcelPulse is a universal package tracking platform in development. Milestone
two connects the responsive Next.js tracking form to a FastAPI endpoint that
returns validated mock shipment data with basic carrier detection.

## Project structure

```text
ParcelPulse/
|-- frontend/          # Next.js, React, TypeScript, and Tailwind CSS
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |-- database/
|   |   |-- models/
|   |   |-- schemas/
|   |   |-- services/
|   |   `-- main.py    # FastAPI application entry point
|   |-- tests/
|   `-- requirements.txt
|-- .env.example
|-- .gitignore
`-- README.md
```

## Prerequisites

- Node.js 20.9 or newer
- npm 10 or newer
- Python 3.11 or newer

## Run the frontend

From the repository root:

```bash
cp .env.example frontend/.env.local
cd frontend
npm install
npm run dev
```

In Windows PowerShell, use `Copy-Item .env.example frontend\.env.local` from the
repository root instead of `cp`. Then open
[http://localhost:3000](http://localhost:3000).

On Windows, if PowerShell blocks the `npm.ps1` shim, use `npm.cmd` in place of
`npm` (for example, `npm.cmd run dev`). This is still the npm package manager.

Useful frontend checks:

```bash
npm run lint
npm run typecheck
npm run build
```

## Run the backend

Create and activate a virtual environment before installing dependencies.

### macOS or Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Windows PowerShell

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The API runs at [http://localhost:8000](http://localhost:8000). Verify it with:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "parcelpulse-api"
}
```

### Tracking lookup

`POST /api/tracking/lookup` accepts a JSON body:

```json
{
  "tracking_number": "1Z999AA10123456784"
}
```

The endpoint removes whitespace, detects a likely carrier, and returns mock
shipment details. It does not call a carrier API.

## Run backend tests

With the backend virtual environment active:

```bash
cd backend
python -m pytest
```

## Environment variables

The frontend reads `NEXT_PUBLIC_API_URL` from `frontend/.env.local`. Start from
the committed root `.env.example` as shown above. `NEXT_PUBLIC_` values are
visible in browser code, so they must never contain secrets.

## Manual tracking test

1. Start FastAPI on port 8000.
2. Start Next.js on port 3000 in a second terminal.
3. Open [http://localhost:3000](http://localhost:3000).
4. Enter `1Z999AA10123456784` and select **Track Package**.
5. Confirm the result card shows UPS, In Transit, August 28, 2026, and the latest
   mock update.

## Milestone scope

This repository intentionally does not include authentication, databases,
caches, containers, cloud infrastructure, or real carrier API integrations.
