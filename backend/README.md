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
`http://127.0.0.1:8000`, so start the backend on the same port:

```bash
uvicorn app.main:app --reload --port 8000
```

CORS already allows the Vite dev server (`http://localhost:5173` and
`http://127.0.0.1:5173`). If you run the API on a different port, set
`VITE_API_BASE_URL` in `frontend/.env` to match.

## AI Crop Disease Identification model

This feature runs a real image classifier, so it needs a model file that is not
stored in git (it is ~92 MB):

```bash
python scripts/download_disease_model.py
```

This downloads `cropguard.onnx` and `classes.json` into
`backend/models/plant_disease/`. Source: `XiElonMAsk/cropguard-models`
(CC-BY-SA-4.0) - a ResNet50 fine-tuned on the PlantVillage dataset (38 classes
across 14 crops). Without the model, the `/api/disease/assess` endpoint returns
`503` with setup instructions; everything else keeps working.

## API Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health
