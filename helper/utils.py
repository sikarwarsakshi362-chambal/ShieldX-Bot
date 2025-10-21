import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "modules"))

from pyrogram import Client, enums, filters
from sqlalchemy.ext.asyncio import AsyncSession
from config import (
    async_session,
    Base,
    DEFAULT_CONFIG,
    DEFAULT_PUNISHMENT,
    DEFAULT_WARNING_LIMIT
)
from sqlalchemy import Column, Integer, String, select

# ====================== PostgreSQL Tables (MongoDB replaced) ======================
class Warning(Base):
    __tablename__ = "warnings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    count = Column(Integer, default=0)

class Punishment(Base):
    __tablename__ = "punishments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String, nullable=False)
    mode = Column(String, default="warn")
    limit = Column(Integer, default=DEFAULT_WARNING_LIMIT)
    penalty = Column(String, default=DEFAULT_PUNISHMENT)

class Allowlist(Base):
    __tablename__ = "allowlists"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)

# ====================== Warning Functions ======================
async def get_warnings(chat_id: str, user_id: str):
    async with async_session() as session:
        result = await session.execute(
            select(Warning).where(Warning.chat_id==chat_id, Warning.user_id==user_id)
        )
        return result.scalar_one_or_none()

async def increment_warning(chat_id: str, user_id: str) -> int:
    async with async_session() as session:
        warning = await get_warnings(chat_id, user_id)
        if warning:
            warning.count += 1
            await session.commit()
            return warning.count
        else:
            new_warning = Warning(chat_id=chat_id, user_id=user_id, count=1)
            session.add(new_warning)
            await session.commit()
            return 1

async def reset_warnings(chat_id: str, user_id: str):
    async with async_session() as session:
        warning = await get_warnings(chat_id, user_id)
        if warning:
            await session.delete(warning)
            await session.commit()

# ====================== Punishment Functions ======================
async def get_config(chat_id: str):
    async with async_session() as session:
        result = await session.execute(
            select(Punishment).where(Punishment.chat_id==chat_id)
        )
        doc = result.scalar_one_or_none()
        if doc:
            return doc.mode, doc.limit, doc.penalty
        return DEFAULT_CONFIG

async def update_config(chat_id: str, mode=None, limit=None, penalty=None):
    async with async_session() as session:
        result = await session.execute(
            select(Punishment).where(Punishment.chat_id==chat_id)
        )
        doc = result.scalar_one_or_none()
        if doc:
            if mode is not None: doc.mode = mode
            if limit is not None: doc.limit = limit
            if penalty is not None: doc.penalty = penalty
            await session.commit()
        else:
            new_doc = Punishment(
                chat_id=chat_id,
                mode=mode or "warn",
                limit=limit or DEFAULT_WARNING_LIMIT,
                penalty=penalty or DEFAULT_PUNISHMENT
            )
            session.add(new_doc)
            await session.commit()

# ====================== Allowlist Functions ======================
async def is_allowlisted(chat_id: str, user_id: str) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(Allowlist).where(Allowlist.chat_id==chat_id, Allowlist.user_id==user_id)
        )
        return result.scalar_one_or_none() is not None

async def add_allowlist(chat_id: str, user_id: str):
    async with async_session() as session:
        if not await is_allowlisted(chat_id, user_id):
            session.add(Allowlist(chat_id=chat_id, user_id=user_id))
            await session.commit()

async def remove_allowlist(chat_id: str, user_id: str):
    async with async_session() as session:
        result = await session.execute(
            select(Allowlist).where(Allowlist.chat_id==chat_id, Allowlist.user_id==user_id)
        )
        doc = result.scalar_one_or_none()
        if doc:
            await session.delete(doc)
            await session.commit()

async def get_allowlist(chat_id: str) -> list:
    async with async_session() as session:
        result = await session.execute(
            select(Allowlist).where(Allowlist.chat_id==chat_id)
        )
        docs = result.scalars().all()
        return [doc.user_id for doc in docs]

# ====================== Misc Default Settings ======================
def get_default_settings():
    return {
        "abuse_on": True,
        "nsfw_on": True,
        "bio_link_on": True,
        "clean_on": False,
        "delete_minutes": 30
    }
