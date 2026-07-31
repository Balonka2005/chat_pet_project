from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.user import UserRead


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class MessageRead(BaseModel):
    id: int
    content: str
    author: UserRead
    room_id: int
    created_at: datetime

    class Config:
        from_attributes = True
