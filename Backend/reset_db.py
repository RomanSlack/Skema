#!/usr/bin/env python3
"""
Script to reset the database schema
"""
import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reset_database():
    """Reset the database by dropping and recreating all tables"""
    
    # Create engine
    engine = create_async_engine(
        settings.database_url,
        echo=True,
    )
    
    try:
        # Import all models to ensure they are registered
        from app.models import (
            User, UserSession, Board, Card, 
            CalendarEvent, JournalEntry, AICommand, AuditLog
        )
        
        logger.info("Dropping all tables...")
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
        
        logger.info("Creating all tables...")
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        
        logger.info("Database reset completed successfully!")
        
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_database())