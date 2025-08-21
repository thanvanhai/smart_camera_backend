# app/workers/cleanup_worker.py
import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, func, and_

from app.core.database import get_db_session
from app.models.detection import Detection
from app.models.tracking import Tracking
from app.models.face_recognition import FaceRecognition
from app.config import settings

logger = logging.getLogger(__name__)

class CleanupWorker:
    def __init__(self):
        # Configuration for data retention (in days)
        self.detection_retention_days = getattr(settings, 'DETECTION_RETENTION_DAYS', 30)
        self.tracking_retention_days = getattr(settings, 'TRACKING_RETENTION_DAYS', 30)
        self.face_retention_days = getattr(settings, 'FACE_RETENTION_DAYS', 90)
        
        # Cleanup intervals
        self.cleanup_interval_hours = 6  # Run cleanup every 6 hours
        self.batch_size = 1000  # Delete records in batches
    
    async def cleanup_old_detections(self):
        """Remove old detection records"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.detection_retention_days)
            logger.info(f"Cleaning up detections older than {cutoff_date}")
            
            async with get_db_session() as db:
                # Count records to be deleted
                count_result = await db.execute(
                    select(func.count(Detection.id))
                    .where(Detection.timestamp < cutoff_date)
                )
                total_count = count_result.scalar() or 0
                
                if total_count == 0:
                    logger.info("No old detections to clean up")
                    return
                
                logger.info(f"Found {total_count} detection records to delete")
                
                deleted_count = 0
                while True:
                    # Delete in batches to avoid long-running transactions
                    result = await db.execute(
                        delete(Detection)
                        .where(Detection.timestamp < cutoff_date)
                        .limit(self.batch_size)
                    )
                    
                    batch_deleted = result.rowcount
                    if batch_deleted == 0:
                        break
                    
                    deleted_count += batch_deleted
                    await db.commit()
                    
                    logger.info(f"Deleted {deleted_count}/{total_count} detection records")
                    
                    # Small delay to prevent overwhelming the database
                    await asyncio.sleep(0.1)
                
                logger.info(f"Cleanup completed: deleted {deleted_count} detection records")
                
        except Exception as e:
            logger.error(f"Error cleaning up detections: {e}")
    
    async def cleanup_old_tracking(self):
        """Remove old tracking records"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.tracking_retention_days)
            logger.info(f"Cleaning up tracking data older than {cutoff_date}")
            
            async with get_db_session() as db:
                count_result = await db.execute(
                    select(func.count(Tracking.id))
                    .where(Tracking.timestamp < cutoff_date)
                )
                total_count = count_result.scalar() or 0
                
                if total_count == 0:
                    logger.info("No old tracking data to clean up")
                    return
                
                logger.info(f"Found {total_count} tracking records to delete")
                
                deleted_count = 0
                while True:
                    result = await db.execute(
                        delete(Tracking)
                        .where(Tracking.timestamp < cutoff_date)
                        .limit(self.batch_size)
                    )
                    
                    batch_deleted = result.rowcount
                    if batch_deleted == 0:
                        break
                    
                    deleted_count += batch_deleted
                    await db.commit()
                    
                    logger.info(f"Deleted {deleted_count}/{total_count} tracking records")
                    await asyncio.sleep(0.1)
                
                logger.info(f"Cleanup completed: deleted {deleted_count} tracking records")
                
        except Exception as e:
            logger.error(f"Error cleaning up tracking data: {e}")
    
    async def cleanup_old_face_recognitions(self):
        """Remove old face recognition records"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.face_retention_days)
            logger.info(f"Cleaning up face recognition data older than {cutoff_date}")
            
            async with get_db_session() as db:
                count_result = await db.execute(
                    select(func.count(FaceRecognition.id))
                    .where(FaceRecognition.timestamp < cutoff_date)
                )
                total_count = count_result.scalar() or 0
                
                if total_count == 0:
                    logger.info("No old face recognition data to clean up")
                    return
                
                logger.info(f"Found {total_count} face recognition records to delete")
                
                deleted_count = 0
                while True:
                    result = await db.execute(
                        delete(FaceRecognition)
                        .where(FaceRecognition.timestamp < cutoff_date)
                        .limit(self.batch_size)
                    )
                    
                    batch_deleted = result.rowcount
                    if batch_deleted == 0:
                        break
                    
                    deleted_count += batch_deleted
                    await db.commit()
                    
                    logger.info(f"Deleted {deleted_count}/{total_count} face recognition records")
                    await asyncio.sleep(0.1)
                
                logger.info(f"Cleanup completed: deleted {deleted_count} face recognition records")
                
        except Exception as e:
            logger.error(f"Error cleaning up face recognition data: {e}")
    
    async def cleanup_orphaned_records(self):
        """Remove orphaned records that reference non-existent cameras"""
        try:
            logger.info("Cleaning up orphaned records")
            
            async with get_db_session() as db:
                # Find detections with invalid camera_id
                orphaned_detections = await db.execute(
                    select(Detection.camera_id, func.count(Detection.id).label('count'))
                    .outerjoin(Camera, Detection.camera_id == Camera.camera_id)
                    .where(Camera.camera_id.is_(None))
                    .group_by(Detection.camera_id)
                )
                
                for row in orphaned_detections:
                    camera_id, count = row.camera_id, row.count
                    logger.warning(f"Found {count} orphaned detection records for camera_id: {camera_id}")
                    
                    # Delete orphaned detections
                    await db.execute(
                        delete(Detection)
                        .where(Detection.camera_id == camera_id)
                    )
                
                # Find tracking records with invalid camera_id
                orphaned_tracking = await db.execute(
                    select(Tracking.camera_id, func.count(Tracking.id).label('count'))
                    .outerjoin(Camera, Tracking.camera_id == Camera.camera_id)
                    .where(Camera.camera_id.is_(None))
                    .group_by(Tracking.camera_id)
                )
                
                for row in orphaned_tracking:
                    camera_id, count = row.camera_id, row.count
                    logger.warning(f"Found {count} orphaned tracking records for camera_id: {camera_id}")
                    
                    # Delete orphaned tracking records
                    await db.execute(
                        delete(Tracking)
                        .where(Tracking.camera_id == camera_id)
                    )
                
                await db.commit()
                logger.info("Orphaned records cleanup completed")
                
        except Exception as e:
            logger.error(f"Error cleaning up orphaned records: {e}")
    
    async def optimize_database(self):
        """Perform database optimization tasks"""
        try:
            logger.info("Starting database optimization")
            
            async with get_db_session() as db:
                # For PostgreSQL, you might want to run VACUUM ANALYZE
                # Note: This requires special privileges and should be done carefully
                
                # Update table statistics
                await db.execute("ANALYZE detections")
                await db.execute("ANALYZE tracking")
                await db.execute("ANALYZE face_recognitions")
                await db.execute("ANALYZE hourly_stats")
                await db.execute("ANALYZE daily_summaries")
                
                logger.info("Database optimization completed")
                
        except Exception as e:
            logger.error(f"Error during database optimization: {e}")
    
    async def get_database_stats(self):
        """Get database statistics for monitoring"""
        try:
            async with get_db_session() as db:
                # Count records in each table
                stats = {}
                
                # Detections count
                detection_count = await db.execute(select(func.count(Detection.id)))
                stats['detections'] = detection_count.scalar()
                
                # Tracking count
                tracking_count = await db.execute(select(func.count(Tracking.id)))
                stats['tracking'] = tracking_count.scalar()
                
                # Face recognition count
                face_count = await db.execute(select(func.count(FaceRecognition.id)))
                stats['face_recognitions'] = face_count.scalar()
                
                # Get disk usage estimates
                total_size_query = """
                    SELECT 
                        pg_total_relation_size('detections') +
                        pg_total_relation_size('tracking') +
                        pg_total_relation_size('face_recognitions') +
                        pg_total_relation_size('hourly_stats') +
                        pg_total_relation_size('daily_summaries') as total_size
                """
                size_result = await db.execute(total_size_query)
                total_size = size_result.scalar()
                stats['total_size_bytes'] = total_size
                stats['total_size_mb'] = round(total_size / 1024 / 1024, 2) if total_size else 0
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    async def run_cleanup_worker(self):
        """Main cleanup worker loop"""
        logger.info("Starting cleanup worker")
        
        last_cleanup = datetime.now()
        
        while True:
            try:
                current_time = datetime.now()
                
                # Run cleanup every cleanup_interval_hours
                time_since_last_cleanup = (current_time - last_cleanup).total_seconds() / 3600
                
                if time_since_last_cleanup >= self.cleanup_interval_hours:
                    logger.info("Starting scheduled cleanup")
                    
                    # Log database stats before cleanup
                    stats_before = await self.get_database_stats()
                    logger.info(f"Database stats before cleanup: {stats_before}")
                    
                    # Run cleanup tasks
                    await self.cleanup_old_detections()
                    await self.cleanup_old_tracking()
                    await self.cleanup_old_face_recognitions()
                    await self.cleanup_orphaned_records()
                    
                    # Optimize database
                    await self.optimize_database()
                    
                    # Log database stats after cleanup
                    stats_after = await self.get_database_stats()
                    logger.info(f"Database stats after cleanup: {stats_after}")
                    
                    last_cleanup = current_time
                    logger.info("Cleanup cycle completed")
                
                # Wait for next check (every hour)
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in cleanup worker main loop: {e}")
                await asyncio.sleep(1800)  # Wait 30 minutes before retrying

# Cleanup worker instance
cleanup_worker = CleanupWorker()

async def run_cleanup_worker():
    """Run the cleanup worker"""
    try:
        await cleanup_worker.run_cleanup_worker()
    except KeyboardInterrupt:
        logger.info("Cleanup worker interrupted by user")
    except Exception as e:
        logger.error(f"Cleanup worker error: {e}")

if __name__ == "__main__":
    asyncio.run(run_cleanup_worker())