import uuid

from pydantic import BaseModel


class Me(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    has_profile: bool
