from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.auth.dependencies import get_current_user
from src.auth.schema import User
from src.bots import models as bot_models
from src.bots import crud as bots_crud
from src.ai.generator import AIBotGenerator
from src.ai.manager import bot_manager

router = APIRouter(prefix="/ai", tags=["AI Bot Generation"])


@router.post("/bots/{bot_id}/generate", response_model=bot_models.Bot)
async def generate_bot_code(
    bot_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates Python code for a Telegram bot based on stored requirements.
    """
    db_bot = await bots_crud.get_bot(db, bot_id=bot_id)
    if not db_bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    if db_bot.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    generator = AIBotGenerator()
    generated_code = await generator.generate_bot_code(db_bot.requirements)

    updated_bot = await bots_crud.update_bot_code(
        db, bot_id=bot_id, code=generated_code
    )
    return updated_bot


@router.post("/bots/{bot_id}/deploy", response_model=bot_models.Bot)
async def deploy_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    db_bot = await bots_crud.get_bot(db, bot_id)

    # Check ownership and if bot exists
    if not db_bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    if db_bot.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    if not db_bot.generated_code:
        raise HTTPException(
            status_code=400, detail="Bot code has not been generated yet."
        )

    # Deploy using the bot manager
    await bot_manager.deploy_bot(
        bot_id=str(db_bot.id),
        bot_code=db_bot.generated_code,
        bot_token=db_bot.bot_token,
    )

    # Update bot status in DB
    updated_bot = await bots_crud.update_bot_status(db, bot_id=db_bot.id, is_running=True)
    return updated_bot


@router.post("/bots/{bot_id}/stop", response_model=bot_models.Bot)
async def stop_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    db_bot = await bots_crud.get_bot(db, bot_id)

    # Check ownership and if bot exists
    if not db_bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    if db_bot.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Stop using the bot manager
    await bot_manager.stop_bot(bot_id=str(db_bot.id))

    # Update bot status in DB
    updated_bot = await bots_crud.update_bot_status(db, bot_id=db_bot.id, is_running=False)
    return updated_bot 