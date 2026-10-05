import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

try:
    from .database import init_db
    from .routes import fields, machines
except ImportError:  # pragma: no cover
    from database import init_db
    from routes import fields, machines

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = FastAPI(title="Machine Manager")
init_db()

app.include_router(fields.router)
app.include_router(machines.router)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def home():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
