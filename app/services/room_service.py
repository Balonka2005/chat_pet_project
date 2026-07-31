from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.message import Message
from app.models.room import Room
from app.schemas.room import RoomCreate


async def get_room_by_name(db: AsyncSession, name: str) -> Room | None:
    result = await db.execute(select(Room).where(Room.name == name))
    return result.scalar_one_or_none()


async def get_room_by_id(db: AsyncSession, room_id: int) -> Room | None:
    result = await db.execute(select(Room).where(Room.id == room_id))
    return result.scalar_one_or_none()


async def list_rooms(db: AsyncSession) -> list[Room]:
    result = await db.execute(select(Room).order_by(Room.created_at.desc()))
    return list(result.scalars().all())


async def create_room(db: AsyncSession, room_in: RoomCreate, creator_id: int) -> Room:
    room = Room(name=room_in.name, description=room_in.description, created_by=creator_id)
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room


async def delete_room(db: AsyncSession, room: Room) -> None:
    await db.delete(room)
    await db.commit()


async def get_room_messages(db: AsyncSession, room_id: int, limit: int = 50, offset: int = 0) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.room_id == room_id)
        .options(selectinload(Message.author))
        .order_by(Message.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def create_message(db: AsyncSession, room_id: int, author_id: int, content: str) -> Message:
    message = Message(content=content, room_id=room_id, author_id=author_id)
    db.add(message)
    await db.commit()
    await db.refresh(message, attribute_names=["author"])
    return message
