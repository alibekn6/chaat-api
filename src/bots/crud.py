from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from src.bots import models, schema


async def create_bot(db: AsyncSession, bot: models.BotCreate, owner_id: int):
    db_bot = schema.Bot(**bot.model_dump(), owner_id=owner_id)
    db.add(db_bot)
    await db.flush()
    bot_id = db_bot.id
    await db.commit()
    return await get_bot(db, bot_id)


async def get_bot(db: AsyncSession, bot_id: int):
    result = await db.execute(
        select(schema.Bot)
        .options(selectinload(schema.Bot.knowledge_sources))
        .filter(schema.Bot.id == bot_id)
    )
    return result.scalar_one_or_none()


async def get_bots_by_owner(
    db: AsyncSession, owner_id: int
):
    result = await db.execute(
        select(schema.Bot)
        .options(selectinload(schema.Bot.knowledge_sources))
        .filter(schema.Bot.owner_id == owner_id)
    )
    return result.scalars().all()


async def create_knowledge_source(
    db: AsyncSession, ks: models.KnowledgeSourceCreate, bot_id: int
):
    db_ks = schema.KnowledgeSource(**ks.model_dump(), bot_id=bot_id)
    db.add(db_ks)
    await db.commit()
    await db.refresh(db_ks)
    return db_ks


async def get_knowledge_sources_by_bot(
    db: AsyncSession, bot_id: int, skip: int = 0, limit: int = 100
):
    result = await db.execute(
        select(schema.KnowledgeSource)
        .filter(schema.KnowledgeSource.bot_id == bot_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def update_bot(db: AsyncSession, bot_id: int, bot_update: models.BotUpdate):
    db_bot = await get_bot(db, bot_id)
    if not db_bot:
        return None
    update_data = bot_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_bot, key, value)
    db.add(db_bot)
    await db.commit()
    await db.refresh(db_bot)
    return db_bot


async def delete_bot(db: AsyncSession, bot_id: int):
    db_bot = await get_bot(db, bot_id)
    if not db_bot:
        return None
    await db.delete(db_bot)
    await db.commit()
    return db_bot 