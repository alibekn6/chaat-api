from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from src.bots import models, schema


async def create_bot(db: AsyncSession, bot: models.BotCreate, owner_id: int) -> schema.Bot:
    db_bot = schema.Bot(**bot.model_dump(), owner_id=owner_id)
    db.add(db_bot)
    await db.commit()
    await db.refresh(db_bot)
    return db_bot


async def get_bot(db: AsyncSession, bot_id: int) -> schema.Bot | None:
    result = await db.execute(select(schema.Bot).filter(schema.Bot.id == bot_id))
    return result.scalar_one_or_none()


async def get_bots_by_owner(
    db: AsyncSession, owner_id: int
) -> list[schema.Bot]:
    result = await db.execute(
        select(schema.Bot).filter(schema.Bot.owner_id == owner_id)
    )
    return list(result.scalars().all())


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


async def update_bot_status(db: AsyncSession, bot_id: int, is_running: bool) -> schema.Bot:
    db_bot = await get_bot(db, bot_id)
    db_bot.is_running = is_running
    db_bot.status = "running" if is_running else "stopped"
    await db.commit()
    await db.refresh(db_bot)
    return db_bot


async def update_bot_code(db: AsyncSession, bot_id: int, code: str) -> schema.Bot:
    db_bot = await get_bot(db, bot_id)
    db_bot.generated_code = code
    db_bot.status = "generated"
    await db.commit()
    await db.refresh(db_bot)
    return db_bot


async def delete_bot(db: AsyncSession, bot_id: int):
    db_bot = await get_bot(db, bot_id)
    if db_bot:
        await db.delete(db_bot)
        await db.commit()
    return db_bot 