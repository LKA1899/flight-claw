# flight-claw

Flight Claw uses a React frontend with a FastAPI backend that serves JSON APIs for the frontend.

## Tech Stack

- Python 3.11+
- FastAPI
- SQLite
- SQLAlchemy
- React + Vite + TypeScript
- Tailwind CSS + Radix UI
- Playwright
- APScheduler

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

cd frontend
npm install
```

## Run

Start the backend API:

```bash
python run.py
```

Start the frontend:

```bash
cd frontend
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

Vite proxies `/api` to `http://localhost:8000` by default. You can also override the API base URL with `frontend/.env.example`.

## Basic Flow

1. Create or update routes in the monitors page.
2. Maintain travel dates for each route.
3. Start an immediate scan or configure scheduled scans.
4. Check scan progress in the scans page.
5. Review results in tasks, prices, plans, reports, and related result pages.
