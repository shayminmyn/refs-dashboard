# Planning: Referral Dashboard

## Project Structure
```
refs-dashboard/
├── backend/
│   ├── src/
│   │   ├── adapters/          # Exchange adapters (BingX, Exness, Bitget...)
│   │   │   ├── base.adapter.ts
│   │   │   ├── bingx.adapter.ts
│   │   │   ├── exness.adapter.ts
│   │   │   └── index.ts       # Adapter registry
│   │   ├── models/            # Mongoose models
│   │   │   ├── referredUser.model.ts
│   │   │   ├── exchange.model.ts
│   │   │   ├── admin.model.ts
│   │   │   └── syncLog.model.ts
│   │   ├── routes/            # Express routers
│   │   │   ├── auth.routes.ts
│   │   │   ├── exchanges.routes.ts
│   │   │   ├── users.routes.ts
│   │   │   ├── stats.routes.ts
│   │   │   └── sync.routes.ts
│   │   ├── middleware/
│   │   │   └── auth.middleware.ts
│   │   ├── jobs/
│   │   │   └── sync.job.ts    # node-cron scheduler
│   │   ├── services/
│   │   │   └── sync.service.ts
│   │   ├── config/
│   │   │   └── exchanges.config.ts
│   │   └── index.ts           # App entry point
│   ├── .env.example
│   ├── package.json
│   └── tsconfig.json
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/login/page.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── layout.tsx
│   │   │   │   ├── page.tsx          # Overview
│   │   │   │   └── [exchangeId]/page.tsx
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── ui/                   # shadcn components
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── Header.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── SummaryCards.tsx
│   │   │   │   ├── ExchangeTabs.tsx
│   │   │   │   ├── UsersTable.tsx
│   │   │   │   ├── TimeSeriesChart.tsx
│   │   │   │   └── SyncStatus.tsx
│   │   ├── lib/
│   │   │   ├── api.ts               # Fetch wrapper
│   │   │   └── auth.ts              # JWT helpers
│   │   └── hooks/
│   │       ├── useExchanges.ts
│   │       └── useUsers.ts
│   ├── .env.local.example
│   └── package.json
│
├── docker-compose.yml
└── README.md
```

## Task Breakdown

### Phase 1: Backend Foundation
- [x] Init Node.js/Express/TypeScript project
- [x] Connect MongoDB with Mongoose
- [x] Create Mongoose models
- [x] JWT auth (login endpoint + middleware)
- [x] Base adapter interface

### Phase 2: Exchange Adapters
- [x] BingX adapter (mock/stub for now, real API keys needed)
- [x] Exness adapter (mock/stub)
- [x] Adapter registry + cronjob scheduler
- [x] Sync service (upsert to MongoDB)

### Phase 3: API Endpoints
- [x] Auth routes
- [x] Exchanges route
- [x] Users route (paginated, filtered)
- [x] Stats routes (overview, per-exchange, timeseries)
- [x] Sync routes (trigger + logs)

### Phase 4: Frontend
- [x] Next.js project scaffold
- [x] Login page with JWT storage
- [x] Dashboard layout (sidebar + header)
- [x] Overview page (summary cards + chart)
- [x] Per-exchange tab page (users table + filters)
- [x] API integration hooks

### Phase 5: DevOps
- [x] docker-compose (MongoDB + backend + frontend)
- [x] .env.example files
- [x] README with setup instructions
