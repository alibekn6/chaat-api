from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Sequence

from src.database import get_async_db
from src.auth.schema import User
from src.bots.schema import Bot
from src.auth.dependencies import get_current_user
from src.bots import models, crud

router = APIRouter(tags=["bots"])


@router.post("/", response_model=models.Bot)
async def create_bot(
    bot: models.BotCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    return await crud.create_bot(db=db, bot=bot, owner_id=current_user.id)


@router.get("/", response_model=List[models.Bot])
async def read_bots(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
) -> Sequence[Bot]:
    bots = await crud.get_bots_by_owner(
        db, owner_id=current_user.id
    )
    return bots


@router.get("/{bot_id}", response_model=models.Bot)
async def read_bot(
    bot_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    db_bot = await crud.get_bot(db, bot_id=bot_id)
    if db_bot is None:
        raise HTTPException(status_code=404, detail="Bot not found")
    if db_bot.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return db_bot


@router.put("/{bot_id}", response_model=models.Bot)
async def update_bot(
    bot_id: int,
    bot_update: models.BotUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    db_bot = await crud.get_bot(db, bot_id=bot_id)
    if db_bot is None:
        raise HTTPException(status_code=404, detail="Bot not found")
    if db_bot.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return await crud.update_bot(db=db, bot_id=bot_id, bot_update=bot_update)


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot(
    bot_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    db_bot = await crud.get_bot(db, bot_id=bot_id)
    if db_bot and db_bot.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    if db_bot is None:
        return
    await crud.delete_bot(db=db, bot_id=bot_id)


@router.post("/{bot_id}/knowledge_sources/", response_model=models.KnowledgeSource)
async def create_knowledge_source_for_bot(
    bot_id: int,
    ks: models.KnowledgeSourceCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    db_bot = await crud.get_bot(db, bot_id=bot_id)
    if db_bot is None:
        raise HTTPException(status_code=404, detail="Bot not found")
    if db_bot.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return await crud.create_knowledge_source(db=db, ks=ks, bot_id=bot_id)


@router.get("/{bot_id}/knowledge_sources/", response_model=List[models.KnowledgeSource])
async def read_knowledge_sources_for_bot(
    bot_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    db_bot = await crud.get_bot(db, bot_id=bot_id)
    if db_bot is None:
        raise HTTPException(status_code=404, detail="Bot not found")
    if db_bot.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    ks = await crud.get_knowledge_sources_by_bot(
        db, bot_id=bot_id, skip=skip, limit=limit
    )
    return ks 