# app/workers/data_processor.py
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db_session
from app.models.detection import Detection
from app.models.tracking import Tracking
from app.models.face_recognition import FaceRecognition
from app.models.camera import Camera
from app.services.analytics_service import AnalyticsService
from app.config import settings

logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self):
        self.analytics_service = AnalyticsService()
        self.processing_interval = 60  # Process every minute
        self.batch_size = 1000
    
    async def process_hourly_statistics(self):
        """Process and aggregate hourly statistics"""
        try:
            current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
            previous_hour = current_hour - timedelta(hours=1)
            
            logger.info(f"Processing hourly stats for: {previous_hour}")
            
            async with get_db_session() as db:
                # Get all active cameras
                cameras_result = await db.execute(
                    select(Camera).where(Camera.status == 'active')
                )
                cameras = cameras_result.scalars().all()
                
                for camera in cameras:
                    await self._process_camera_hourly_stats(db, camera.camera_id, previous_hour)
            
        except Exception as e:
            logger.error(f"Error processing hourly statistics: {e}")
    
    async def _process_camera_hourly_stats(self, db: AsyncSession, camera_id: str, hour_timestamp: datetime):
        """Process hourly statistics for a specific camera"""
        try:
            next_hour = hour_timestamp + timedelta(hours=1)
            
            # Count detections in the hour
            detection_count_result = await db.execute(
                select(func.count(Detection.id))
                .where(
                    and_(
                        Detection.camera_id == camera_id,
                        Detection.timestamp >= hour_timestamp,
                        Detection.timestamp < next_hour
                    )
                )
            )
            total_detections = detection_count_result.scalar() or 0
            
            # Count unique tracks
            unique_tracks_result = await db.execute(
                select(func.count(func.distinct(Tracking.track_id)))
                .where(
                    and_(
                        Tracking.camera_id == camera_id,
                        Tracking.timestamp >= hour_timestamp,
                        Tracking.timestamp < next_hour
                    )
                )
            )
            unique_tracks = unique_tracks_result.scalar() or 0
            
            # Average confidence
            avg_confidence_result = await db.execute(
                select(func.avg(Tracking.confidence))
                .where(
                    and_(
                        Tracking.camera_id == camera_id,
                        Tracking.timestamp >= hour_timestamp,
                        Tracking.timestamp < next_hour
                    )
                )
            )
            avg_confidence = avg_confidence_result.scalar() or 0.0
            
            # Count persons (assuming object_type = 'person')
            person_count_result = await db.execute(
                select(func.count(Tracking.id))
                .where(
                    and_(
                        Tracking.camera_id == camera_id,
                        Tracking.object_type == 'person',
                        Tracking.timestamp >= hour_timestamp,
                        Tracking.timestamp < next_hour
                    )
                )
            )
            person_count = person_count_result.scalar() or 0
            
            # Update hourly stats
            await self.analytics_service.update_hourly_stats(
                db, camera_id, hour_timestamp,
                person_count, total_detections, unique_tracks, float(avg_confidence)
            )
            
            logger.info(f"Updated hourly stats for camera {camera_id}: "
                       f"persons={person_count}, detections={total_detections}")
            
        except Exception as e:
            logger.error(f"Error processing hourly stats for camera {camera_id}: {e}")
    
    async def process_daily_summaries(self):
        """Process and aggregate daily summaries"""
        try:
            yesterday = (datetime.now() - timedelta(days=1)).date()
            logger.info(f"Processing daily summary for: {yesterday}")
            
            async with get_db_session() as db:
                cameras_result = await db.execute(
                    select(Camera).where(Camera.status == 'active')
                )
                cameras = cameras_result.scalars().all()
                
                for camera in cameras:
                    await self._process_camera_daily_summary(db, camera.camera_id, yesterday)
                    
        except Exception as e:
            logger.error(f"Error processing daily summaries: {e}")
    
    async def _process_camera_daily_summary(self, db: AsyncSession, camera_id: str, date):
        """Process daily summary for a specific camera"""
        try:
            start_of_day = datetime.combine(date, datetime.min.time())
            end_of_day = start_of_day + timedelta(days=1)
            
            # Total persons detected
            total_persons_result = await db.execute(
                select(func.count(Tracking.id))
                .where(
                    and_(
                        Tracking.camera_id == camera_id,
                        Tracking.object_type == 'person',
                        Tracking.timestamp >= start_of_day,
                        Tracking.timestamp < end_of_day
                    )
                )
            )
            total_persons = total_persons_result.scalar() or 0
            
            # Total detections
            total_detections_result = await db.execute(
                select(func.count(Detection.id))
                .where(
                    and_(
                        Detection.camera_id == camera_id,
                        Detection.timestamp >= start_of_day,
                        Detection.timestamp < end_of_day
                    )
                )
            )
            total_detections = total_detections_result.scalar() or 0
            
            # Find peak hour (hour with most detections)
            peak_hour_result = await db.execute(
                select(
                    func.extract('hour', Detection.timestamp).label('hour'),
                    func.count(Detection.id).label('count')
                )
                .where(
                    and_(
                        Detection.camera_id == camera_id,
                        Detection.timestamp >= start_of_day,
                        Detection.timestamp < end_of_day
                    )
                )
                .group_by(func.extract('hour', Detection.timestamp))
                .order_by(func.count(Detection.id).desc())
                .limit(1)
            )
            
            peak_hour_data = peak_hour_result.first()
            peak_hour = int(peak_hour_data.hour) if peak_hour_data else 0
            
            # Calculate uptime (simplified - assume 100% if we have any data)
            uptime_percentage = 100.0 if total_detections > 0 else 0.0
            
            # Update daily summary
            await self.analytics_service.update_daily_summary(
                db, camera_id, date, peak_hour,
                total_persons, total_detections, uptime_percentage
            )
            
            logger.info(f"Updated daily summary for camera {camera_id}: "
                       f"persons={total_persons}, detections={total_detections}, peak_hour={peak_hour}")
                       
        except Exception as e:
            logger.error(f"Error processing daily summary for camera {camera_id}: {e}")
    
    async def process_detection_aggregation(self):
        """Aggregate detection data for better performance"""
        try:
            logger.info("Starting detection data aggregation")
            
            async with get_db_session() as db:
                # Process recent detections that haven't been aggregated
                cutoff_time = datetime.now() - timedelta(minutes=5)
                
                detections_result = await db.execute(
                    select(Detection)
                    .where(Detection.processed_at <= cutoff_time)
                    .limit(self.batch_size)
                )
                detections = detections_result.scalars().all()
                
                if detections:
                    logger.info(f"Processing {len(detections)} detection records")
                    
                    # Group by camera and time window
                    camera_stats = {}
                    for detection in detections:
                        camera_id = detection.camera_id
                        
                        if camera_id not in camera_stats:
                            camera_stats[camera_id] = {
                                'detection_count': 0,
                                'object_count': 0,
                                'last_update': detection.timestamp
                            }
                        
                        camera_stats[camera_id]['detection_count'] += 1
                        if detection.objects:
                            camera_stats[camera_id]['object_count'] += len(detection.objects)
                        
                        if detection.timestamp > camera_stats[camera_id]['last_update']:
                            camera_stats[camera_id]['last_update'] = detection.timestamp
                    
                    # Update analytics for each camera
                    for camera_id, stats in camera_stats.items():
                        await self.analytics_service.update_detection_stats(
                            db, camera_id, stats['object_count']
                        )
                    
                    logger.info(f"Updated analytics for {len(camera_stats)} cameras")
        
        except Exception as e:
            logger.error(f"Error in detection aggregation: {e}")
    
    async def run_processor(self):
        """Main processing loop"""
        logger.info("Starting data processor")
        
        last_hourly_process = datetime.now().replace(minute=0, second=0, microsecond=0)
        last_daily_process = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        while True:
            try:
                current_time = datetime.now()
                
                # Run detection aggregation every processing interval
                await self.process_detection_aggregation()
                
                # Run hourly processing at the start of each hour
                current_hour = current_time.replace(minute=0, second=0, microsecond=0)
                if current_hour > last_hourly_process:
                    await self.process_hourly_statistics()
                    last_hourly_process = current_hour
                
                # Run daily processing once per day at midnight
                current_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
                if current_day > last_daily_process:
                    await self.process_daily_summaries()
                    last_daily_process = current_day
                
                # Wait for next processing cycle
                await asyncio.sleep(self.processing_interval)
                
            except Exception as e:
                logger.error(f"Error in data processor main loop: {e}")
                await asyncio.sleep(30)  # Wait before retrying

# Processor instance
processor = DataProcessor()

async def run_data_processor():
    """Run the data processor"""
    try:
        await processor.run_processor()
    except KeyboardInterrupt:
        logger.info("Data processor interrupted by user")
    except Exception as e:
        logger.error(f"Data processor error: {e}")

if __name__ == "__main__":
    asyncio.run(run_data_processor())