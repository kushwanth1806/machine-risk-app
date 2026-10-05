import json
import os

import requests
from fastapi import APIRouter, HTTPException

try:
    from ..database import get_connection
    from ..schemas import MachineIn
    from .fields import get_all_fields
except ImportError:  # pragma: no cover
    from database import get_connection
    from routes.fields import get_all_fields
    from schemas import MachineIn

router = APIRouter(prefix="/api/machines", tags=["machines"])

ML_URL = os.environ.get("ML_URL", "http://127.0.0.1:8001")


def validate_values(fields, values):
    """Check the submitted values against the configured fields."""
    cleaned = {}
    for field in fields:
        value = values.get(str(field["id"]))

        if value is None or value == "":
            if field["required"]:
                raise HTTPException(status_code=400, detail=f"{field['name']} is required")
            continue

        if field["type"] == "number":
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail=f"{field['name']} must be a number")
        elif field["type"] == "dropdown":
            if value not in field["options"]:
                raise HTTPException(status_code=400, detail=f"Invalid option for {field['name']}")
        else:
            value = str(value)

        cleaned[str(field["id"])] = value
    return cleaned


@router.get("")
def list_machines():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM machines ORDER BY id").fetchall()
    conn.close()
    return [{"id": r["id"], "values": json.loads(r["data"])} for r in rows]


@router.post("", status_code=201)
def create_machine(machine: MachineIn):
    conn = get_connection()
    cleaned = validate_values(get_all_fields(conn), machine.values)
    cursor = conn.execute("INSERT INTO machines (data) VALUES (?)", (json.dumps(cleaned),))
    conn.commit()
    conn.close()
    return {"id": cursor.lastrowid, "values": cleaned}


@router.put("/{machine_id}")
def update_machine(machine_id: int, machine: MachineIn):
    conn = get_connection()
    exists = conn.execute("SELECT id FROM machines WHERE id = ?", (machine_id,)).fetchone()
    if exists is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Machine not found")

    cleaned = validate_values(get_all_fields(conn), machine.values)
    conn.execute("UPDATE machines SET data = ? WHERE id = ?", (json.dumps(cleaned), machine_id))
    conn.commit()
    conn.close()
    return {"id": machine_id, "values": cleaned}


@router.delete("/{machine_id}", status_code=204)
def delete_machine(machine_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM machines WHERE id = ?", (machine_id,))
    conn.commit()
    conn.close()


@router.post("/{machine_id}/predict")
def predict_risk(machine_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM machines WHERE id = ?", (machine_id,)).fetchone()
    fields = get_all_fields(conn)
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Machine not found")

    # the ML service works with field names, not ids
    values = json.loads(row["data"])
    machine_data = {f["name"]: values.get(str(f["id"])) for f in fields}

    try:
        response = requests.post(f"{ML_URL}/predict", json={"data": machine_data}, timeout=10)
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="ML service is not running (port 8001)")

    if response.status_code != 200:
        detail = response.json().get("detail", "Prediction failed")
        raise HTTPException(status_code=response.status_code, detail=detail)
    return response.json()
