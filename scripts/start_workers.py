# scripts/start_workers.py
"""
Script to start background workers independently from the main FastAPI application.
Useful for distributed deployment where workers run on separate containers/servers.
"""
import asyncio
import sys
import os
import signal
import logging
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.core.database import init_database
from app.core.rabbitmq import init_rabbitmq
from app.workers import start_background_consumers, stop_background_consumers

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WorkerManager:
    def __init__(self):
        self.running = False
        self.shutdown_event = asyncio.Event()
    
    async def startup(self):
        """Initialize services before starting workers"""
        try:
            logger.info("Initializing services for workers...")
            
            # Initialize database
            await init_database()
            logger.info("Database initialized")
            
            # Initialize RabbitMQ
            await init_rabbitmq()
            logger.info("RabbitMQ initialized")
            
            logger.info("Services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise
    
    async def run_workers(self):
        """Run all background workers"""
        try:
            self.running = True
            logger.info("Starting background workers...")
            
            # Start workers
            workers_task = asyncio.create_task(start_background_consumers())
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            logger.info("Shutdown signal received, stopping workers...")
            workers_task.cancel()
            
            try:
                await workers_task
            except asyncio.CancelledError:
                pass
            
            await stop_background_consumers()
            
        except Exception as e:
            logger.error(f"Error running workers: {e}")
        finally:
            self.running = False
            logger.info("Workers stopped")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown_event.set()

async def main():
    """Main function to run workers"""
    manager = WorkerManager()
    
    # Setup signal handlers
    for sig in [signal.SIGTERM, signal.SIGINT]:
        signal.signal(sig, manager.signal_handler)
    
    try:
        # Initialize services
        await manager.startup()
        
        # Run workers
        await manager.run_workers()
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Worker manager error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)