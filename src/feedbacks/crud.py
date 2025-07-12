import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.feedbacks.models import Feedback, FeedbackImage
from src.feedbacks.schemas import FeedbackCreate, FeedbackUpdate, FeedbackStatus
from src.utils.azure_storage import storage_manager


class FeedbackCRUD:
    """CRUD operations for feedback management."""
    
    async def create_feedback(
        self, 
        db: AsyncSession, 
        feedback_data: FeedbackCreate, 
        bot_id: int
    ) -> Feedback:
        """Create a new feedback."""
        feedback = Feedback(
            bot_id=bot_id,
            user_telegram_id=feedback_data.user_telegram_id,
            username=feedback_data.username,
            first_name=feedback_data.first_name,
            last_name=feedback_data.last_name,
            rating=feedback_data.rating,
            message_text=feedback_data.message_text,
            status=FeedbackStatus.new
        )
        
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)
        
        return feedback
    
    async def add_feedback_image(
        self, 
        db: AsyncSession, 
        feedback_id: int, 
        image_data: bytes, 
        bot_id: int,
        original_filename: str = None
    ) -> FeedbackImage:
        """Add image to feedback using Azure Storage."""
        # Generate filename if not provided
        if not original_filename:
            original_filename = f"feedback_{feedback_id}_{uuid.uuid4().hex[:8]}.jpg"
        
        # Upload to Azure Storage
        storage_type, file_path = await storage_manager.upload_feedback_image(
            image_data=image_data,
            bot_id=bot_id,
            feedback_id=feedback_id,
            original_filename=original_filename
        )
        
        # Create database record
        image = FeedbackImage(
            feedback_id=feedback_id,
            file_path=file_path,
            storage_type=storage_type,
            file_size=len(image_data),
            original_filename=original_filename
        )
        
        db.add(image)
        await db.commit()
        await db.refresh(image)
        
        return image
    
    async def get_feedback_by_id(
        self, 
        db: AsyncSession, 
        feedback_id: int, 
        bot_id: int
    ) -> Optional[Feedback]:
        """Get feedback by ID with images."""
        stmt = select(Feedback).where(
            Feedback.id == feedback_id,
            Feedback.bot_id == bot_id
        ).options(selectinload(Feedback.images))
        
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_feedback_list(
        self, 
        db: AsyncSession, 
        bot_id: int,
        status: Optional[FeedbackStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Feedback]:
        """Get feedback list with pagination and filtering."""
        stmt = select(Feedback).where(Feedback.bot_id == bot_id)
        
        if status:
            stmt = stmt.where(Feedback.status == status)
        
        stmt = stmt.options(selectinload(Feedback.images))
        stmt = stmt.order_by(Feedback.created_at.desc())
        stmt = stmt.offset(skip).limit(limit)
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def update_feedback_status(
        self, 
        db: AsyncSession, 
        feedback_id: int, 
        bot_id: int,
        status: FeedbackStatus
    ) -> Optional[Feedback]:
        """Update feedback status."""
        stmt = update(Feedback).where(
            Feedback.id == feedback_id,
            Feedback.bot_id == bot_id
        ).values(status=status)
        
        await db.execute(stmt)
        await db.commit()
        
        return await self.get_feedback_by_id(db, feedback_id, bot_id)
    
    async def delete_feedback(
        self, 
        db: AsyncSession, 
        feedback_id: int, 
        bot_id: int
    ) -> bool:
        """Delete feedback and its images."""
        # Get feedback with images
        feedback = await self.get_feedback_by_id(db, feedback_id, bot_id)
        if not feedback:
            return False
        
        # Delete images from storage
        for image in feedback.images:
            await storage_manager.delete_image(image.storage_type, image.file_path)
        
        # Delete from database
        stmt = delete(Feedback).where(
            Feedback.id == feedback_id,
            Feedback.bot_id == bot_id
        )
        
        await db.execute(stmt)
        await db.commit()
        
        return True
    
    async def get_feedback_stats(
        self, 
        db: AsyncSession, 
        bot_id: int
    ) -> dict:
        """Get feedback statistics."""
        stmt = select(
            func.count(Feedback.id).label("total_count"),
            func.avg(Feedback.rating).label("avg_rating"),
            func.count(Feedback.id).filter(Feedback.status == FeedbackStatus.new).label("new_count"),
            func.count(Feedback.id).filter(Feedback.status == FeedbackStatus.read).label("read_count"),
            func.count(Feedback.id).filter(Feedback.status == FeedbackStatus.replied).label("replied_count")
        ).where(Feedback.bot_id == bot_id)
        
        result = await db.execute(stmt)
        stats = result.first()

        # Calculate rating distribution
        rating_dist_stmt = select(
            Feedback.rating, func.count(Feedback.id)
        ).where(
            Feedback.bot_id == bot_id,
            Feedback.rating.isnot(None)
        ).group_by(Feedback.rating)
        rating_result = await db.execute(rating_dist_stmt)
        rating_counts = dict(rating_result.all())
        # Ensure all ratings 1-5 are present as strings
        rating_distribution = {str(i): rating_counts.get(i, 0) for i in range(1, 6)}

        return {
            "total_count": stats.total_count or 0,
            "average_rating": float(stats.avg_rating) if stats.avg_rating else 0.0,
            "new_count": stats.new_count or 0,
            "read_count": stats.read_count or 0,
            "replied_count": stats.replied_count or 0,
            "rating_distribution": rating_distribution
        }
    
    async def get_image_accessible_url(self, image: FeedbackImage) -> str:
        """Get accessible URL for the image."""
        return await storage_manager.get_image_url(image.storage_type, image.file_path)


# Create global instance
feedback_crud = FeedbackCRUD() 