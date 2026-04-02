# UltrERP Architecture v1

**Created:** 2026-03-30

## Overview
Enterprise Resource Planning system with modular architecture.

## Tech Stack
- **Backend:** Python/FastAPI
- **Database:** PostgreSQL
- **Frontend:** React
- **Infrastructure:** Docker, Cloudflare

## Modules
1. Inventory Management
2. Order Processing
3. Financial Tracking
4. HR Module

## Data Flow
```
User → React UI → FastAPI → PostgreSQL
         ↓
    Cloudflare CDN
```
