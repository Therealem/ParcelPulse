# ParcelPulse

ParcelPulse is a universal package tracking platform in development. The
current application provides provider-backed multi-carrier lookups,
PostgreSQL-backed saved shipments, and shipment detail pages with tracking
history. Deterministic mock tracking remains the default, while EasyPost or
Shippo can be enabled explicitly for real tracking data.

## Project structure

```text
ParcelPulse/
|-- frontend/          # Next.js, React, TypeScript, and Tailwind CSS
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |-- carriers/
|   |   |-- database/
|   |   |-- models/
|   |   |-- schemas/
|   |   |-- services/
|   |   |-- tracking_providers/
|   |   `-- main.py    # FastAPI application entry point
|   |-- alembic/       # Versioned database migrations
|   |-- alembic.ini
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

Create `backend/.env` with the PostgreSQL and authentication settings before
starting FastAPI:

```env
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=parcelpulse
DATABASE_USER=parcelpulse_app
DATABASE_PASSWORD=your_actual_postgresql_password
AUTH_SECRET_KEY=paste_a_generated_random_value_here
AUTH_TOKEN_EXPIRE_MINUTES=480
AUTH_COOKIE_NAME=parcelpulse_session
AUTH_COOKIE_SECURE=false
AUTH_COOKIE_SAMESITE=lax
FRONTEND_ORIGIN=http://localhost:3000
SHIPPO_API_TOKEN=replace_with_shippo_api_token
EASYPOST_API_KEY=replace_with_easypost_api_key
TRACKING_PROVIDER=mock
```

The database password, authentication secret, and provider API credentials
belong only in `backend/.env`; that file is ignored by Git. Generate a unique
random authentication secret for each deployed environment. Use
`AUTH_COOKIE_SECURE=true` when serving the API over HTTPS.

Generate a local authentication secret without committing it:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the output into `backend/.env` as `AUTH_SECRET_KEY`.

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload
```

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Complete the applicable steps in **Database migrations** below before starting
Uvicorn. The application does not run `create_all` or migrations at startup;
production deployments must apply committed migrations explicitly.

## Database migrations

Alembic reads the same `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`,
`DATABASE_USER`, and `DATABASE_PASSWORD` values from `backend/.env` as the
FastAPI application. Run all Alembic commands from the `backend` directory.

For a new, empty database, apply every migration before starting FastAPI:

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
```

For the existing database from the shipment-history milestone, first stop
FastAPI, take a backup, and verify that it is at the initial revision:

```powershell
..\.venv\Scripts\python.exe -m alembic current
```

It should report `20260827_0001`. The authentication migration can then be
applied normally:

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
```

The migration creates `users`, adds a nullable `shipments.user_id`, and changes
tracking-number uniqueness from global to per-user. Existing shipment and event
rows are not deleted or recreated. Existing shipments retain `user_id = NULL`,
which preserves them as unassigned legacy records while keeping them out of all
user-facing API queries. Confirm the new revision afterward:

```powershell
..\.venv\Scripts\python.exe -m alembic current
```

It should report `20260827_0002 (head)`. Finally, confirm that no model changes
are missing from the migration chain:

```powershell
..\.venv\Scripts\python.exe -m alembic check
```

Common migration commands:

```powershell
# Apply all pending revisions
..\.venv\Scripts\python.exe -m alembic upgrade head

# Reverse exactly one revision
..\.venv\Scripts\python.exe -m alembic downgrade -1

# Show the database's current revision
..\.venv\Scripts\python.exe -m alembic current

# Show the migration chain
..\.venv\Scripts\python.exe -m alembic history
```

Do not use `alembic stamp head` to skip the authentication migration: stamping
does not execute its schema changes. The authentication downgrade removes user
accounts and may fail if multiple users saved the same tracking number. The
initial revision's downgrade removes both application tables. Never downgrade
on a populated database unless the consequences are explicitly intended and a
verified backup exists.

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

Tracking and shipment-management endpoints require an authenticated session.
The browser stores the signed session token in an HttpOnly cookie; the frontend
does not use local storage for authentication.

`POST /api/tracking` accepts a JSON body:

```json
{
  "tracking_number": "1Z999AA10123456784"
}
```

The tracking pipeline removes whitespace, normalizes case, requires exactly
one matching carrier adapter, and asks the configured provider for normalized
shipment details and tracking events. Successful lookups are saved to
PostgreSQL for the authenticated user. Repeating a lookup updates that user's
existing row without duplicating events; a different user may save the same
number independently. Unsupported, invalid, or ambiguous formats return a 422
response. The compatibility route `POST /api/tracking/lookup` remains
available, but new clients should use `POST /api/tracking`.

### Tracking providers

`TRACKING_PROVIDER` controls the backend provider and supports three values:

- `mock` is the default when the variable is absent. It uses the deterministic
  UPS, USPS, FedEx, and DHL adapters and never makes an external request.
- `shippo` uses Shippo's authenticated tracking endpoint for real provider
  data while retaining ParcelPulse carrier detection and persistence.
- `easypost` creates a standalone EasyPost Tracker for real provider data while
  retaining ParcelPulse carrier detection and persistence.

To configure EasyPost locally, place these values in `backend/.env`:

```env
TRACKING_PROVIDER=easypost
EASYPOST_API_KEY=your_easypost_test_or_production_key
```

FastAPI sends the normalized tracking number and detected carrier to EasyPost's
standalone Tracker API. The returned status, delivery estimate, carrier, and
tracking details are normalized into the same ParcelPulse result used by mock
and Shippo modes. See EasyPost's official
[authentication guide](https://docs.easypost.com/docs/authentication) and
[Tracker API reference](https://docs.easypost.com/docs/trackers).

To configure Shippo locally, place these values in `backend/.env`:

```env
TRACKING_PROVIDER=shippo
SHIPPO_API_TOKEN=your_shippo_test_or_live_token
```

Store only the raw `shippo_test_...` or `shippo_live_...` value. Do not include
the `ShippoToken` prefix in `backend/.env`; ParcelPulse adds that authorization
scheme to the outbound request.

A Shippo test key can use Shippo's predefined test tracking tokens. Tracking
an arbitrary real package requires live-mode data and a valid live key.

Never place an EasyPost key or Shippo token in `.env.example`, frontend
environment files, browser code, logs, screenshots, or commits. API keys must
remain in `backend/.env`. ParcelPulse sends credentials only from FastAPI to
the configured provider over HTTPS. See Shippo's official
[authentication guide](https://docs.goshippo.com/docs/guides_general/authentication/)
and [tracking endpoint reference](https://docs.goshippo.com/api-reference/tracking-status/get-a-tracking-status).

After changing provider configuration, restart FastAPI. To switch safely back
to deterministic development data:

```env
TRACKING_PROVIDER=mock
```

`EASYPOST_API_KEY` and `SHIPPO_API_TOKEN` are not required in mock mode.
Provider failures are returned as stable API errors; raw provider response
details and credentials are never sent to the frontend.

Use these deterministic tracking numbers when `TRACKING_PROVIDER=mock`:

| Carrier | Tracking number |
| --- | --- |
| UPS | `1Z999AA10123456784` |
| USPS | `9400111899223856928499` |
| FedEx | `123456789012` |
| DHL | `1234567890` |

### Saved shipments

List the authenticated user's saved shipments:

```bash
curl http://localhost:8000/api/shipments
```

Retrieve a shipment using the `id` returned by the list endpoint:

```bash
curl http://localhost:8000/api/shipments/1
```

Refresh an owned shipment through the same tracking pipeline:

```bash
curl -X POST http://localhost:8000/api/shipments/1/refresh
```

Refresh updates current shipment fields and only inserts carrier events that
are not already stored for that shipment.

Delete one shipment and its related tracking history:

```bash
curl -X DELETE http://localhost:8000/api/shipments/1
```

A successful deletion returns `204 No Content`. Other shipments are not
affected, and IDs belonging to another account return 404.

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

The frontend reads `NEXT_PUBLIC_API_URL` from `frontend/.env.local`. For local
cookie authentication, use `http://localhost:8000` so it is same-site with the
frontend at `http://localhost:3000`. Start from the committed root
`.env.example`. `NEXT_PUBLIC_` values are visible in browser code, so they must
never contain secrets.

## Manual tracking test

1. Start FastAPI on port 8000.
2. Start Next.js on port 3000 in a second terminal.
3. Open [http://localhost:3000/register](http://localhost:3000/register) and
   create an account, or sign in at `/login`.
4. Return home, enter any mock tracking number from the table above, and select
   **Track Package**.
5. Confirm ParcelPulse opens the saved shipment detail page with the matching
   carrier, status, estimate, latest update, and tracking timeline.
6. Open **View Shipments** and confirm the saved shipment is present.

The saved shipments dashboard also supports partial tracking-number search,
carrier and status filters, and sorting by newest saved, oldest saved, or
earliest estimated delivery. Use **Refresh** on a card or detail page to run the
mock lookup again without duplicating events. The detail page also provides a
confirmed **Delete Shipment** action.

## Milestone scope

This repository intentionally does not include caches, containers, cloud
infrastructure, password reset/email verification, multi-factor authentication,
or direct carrier-specific API integrations. EasyPost and Shippo are optional
real tracking providers; mock mode remains the safe development default.
