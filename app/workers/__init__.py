# app/workers/__init__.py
import asyncio
import logging
from typing import List

logger = logging.getLogger(__name__)

# Global worker tasks
worker_tasks: List[asyncio.Task] = []

async def start_background_consumers():
    """Start all background consumer workers"""
    global worker_tasks
    
    try:
        logger.info("Starting background consumers...")
        
        # Import here to avoid circular imports
        from app.workers.rabbitmq_consumer import run_consumer
        from app.workers.data_processor import run_data_processor  
        from app.workers.cleanup_worker import run_cleanup_worker
        
        # Start RabbitMQ consumer
        rabbitmq_task = asyncio.create_task(
            run_consumer(),
            name="rabbitmq_consumer"
        )
        worker_tasks.append(rabbitmq_task)
        
        # Start data processor
        processor_task = asyncio.create_task(
            run_data_processor(),
            name="data_processor"
        )
        worker_tasks.append(processor_task)
        
        # Start cleanup worker
        cleanup_task = asyncio.create_task(
            run_cleanup_worker(),
            name="cleanup_worker"
        )
        worker_tasks.append(cleanup_task)
        
        logger.info(f"Started {len(worker_tasks)} background workers")
        
        # Monitor tasks
        await monitor_workers()
        
    except Exception as e:
        logger.error(f"Error starting background consumers: {e}")
        await stop_background_consumers()
        raise

async def monitor_workers():
    """Monitor background workers and restart if needed"""
    while True:
        try:
            # Check if any worker has died
            for i, task in enumerate(worker_tasks):
                if task.done():
                    task_name = task.get_name()
                    logger.warning(f"Worker {task_name} has stopped")
                    
                    # Get the exception if the task failed
                    try:
                        await task
                    except Exception as e:
                        logger.error(f"Worker {task_name} failed: {e}")
                    
                    # Restart the worker
                    await restart_worker(i, task_name)
            
            # Wait before next check
            await asyncio.sleep(30)  # Check every 30 seconds
            
        except asyncio.CancelledError:
            logger.info("Worker monitor cancelled")
            break
        except Exception as e:
            logger.error(f"Error in worker monitor: {e}")
            await asyncio.sleep(10)

async def restart_worker(index: int, task_name: str):
    """Restart a specific worker"""
    try:
        logger.info(f"Restarting worker: {task_name}")
        
        # Import here to avoid circular imports
        from app.workers.rabbitmq_consumer import run_consumer
        from app.workers.data_processor import run_data_processor
        from app.workers.cleanup_worker import run_cleanup_worker
        
        if task_name == "rabbitmq_consumer":
            new_task = asyncio.create_task(
                run_consumer(),
                name="rabbitmq_consumer"
            )
        elif task_name == "data_processor":
            new_task = asyncio.create_task(
                run_data_processor(),
                name="data_processor"
            )
        elif task_name == "cleanup_worker":
            new_task = asyncio.create_task(
                run_cleanup_worker(),
                name="cleanup_worker"
            )
        else:
            logger.error(f"Unknown worker type: {task_name}")
            return
        
        # Replace the old task with the new one
        worker_tasks[index] = new_task
        logger.info(f"Worker {task_name} restarted successfully")
        
    except Exception as e:
        logger.error(f"Failed to restart worker {task_name}: {e}")

async def stop_background_consumers():
    """Stop all background consumer workers"""
    global worker_tasks
    
    logger.info("Stopping background consumers...")
    
    # Cancel all tasks
    for task in worker_tasks:
        if not task.done():
            task.cancel()
    
    # Wait for tasks to complete
    if worker_tasks:
        try:
            await asyncio.wait_for(
                asyncio.gather(*worker_tasks, return_exceptions=True),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            logger.warning("Some workers did not stop gracefully within timeout")
    
    # Clear tasks
    worker_tasks.clear()
    logger.info("Background consumers stopped")

def get_worker_status():
    """Get status of all background workers"""
    status = {
        "total_workers": len(worker_tasks),
        "running_workers": sum(1 for task in worker_tasks if not task.done()),
        "failed_workers": sum(1 for task in worker_tasks if task.done() and task.exception()),
        "workers": []
    }
    
    for task in worker_tasks:
        worker_info = {
            "name": task.get_name(),
            "running": not task.done(),
            "cancelled": task.cancelled() if task.done() else False
        }
        
        if task.done() and task.exception():
            worker_info["error"] = str(task.exception())
        
        status["workers"].append(worker_info)
    
    return status