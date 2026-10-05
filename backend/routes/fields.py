import json
import sqlite3

from fastapi import APIRouter, HTTPException

try:
    from ..database import get_connection
    from ..schemas import FIELD_TYPES, FieldIn
except ImportError:  # pragma: no cover
    from database import get_connection
    from schemas import FIELD_TYPES, FieldIn

router = APIRouter(prefix="/api/fields", tags=["fields"])


def row_to_field(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "type": row["type"],
        "required": bool(row["required"]),
        "options": json.loads(row["options"]),
    }


def get_all_fields(conn):
    rows = conn.execute("SELECT * FROM fields ORDER BY id").fetchall()
    return [row_to_field(r) for r in rows]


def check_field(field: FieldIn):
    field.name = field.name.strip()
    if not field.name:
        raise HTTPException(status_code=400, detail="Field name is required")
    if field.type not in FIELD_TYPES:
        raise HTTPException(status_code=400, detail="Type must be text, number or dropdown")

    field.options = [o.strip() for o in field.options if o.strip()]
    if field.type == "dropdown" and len(field.options) == 0:
        raise HTTPException(status_code=400, detail="Dropdown needs at least one option")
    if field.type != "dropdown":
        field.options = []


@router.get("")
def list_fields():
    conn = get_connection()
    fields = get_all_fields(conn)
    conn.close()
    return fields


@router.post("", status_code=201)
def create_field(field: FieldIn):
    check_field(field)
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO fields (name, type, required, options) VALUES (?, ?, ?, ?)",
            (field.name, field.type, int(field.required), json.dumps(field.options)),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Field name already exists")
    finally:
        conn.close()
    return {"id": cursor.lastrowid, **field.model_dump()}


@router.put("/{field_id}")
def update_field(field_id: int, field: FieldIn):
    check_field(field)
    conn = get_connection()
    existing = conn.execute("SELECT * FROM fields WHERE id = ?", (field_id,)).fetchone()
    if existing is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Field not found")
    if existing["type"] != field.type:
        conn.close()
        raise HTTPException(status_code=400, detail="Field type cannot be changed")

    try:
        conn.execute(
            "UPDATE fields SET name = ?, required = ?, options = ? WHERE id = ?",
            (field.name, int(field.required), json.dumps(field.options), field_id),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Field name already exists")
    finally:
        conn.close()
    return {"id": field_id, **field.model_dump()}


@router.delete("/{field_id}", status_code=204)
def delete_field(field_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM fields WHERE id = ?", (field_id,))

    # remove the deleted field's values from every machine
    for machine in conn.execute("SELECT id, data FROM machines").fetchall():
        data = json.loads(machine["data"])
        if str(field_id) in data:
            del data[str(field_id)]
            conn.execute(
                "UPDATE machines SET data = ? WHERE id = ?",
                (json.dumps(data), machine["id"]),
            )
    conn.commit()
    conn.close()
