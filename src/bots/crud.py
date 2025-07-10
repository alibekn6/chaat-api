from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from src.bots import models, schema


async def create_bot(db: AsyncSession, bot: models.BotCreate, owner_id: int) -> schema.Bot:
    bot_data = bot.model_dump()
    db_bot = schema.Bot(**bot_data, owner_id=owner_id)
    db.add(db_bot)
    await db.commit()
    await db.refresh(db_bot)
    return db_bot


async def get_bot(db: AsyncSession, bot_id: int) -> schema.Bot | None:
    result = await db.execute(select(schema.Bot).filter(schema.Bot.id == bot_id))
    return result.scalar_one_or_none()


async def get_bot_by_token(db: AsyncSession, bot_token: str) -> schema.Bot | None:
    result = await db.execute(select(schema.Bot).filter(schema.Bot.bot_token == bot_token).limit(1))
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

    # Check if critical fields that invalidate generated code have changed
    if (
        "requirements" in update_data and update_data["requirements"] != db_bot.requirements
    ) or (
        "bot_token" in update_data and update_data["bot_token"] != db_bot.bot_token
    ):
        db_bot.status = "created"
        db_bot.generated_code = None
        db_bot.is_running = False
        # We don't clear the PID here, as a separate stop call is needed.
        # But we could kill it here if needed. For now, just reset status.

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


async def update_bot_pid(db: AsyncSession, bot_id: int, pid: int | None) -> schema.Bot:
    db_bot = await get_bot(db, bot_id)
    if db_bot:
        db_bot.pid = pid
        await db.commit()
        await db.refresh(db_bot)
    return db_bot


async def update_bot_knowledge_status(db: AsyncSession, bot_id: int, status: str) -> schema.Bot:
    """Update the knowledge base status for a bot."""
    db_bot = await get_bot(db, bot_id)
    if db_bot:
        db_bot.knowledge_base_status = status
        await db.commit()
        await db.refresh(db_bot)
    return db_bot


async def delete_bot(db: AsyncSession, bot_id: int):
    db_bot = await get_bot(db, bot_id)
    if db_bot:
        await db.delete(db_bot)
        await db.commit()
    return db_bot 