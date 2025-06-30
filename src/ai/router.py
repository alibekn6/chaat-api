from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
import aiofiles

from src.database import get_async_db
from src.auth.dependencies import get_current_user
from src.auth.schema import User
from src.bots import models as bot_models
from src.bots import crud as bots_crud
from src.ai.generator import generate_bot_code
from src.ai.manager import bot_manager
from src.ai.knowledge import process_and_store_knowledge_base, KNOWLEDGE_BASES_DIR

router = APIRouter(prefix="/ai", tags=["AI Bot Generation"])

# Ensure knowledge bases directory exists
KNOWLEDGE_BASES_DIR.mkdir(exist_ok=True)


@router.post("/bots/{bot_id}/knowledge/upload")
async def upload_knowledge_base(
    bot_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a PDF file to create a knowledge base for a Q&A bot.
    """
    db_bot = await bots_crud.get_bot(db, bot_id=bot_id)
    if not db_bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    if db_bot.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if this is a Q&A bot
    if db_bot.bot_type != "qa_knowledge_base":
        raise HTTPException(
            status_code=400, 
            detail="Knowledge base upload is only available for Q&A bots"
        )
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Create bot-specific directory
    bot_dir = KNOWLEDGE_BASES_DIR / str(bot_id)
    bot_dir.mkdir(exist_ok=True)
    
    # Save the uploaded file
    file_path = bot_dir / file.filename
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Start background processing
    background_tasks.add_task(
        process_and_store_knowledge_base, 
        bot_id, 
        str(file_path)
    )
    
    # Update bot status to processing
    await bots_crud.update_bot_knowledge_status(db, bot_id, "processing")
    
    return {"message": "Knowledge base upload successful. Processing has begun."}


@router.get("/bots/{bot_id}/knowledge/status")
async def get_knowledge_base_status(
    bot_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the status of a bot's knowledge base.
    """
    db_bot = await bots_crud.get_bot(db, bot_id=bot_id)
    if not db_bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    if db_bot.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return {
        "bot_id": bot_id,
        "knowledge_base_status": db_bot.knowledge_base_status,
        "bot_type": db_bot.bot_type
    }


@router.post("/bots/{bot_id}/generate", response_model=bot_models.Bot)
async def generate_bot_code_endpoint(
    bot_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates Python code for a Telegram bot based on stored requirements and bot type.
    """
    db_bot = await bots_crud.get_bot(db, bot_id=bot_id)
    if not db_bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    if db_bot.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        generated_code = await generate_bot_code(
            bot_id=db_bot.id,
            bot_type=db_bot.bot_type,
            requirements=db_bot.requirements,
            knowledge_base_status=db_bot.knowledge_base_status
        )

        updated_bot = await bots_crud.update_bot_code(
            db, bot_id=bot_id, code=generated_code
        )
        return updated_bot
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=400, detail=str(e))


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

    # Stop any previously running instance of the same bot
    if db_bot.pid:
        await bot_manager.stop_bot(db_bot.pid)

    # Deploy using the bot manager
    pid = await bot_manager.deploy_bot(
        bot_id=str(db_bot.id),
        bot_code=db_bot.generated_code,
        bot_token=db_bot.bot_token,
    )

    # Save new PID and update status in DB
    await bots_crud.update_bot_pid(db, bot_id=db_bot.id, pid=pid)
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
    await bot_manager.stop_bot(pid=db_bot.pid)

    # Clear PID and update bot status in DB
    await bots_crud.update_bot_pid(db, bot_id=db_bot.id, pid=None)
    updated_bot = await bots_crud.update_bot_status(db, bot_id=db_bot.id, is_running=False)
    return updated_bot 