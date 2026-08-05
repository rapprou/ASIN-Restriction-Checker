# ASIN Restriction Checker

A Python CLI tool that bulk-checks Amazon selling restrictions on a list of ASINs via the SP-API, before committing to sourcing inventory.

## Problem

Amazon sellers sourcing products in bulk face a manual bottleneck: checking whether each ASIN is eligible for sale on their marketplace requires clicking through Seller Central one product at a time. At 100+ ASINs per sourcing session, that's hours of repetitive work.

This tool automates the process — drop a CSV of ASINs, get back a CSV with `ELIGIBLE / APPROVAL_REQUIRED / NOT_ELIGIBLE` per product, in minutes.

## Stack

- Python 3.10+
- [Amazon SP-API](https://developer-docs.amazon.com/sp-api/) — `GET /listings/2021-08-01/restrictions`
- LWA (Login with Amazon) OAuth2 for token refresh
- `requests`, `python-dotenv`

No third-party SP-API wrapper — raw HTTP calls with token caching and exponential backoff on 429s.

## Features

- Bulk processing from CSV (with or without header row)
- Auto token refresh every 50 requests
- Checkpoint/resume: if interrupted, picks up where it left off
- Rate limiting: 4 req/s (SP-API limit is 5/s)
- Exponential backoff on 429 responses
- Classifies `new` condition restrictions only (filters out `used_*` noise)

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd asin-restriction-checker
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install requests python-dotenv
```

### 2. Create an SP-API application

1. Go to [Seller Central — Develop apps](https://sellercentral.amazon.fr/apps/develop)
2. Create a new application with role **Listing restrictions** (or **Product listing**)
3. Note your **Client ID** and **Client Secret**

### 3. Get your refresh token

Authorize your app from the Developer Portal and copy the `Atzr|...` refresh token displayed after authorization.

### 4. Configure credentials

```bash
cp .env.example .env
```

Edit `.env` with your credentials — never commit this file:

```
LWA_CLIENT_ID=amzn1.application-oa2-client.YOUR_CLIENT_ID
LWA_CLIENT_SECRET=amzn1.oa2-cs.v1.YOUR_CLIENT_SECRET
LWA_REFRESH_TOKEN=Atzr|YOUR_REFRESH_TOKEN
SELLER_ID=YOUR_SELLER_ID
MARKETPLACE_ID=A13V1IB3VIYZZH
```

Marketplace IDs for reference:

| Country | ID |
|---|---|
| France | `A13V1IB3VIYZZH` |
| Germany | `A1PA6795UKMFR9` |
| Spain | `A1RKKUPIHCS9HS` |
| Italy | `APJ6JRA9NG5V4` |
| UK | `A1F83G8C2ARO7P` |
| Netherlands | `A1805IZSGTT6HS` |

## Usage

### 1. Prepare your input

Edit `asins.csv` — one ASIN per line, with a header:

```
asin
B09SHKHX48
B083FW5BXN
B0CHXMX9XC
```

### 2. Run

```bash
python check_asin.py
```

Output is written to `output.csv`:

```
ASIN,Statut,Code restriction,Message
B09SHKHX48,ELIGIBLE,,Vente libre
B083FW5BXN,APPROVAL_REQUIRED,APPROVAL_REQUIRED,Autorisation requise
B0CHXMX9XC,NOT_ELIGIBLE,NOT_ELIGIBLE,Non éligible
```

If interrupted, just re-run — the `.checkpoint.json` file tracks progress and the script resumes automatically.

## Output statuses

| Status | Meaning |
|---|---|
| `ELIGIBLE` | Can be listed immediately |
| `APPROVAL_REQUIRED` | Amazon requires an approval request before listing |
| `NOT_ELIGIBLE` | Cannot be listed with this account |
| `NOT_FOUND` | ASIN does not exist on this marketplace |
| `ERROR` | API error — check the message column |

## Known limitations

- Checks `new` condition only (`conditionType` starting with `new`). Change `CONDITION_TYPE` in the script for used conditions.
- SP-API restriction endpoint reflects the state at call time — restrictions can change.
- No support for batch requests (the restrictions endpoint is per-ASIN).
- Access scoped to a single marketplace per run; re-run with a different `MARKETPLACE_ID` for other regions.

## V2 — REST API (in progress)

A FastAPI wrapper around the same SP-API logic is currently in development, adding:
- JWT-authenticated REST endpoints (`POST /login`, `POST /check-asin`)
- PostgreSQL-backed 24h result caching (raw SQL, no ORM)
- Docker Compose setup (API + PostgreSQL containers)

See [`CLAUDE.md`](./CLAUDE.md) for architecture details and setup instructions.