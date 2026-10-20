from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.src.models.user import User
from backend.src.auth import verify_password, hash_password

async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()

async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

async def create_user(db: AsyncSession, username: str, email: str, password: str, role: str) -> User:
    hashed = hash_password(password)
    user = User(username=username, email=email, hashed_password=hashed, role=role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
