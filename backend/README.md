# ANNADATA - Backend

Field Intelligence & Smart Crop Decision Support API built with FastAPI.

## Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
```

## Run

The frontend is configured (in `frontend/.env`) to call the API at
`http://127.0.0.1:8001`, so start the backend on the same port:

```bash
uvicorn app.main:app --reload --port 8001
```

CORS already allows the Vite dev server (`http://localhost:5173` and
`http://127.0.0.1:5173`). If you run the API on a different port, set
`VITE_API_BASE_URL` in `frontend/.env` to match.

## API Docs

- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc
- Health: http://localhost:8001/health
