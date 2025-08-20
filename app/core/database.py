from typing import AsyncGenerator
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool
from sqlalchemy import MetaData

from app.config import settings

logger = structlog.get_logger(__name__)

# Database metadata with naming convention for constraints
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
)

# Base class for all database models
Base = declarative_base(metadata=metadata)


class DatabaseManager:
    """Database manager for handling connections and sessions."""
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self._initialized = False
    
    def initialize(self):
        """Initialize database engine and session factory."""
        if self._initialized:
            return
        
        logger.info("Initializing database connection", url=settings.database_url)
        
        # Create async engine  # ⚡ Async engine KHÔNG dùng pool_size/max_overflow
        self.engine = create_async_engine(
            settings.database_url,
            echo=settings.database_echo,
            # pool_size=settings.database_pool_size,
            # max_overflow=settings.database_max_overflow,
            poolclass=NullPool if settings.is_development else None,
            future=True,
            pool_pre_ping=True,   # tránh connection chết
        )
        
        
        # Create session factory
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        self._initialized = True
        logger.info("Database initialized successfully")
    
    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session."""
        if not self._initialized:
            self.initialize()
        
        async with self.session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error("Database session error", error=str(e))
                raise
            finally:
                await session.close()
    
    async def health_check(self) -> bool:
        """Check database health."""
        try:
            async with self.session_factory() as session:
                await session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False


# Global database manager instance
db_manager = DatabaseManager()


# Dependency for getting database session
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting database session."""
    async for session in db_manager.get_session():
        yield session


# Database event handlers
async def init_database():
    """Initialize database on application startup."""
    try:
        db_manager.initialize()
        logger.info("Database startup completed")
    except Exception as e:
        logger.error("Database startup failed", error=str(e))
        raise


async def close_database():
    """Close database on application shutdown."""
    try:
        await db_manager.close()
        logger.info("Database shutdown completed")
    except Exception as e:
        logger.error("Database shutdown failed", error=str(e))


# Utility functions for database operations
async def create_tables():
    """Create all database tables."""
    if not db_manager._initialized:
        db_manager.initialize()
    
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("All database tables created")


async def drop_tables():
    """Drop all database tables (use with caution!)."""
    if not db_manager._initialized:
        db_manager.initialize()
    
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    logger.info("All database tables dropped")


# Transaction helper
class DatabaseTransaction:
    """Context manager for database transactions."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._in_transaction = False
    
    async def __aenter__(self):
        if not self._in_transaction:
            await self.session.begin()
            self._in_transaction = True
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._in_transaction:
            if exc_type is not None:
                await self.session.rollback()
                logger.error("Transaction rolled back", error=str(exc_val))
            else:
                await self.session.commit()
                logger.debug("Transaction committed successfully")
            self._in_transaction = False


def with_transaction(session: AsyncSession) -> DatabaseTransaction:
    """Create a transaction context manager."""
    return DatabaseTransaction(session)