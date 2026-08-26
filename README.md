# ParcelPulse

ParcelPulse is a universal package tracking platform in development. The
current application provides mock multi-carrier lookups, PostgreSQL-backed
saved shipments, and shipment detail pages with tracking history.

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

Create `backend/.env` with the PostgreSQL connection settings before using the
database health endpoint:

```env
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=parcelpulse
DATABASE_USER=parcelpulse_app
DATABASE_PASSWORD=your_actual_postgresql_password
```

The password belongs only in `backend/.env`; that file is ignored by Git. No
password is stored in application source.

Create or update the ParcelPulse tables after configuring the database:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.database.init_db
```

The command is safe to rerun. It creates any missing tables and adds the mock
history to an existing UPS sample shipment without duplicating events.

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

Verify PostgreSQL connectivity with:

```bash
curl http://localhost:8000/health/db
```

A working connection returns:

```json
{
  "status": "ok",
  "database": "connected"
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
shipment details. Successful lookups are saved to PostgreSQL, and another
lookup for the same tracking number updates the existing row. It does not call
a carrier API.

### Saved shipments

List every saved shipment:

```bash
curl http://localhost:8000/api/shipments
```

Retrieve a shipment using the `id` returned by the list endpoint:

```bash
curl http://localhost:8000/api/shipments/1
```

The single-shipment response includes a `tracking_events` array ordered newest
to oldest. In the frontend, select any card at
[http://localhost:3000/shipments](http://localhost:3000/shipments) to open its
detail page and tracking timeline.

To verify the mock tracking events directly in PostgreSQL, connect with `psql`
and run:

```sql
SELECT te.id,
       te.shipment_id,
       te.status,
       te.description,
       te.location,
       te.event_time
FROM tracking_events AS te
JOIN shipments AS s ON s.id = te.shipment_id
WHERE s.tracking_number = '1Z999AA10123456784'
ORDER BY te.event_time DESC;
```

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
6. Open **View Shipments**, select the saved shipment, and confirm its four-event
   timeline is ordered newest to oldest.

## Milestone scope

This repository intentionally does not include authentication, caches,
containers, cloud infrastructure, or real carrier API integrations.
