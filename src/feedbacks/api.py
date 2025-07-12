from fastapi import APIRouter, Depends, HTTPException, Request, File, UploadFile, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import json
from src.database import get_async_db as get_db
from src.feedbacks import crud, schemas
from src.feedbacks.dependencies import verify_bot_token
from src.auth.dependencies import get_current_user
from src.auth.schema import User
from src.bots.crud import get_bot
from src.bots.schema import Bot


router = APIRouter(tags=["feedbacks"])


@router.post("/bots/{bot_id}/feedbacks", response_model=schemas.FeedbackResponse)
async def create_feedback(
    bot_id: int,
    rating: int = Form(...),
    message_text: str = Form(...),
    user_telegram_id: int = Form(...),
    username: str = Form(None),
    first_name: str = Form(None),
    last_name: str = Form(None),
    images: List[UploadFile] = File(None),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    token_data: Bot = Depends(verify_bot_token)
):
    """Create a new feedback with optional images (protected by bot token)."""
    if token_data.id != bot_id:
        raise HTTPException(status_code=403, detail="Bot token does not match bot ID")
    
    # Validate rating
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    # Create feedback data
    feedback_data = schemas.FeedbackCreate(
        user_telegram_id=user_telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        rating=rating,
        message_text=message_text
    )
    
    # Create feedback
    feedback = await crud.feedback_crud.create_feedback(db, feedback_data, bot_id)
    
    # Process images if provided
    if images:
        for image_file in images:
            if image_file.filename:
                # Read image data
                image_data = await image_file.read()
                
                # Upload to Azure Storage
                await crud.feedback_crud.add_feedback_image(
                    db=db,
                    feedback_id=feedback.id,
                    image_data=image_data,
                    bot_id=bot_id,
                    original_filename=image_file.filename
                )
    
    # Get feedback with images
    feedback_with_images = await crud.feedback_crud.get_feedback_by_id(db, feedback.id, bot_id)
    
    # Convert image URLs for response
    image_responses = []
    for image in feedback_with_images.images:
        accessible_url = await crud.feedback_crud.get_image_accessible_url(image)
        image_responses.append(schemas.FeedbackImage(
            id=image.id,
            feedback_id=image.feedback_id,
            file_path=accessible_url,
            storage_type=image.storage_type,
            file_size=image.file_size,
            original_filename=image.original_filename,
            created_at=image.created_at
        ))
    
    return schemas.FeedbackResponse(
        id=feedback_with_images.id,
        bot_id=feedback_with_images.bot_id,
        user_telegram_id=feedback_with_images.user_telegram_id,
        username=feedback_with_images.username,
        first_name=feedback_with_images.first_name,
        last_name=feedback_with_images.last_name,
        rating=feedback_with_images.rating,
        message_text=feedback_with_images.message_text,
        status=feedback_with_images.status,
        images=image_responses,
        created_at=feedback_with_images.created_at
    )


@router.get("/bots/{bot_id}/feedbacks", response_model=List[schemas.FeedbackResponse])
async def get_bot_feedbacks(
    bot_id: int,
    status: Optional[schemas.FeedbackStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all feedbacks for a bot (admin only)."""
    # Verify user owns this bot
    bot = await get_bot(db, bot_id)
    if not bot or bot.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    feedbacks = await crud.feedback_crud.get_feedback_list(
        db, bot_id, status, skip, limit
    )
    
    # Convert to response format with image URLs
    response_feedbacks = []
    for feedback in feedbacks:
        image_responses = []
        for image in feedback.images:
            accessible_url = await crud.feedback_crud.get_image_accessible_url(image)
            image_responses.append(schemas.FeedbackImage(
                id=image.id,
                feedback_id=image.feedback_id,
                file_path=accessible_url,
                storage_type=image.storage_type,
                file_size=image.file_size,
                original_filename=image.original_filename,
                created_at=image.created_at
            ))
        
        response_feedbacks.append(schemas.FeedbackResponse(
            id=feedback.id,
            bot_id=feedback.bot_id,
            user_telegram_id=feedback.user_telegram_id,
            username=feedback.username,
            first_name=feedback.first_name,
            last_name=feedback.last_name,
            rating=feedback.rating,
            message_text=feedback.message_text,
            status=feedback.status,
            images=image_responses,
            created_at=feedback.created_at
        ))
    
    return response_feedbacks


@router.get("/bots/{bot_id}/feedbacks/stats", response_model=schemas.FeedbackStats)
async def get_feedback_stats(
    bot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get feedback statistics for a bot (admin only)."""
    # Verify user owns this bot
    bot = await get_bot(db, bot_id)
    if not bot or bot.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    stats = await crud.feedback_crud.get_feedback_stats(db, bot_id)
    return schemas.FeedbackStats(
        total_count=stats["total_count"],
        average_rating=stats["average_rating"],
        new_count=stats["new_count"],
        read_count=stats["read_count"],
        replied_count=stats["replied_count"],
        rating_distribution=stats["rating_distribution"]
    )



@router.get("/bots/{bot_id}/feedbacks/{feedback_id}", response_model=schemas.FeedbackResponse)
async def get_feedback(
    bot_id: int,
    feedback_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific feedback by ID (admin only)."""
    # Verify user owns this bot
    bot = await get_bot(db, bot_id)
    if not bot or bot.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    feedback = await crud.feedback_crud.get_feedback_by_id(db, feedback_id, bot_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Convert image URLs for response
    image_responses = []
    for image in feedback.images:
        accessible_url = await crud.feedback_crud.get_image_accessible_url(image)
        image_responses.append(schemas.FeedbackImage(
            id=image.id,
            feedback_id=image.feedback_id,
            file_path=accessible_url,
            storage_type=image.storage_type,
            file_size=image.file_size,
            original_filename=image.original_filename,
            created_at=image.created_at
        ))
    
    return schemas.FeedbackResponse(
        id=feedback.id,
        bot_id=feedback.bot_id,
        user_telegram_id=feedback.user_telegram_id,
        username=feedback.username,
        first_name=feedback.first_name,
        last_name=feedback.last_name,
        rating=feedback.rating,
        message_text=feedback.message_text,
        status=feedback.status,
        images=image_responses,
        created_at=feedback.created_at
    )


@router.patch("/bots/{bot_id}/feedbacks/{feedback_id}/status", response_model=schemas.FeedbackResponse)
async def update_feedback_status(
    bot_id: int,
    feedback_id: int,
    status_update: schemas.FeedbackStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update feedback status (admin only)."""
    # Verify user owns this bot
    bot = await get_bot(db, bot_id)
    if not bot or bot.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    feedback = await crud.feedback_crud.update_feedback_status(
        db, feedback_id, bot_id, status_update.status
    )
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Convert image URLs for response
    image_responses = []
    for image in feedback.images:
        accessible_url = await crud.feedback_crud.get_image_accessible_url(image)
        image_responses.append(schemas.FeedbackImage(
            id=image.id,
            feedback_id=image.feedback_id,
            file_path=accessible_url,
            storage_type=image.storage_type,
            file_size=image.file_size,
            original_filename=image.original_filename,
            created_at=image.created_at
        ))
    
    return schemas.FeedbackResponse(
        id=feedback.id,
        bot_id=feedback.bot_id,
        user_telegram_id=feedback.user_telegram_id,
        username=feedback.username,
        first_name=feedback.first_name,
        last_name=feedback.last_name,
        rating=feedback.rating,
        message_text=feedback.message_text,
        status=feedback.status,
        images=image_responses,
        created_at=feedback.created_at
    )




@router.delete("/bots/{bot_id}/feedbacks/{feedback_id}")
async def delete_feedback(
    bot_id: int,
    feedback_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a feedback and its images (admin only)."""
    # Verify user owns this bot
    bot = await get_bot(db, bot_id)
    if not bot or bot.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    success = await crud.feedback_crud.delete_feedback(db, feedback_id, bot_id)
    if not success:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return {"message": "Feedback deleted successfully"} 