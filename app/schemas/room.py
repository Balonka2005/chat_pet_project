from datetime import datetime

from pydantic import BaseModel, Field


class RoomCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None


class RoomRead(BaseModel):
    id: int
    name: str
    description: str | None
    created_by: int | None
    created_at: datetime

    class Config:
        from_attributes = True
