# app/crud.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.auth.schema import User
from src.auth.models import UserCreate, UserUpdate

class UserCRUD:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(self, user_create: UserCreate) -> User:
        user = User(**user_create.dict())
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_user(self, user_id: int) -> User:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_user(self, user_id: int, user_update: UserUpdate) -> User:
        user = await self.get_user(user_id)
        if user:
            for key, value in user_update.dict(exclude_unset=True).items():
                setattr(user, key, value)
            await self.session.commit()
            await self.session.refresh(user)
            return user
        return None

    async def delete_user(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        if user:
            await self.session.delete(user)
            await self.session.commit()
            return True
        return False