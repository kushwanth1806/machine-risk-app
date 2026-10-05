from typing import Any

from pydantic import BaseModel, Field

FIELD_TYPES = ("text", "number", "dropdown")


class FieldIn(BaseModel):
    name: str
    type: str
    required: bool = False
    options: list[str] = Field(default_factory=list)


class MachineIn(BaseModel):
    # key = field id (as string), value = what the user entered
    values: dict[str, Any]
