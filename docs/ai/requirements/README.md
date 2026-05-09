# Requirements: Referral Dashboard

## Problem Statement
Manage the activity of users registered through partner/referral links of crypto exchanges (BingX, Exness, Bitget, etc.). Monitor user activity such as deposits, trading volume, and commissions received. Each exchange gets its own tracking tab.

## Stakeholders
- Admin / Partner: Views referral stats, commissions, and user activity across exchanges.

## Functional Requirements

### Authentication
- FR-01: Admin can log in with username and password (JWT-based).
- FR-02: Protected routes — all dashboard routes require authentication.

### Dashboard Overview
- FR-03: Summary cards showing total referrals, total deposits, total volume, and total commission across all exchanges.
- FR-04: Per-exchange tab navigation (BingX, Exness, Bitget, etc.) — dynamically loaded from config.

### Per-Exchange Tab
- FR-05: Table of referred users with columns: User ID, Name/Email, Registration Date, Deposit Amount, Trading Volume, Commission Earned, Status.
- FR-06: Date range filter to query activity within a period.
- FR-07: Search by user ID or name.
- FR-08: Pagination support.

### Data Collection (Backend)
- FR-09: Cronjob periodically fetches data from each exchange's affiliate/partner API.
- FR-10: Raw data is normalized into a single unified `ReferredUser` schema and saved to MongoDB.
- FR-11: Each exchange has its own adapter implementing a common interface.
- FR-12: New exchanges can be added by writing a new adapter + registering in config — no changes to core logic.

### Commission & Analytics
- FR-13: View total commission earned per exchange.
- FR-14: Time-series chart of deposits/volume/commission by day or month.

## Non-Functional Requirements
- NFR-01: The system is extensible — adding a new exchange requires minimal changes.
- NFR-02: The backend API is stateless (JWT auth).
- NFR-03: Data refresh interval is configurable per exchange (default: every hour via cronjob).
- NFR-04: MongoDB is used as the primary data store.
- NFR-05: Frontend is built with Next.js (App Router), Tailwind CSS, and shadcn/ui.

## Out of Scope (v1)
- Multi-admin / role-based access control
- Email notifications
- Real-time WebSocket updates
- Mobile app
