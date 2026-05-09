# Refs Dashboard

A full-stack web application to manage referral users across crypto exchange partner programs (BingX, Exness, Bitget, and more).

## Features

- **Multi-exchange tracking** — each exchange has its own tab with isolated data
- **Unified schema** — all exchange data normalized into one `ReferredUser` model
- **Pluggable adapter system** — add a new exchange by writing one adapter class
- **Auto-sync** — node-cron jobs fetch data from exchange APIs on a configurable schedule
- **Manual sync** — trigger a sync on demand from the UI
- **JWT auth** — protected admin dashboard
- **Charts & analytics** — deposits, volume, commission over time; per-exchange breakdown

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 14, Tailwind CSS, Recharts |
| Backend | Python 3.12, FastAPI, Uvicorn |
| ODM | Beanie (async MongoDB ODM) |
| Database | MongoDB |
| Auth | PyJWT + passlib[bcrypt] |
| HTTP Client | httpx (async) |
| Scheduler | APScheduler |

## Project Structure

```
refs-dashboard/
├── backend/         # Express API + adapters + cronjobs
├── frontend/        # Next.js dashboard
├── docs/ai/         # Phase documentation (requirements, design, planning)
└── docker-compose.yml
```

## Quick Start (Local Dev)

### Prerequisites
- Node.js 20+
- MongoDB running locally (or Docker)

### 1. Backend

```bash
cd backend
cp .env.example .env
# Chỉnh .env — điền JWT_SECRET và API key các sàn (tuỳ chọn, dùng mock nếu bỏ trống)

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 4000
```

Backend chạy tại `http://localhost:4000` — Swagger UI tại `http://localhost:4000/docs`.

### 2. Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Frontend runs on `http://localhost:3000`.

### Default Credentials

```
Username: admin
Password: admin123
```

> Change via `Admin.updateOne(...)` in the database after first login.

## Docker

```bash
# Copy and fill backend env
cp backend/.env.example backend/.env

docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:4000
- MongoDB: localhost:27017

## Adding a New Exchange

1. Create `backend/app/adapters/myexchange.py`:

```python
from app.adapters.base import BaseExchangeAdapter, NormalizedUser

class MyExchangeAdapter(BaseExchangeAdapter):
    @property
    def exchange_id(self) -> str:
        return "myexchange"

    async def fetch_referrals(self) -> list[NormalizedUser]:
        # Gọi API partner, chuẩn hoá về NormalizedUser
        ...
```

2. Đăng ký trong `backend/app/adapters/registry.py`:

```python
from app.adapters.myexchange import MyExchangeAdapter

_adapters = [
    BingXAdapter(),
    ExnessAdapter(),
    BitgetAdapter(),
    MyExchangeAdapter(),  # thêm vào đây
]
```

3. Seed the exchange record in MongoDB (or add to `seed.ts`):

```json
{ "id": "myexchange", "name": "My Exchange", "enabled": true, "cronSchedule": "0 * * * *" }
```

That's it — the frontend will automatically show the new tab.

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/me` | Current admin |
| GET | `/api/exchanges` | List exchanges |
| GET | `/api/users` | Paginated users (filter by exchange, search, date) |
| GET | `/api/stats/overview` | Totals across all exchanges |
| GET | `/api/stats/:exchangeId` | Totals for one exchange |
| GET | `/api/stats/:exchangeId/timeseries` | Time-series chart data |
| GET | `/api/sync/logs` | Sync history |
| POST | `/api/sync/:exchangeId` | Trigger manual sync |
