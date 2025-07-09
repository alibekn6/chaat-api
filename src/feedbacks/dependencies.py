from fastapi import HTTPException, Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.database import get_async_db
from src.bots import crud as bots_crud


async def verify_bot_token(
    x_bot_token: Optional[str] = Header(None, description="Bot token for authorization"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Verify that the request comes from a legitimate bot.
    Checks the X-Bot-Token header against the bot's stored token.
    Returns the bot object if token is valid.
    """
    if not x_bot_token:
        raise HTTPException(
            status_code=401, 
            detail="Missing bot token. Include X-Bot-Token header."
        )
    
    # Find bot by token
    db_bot = await bots_crud.get_bot_by_token(db, bot_token=x_bot_token)
    if not db_bot:
        raise HTTPException(
            status_code=403, 
            detail="Invalid bot token"
        )
    
    return db_bot 