# Dynamic Machine Data Management & Local Risk Prediction

A small web app to configure machine fields dynamically, manage machine records (CRUD), and predict a machine's risk level (Low / Medium / High) with a local Python ML model.

## Technologies
- **Backend:** Python, FastAPI (also serves the frontend)
- **Frontend:** Plain HTML/CSS/JavaScript (single page, no build step)
- **Database:** SQLite (created automatically on first run, no setup)
- **ML:** Python, scikit-learn (RandomForest) trained on synthetic data, served by a separate local FastAPI service. No cloud AI or external APIs.

## Setup & Run
Requires Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Open **two terminals** (venv activated in both):

**1. Start the Python ML component (port 8001)**
```bash
cd ml_service
python train.py                      # optional: trains and saves model.joblib (auto-trains on first start if missing)
uvicorn service:app --port 8001
```

**2. Start the backend + UI (port 8000)**
```bash
cd backend
uvicorn main:app --port 8000
```

Open http://127.0.0.1:8000. Set the `ML_URL` environment variable to point the backend at a different ML address (default `http://127.0.0.1:8001`).

## Project Structure
```
backend/
  main.py            app entry point, serves the frontend
  database.py        SQLite connection and table setup
  schemas.py         request models
  routes/fields.py   field configuration endpoints
  routes/machines.py machine CRUD + prediction endpoint
frontend/            index.html, style.css, app.js
ml_service/
  train.py           generates synthetic data and trains the model
  service.py         prediction API
```

## Architecture
```
Web UI (frontend/index.html)
   │  REST/JSON
Backend (backend/main.py, :8000)  ──►  SQLite (fields + machines tables)
   │  HTTP POST /predict  {field name: value}
Python ML service (ml_service/service.py, :8001) ── RandomForest (model.joblib)
   │  {risk_level, confidence, features_used, features_ignored}
Backend ──► Web UI
```

**Database design (no schema change per field):**
- `fields(id, name, type, required, options)`: one row per configured field. `type` is `text`, `number` or `dropdown`; `options` is a JSON list for dropdowns.
- `machines(id, data)`: `data` is a JSON object `{field_id: value}`.

Adding a field is just an `INSERT` into `fields`. The UI reads `/api/fields` and builds the table columns and the create/edit form from it. The backend validates values against the field definitions (required, number, dropdown option).

**API:** `GET/POST /api/fields`, `PUT/DELETE /api/fields/{id}`, `GET/POST /api/machines`, `PUT/DELETE /api/machines/{id}`, `POST /api/machines/{id}/predict`.

## The ML model
Inputs: `Temperature`, `Pressure` (numbers) and `Vibration` (Low/Medium/High). The model is trained on synthetic data (`train.py`) where risk rises with all three. Accuracy is about 0.89 on a held-out split; it exists to demonstrate the flow, not to be accurate.

The backend sends the machine's values keyed by field **name**, and the ML service matches `temperature`, `pressure` and `vibration` case-insensitively. A machine missing one of these gets a clear error.

## The `Humidity` scenario
1. **How the app handles the new field:** adding "Humidity (Number)" in the Field Configuration tab inserts a row in `fields`. The records table and form show it immediately, and values are stored in each machine's JSON `data`. No code or schema change.
2. **Can the existing model use it?** No. The model was trained on exactly three features and has no weights for Humidity. The ML service does not fail: it ignores unknown fields and returns them in `features_ignored`, which the UI displays. Predictions are unchanged by Humidity.
3. **What's needed for the model to use it:**
   - Training data that includes Humidity (real historical records with risk labels, or an updated synthetic generator).
   - Add `humidity` to `FEATURES` in `train.py`, handle missing values (imputation) for older machines without a value, and retrain.
   - Update the input handling in `service.py` and redeploy the new `model.joblib`.
   - For a fully dynamic setup, add a configurable "use for prediction" mapping between fields and model features, plus model versioning.

## Notes / limitations
- Field type cannot be changed after creation (it would invalidate stored values). Deleting a field removes its values from all machines.
- No authentication; not production-ready by design. No secrets are used or committed.
