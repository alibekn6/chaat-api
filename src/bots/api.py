from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.database import get_async_db
from src.auth.schema import User
from src.auth.dependencies import get_current_user
from src.bots import models, crud

router = APIRouter(tags=["bots"])


@router.post("/", response_model=models.Bot, status_code=status.HTTP_201_CREATED)
async def create_bot_record(
    bot: models.BotCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new bot record in the database.
    This is the first step before generating code for the bot.
    """
    return await crud.create_bot(db=db, bot=bot, owner_id=current_user.id)


@router.get("/", response_model=List[models.Bot])
async def read_bots(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve all bots owned by the current user.
    """
    return await crud.get_bots_by_owner(db, owner_id=current_user.id)


@router.get("/{bot_id}", response_model=models.Bot)
async def read_bot(
    bot_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a single bot by its ID.
    """
    db_bot = await crud.get_bot(db, bot_id=bot_id)
    if db_bot is None:
        raise HTTPException(status_code=404, detail="Bot not found")
    if db_bot.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return db_bot


@router.put("/{bot_id}", response_model=models.Bot)
async def update_bot_details(
    bot_id: int,
    bot_update: models.BotUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a bot's details, such as its name or requirements.
    """
    db_bot = await crud.get_bot(db, bot_id=bot_id)
    if db_bot is None:
        raise HTTPException(status_code=404, detail="Bot not found")
    if db_bot.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return await crud.update_bot(db=db, bot_id=bot_id, bot_update=bot_update)


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot_record(
    bot_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a bot record from the database.
    Note: This does not stop a running bot process. Use the /ai/bots/{bot_id}/stop endpoint for that.
    """
    db_bot = await crud.get_bot(db, bot_id=bot_id)
    if db_bot and db_bot.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    if db_bot is None:
        return
    # Stop the bot process if running
    if db_bot.pid:
        from src.ai.manager import bot_manager
        await bot_manager.stop_bot(db_bot.pid)
        await crud.update_bot_pid(db, bot_id=bot_id, pid=None)
        await crud.update_bot_status(db, bot_id=bot_id, is_running=False)
    
    # Clean up knowledge base if it exists
    if db_bot.bot_type == "qa_knowledge_base":
        from src.ai.knowledge import delete_knowledge_base
        delete_knowledge_base(bot_id)
    
    await crud.delete_bot(db=db, bot_id=bot_id) 