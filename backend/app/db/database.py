import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Default to SQLite for local development if Postgres is not provided
# For SQLite with async, we use sqlite+aiosqlite
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./utservio.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
