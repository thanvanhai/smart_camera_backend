"""
Detection processing service
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc, and_, extract

from ..models.detection import Detection, DetectionSummary
from ..models.camera import Camera
from ..schemas.detection import (
    DetectionCreate, DetectionFilter, DetectionStats,
    HourlyDetectionStats, DetectionHeatmap, DetectionAlert,
    BulkDetectionCreate
)

class DetectionService:
    """Service for detection processing operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_detection(self, detection_data: DetectionCreate) -> Detection:
        """Create a new detection record"""
        db_detection = Detection(
            camera_id=detection_data.camera_id,
            class_name=detection_data.class_name,
            confidence=detection_data.confidence,
            bbox_x=detection_data.bbox.x,
            bbox_y=detection_data.bbox.y,
            bbox_width=detection_data.bbox.width,
            bbox_height=detection_data.bbox.height,
            timestamp=detection_data.timestamp,
            frame_id=detection_data.frame_id,
            additional_data=detection_data.additional_data
        )
        
        self.db.add(db_detection)
        await  self.db.commit()
        await  self.db.refresh(db_detection)
        return db_detection
    
    async def create_bulk_detections(
        self, 
        bulk_data: BulkDetectionCreate
    ) -> List[Detection]:
        """Create multiple detections efficiently"""
        detections = []
        
        for detection_data in bulk_data.detections:
            db_detection = Detection(
                camera_id=detection_data.camera_id,
                class_name=detection_data.class_name,
                confidence=detection_data.confidence,
                bbox_x=detection_data.bbox.x,
                bbox_y=detection_data.bbox.y,
                bbox_width=detection_data.bbox.width,
                bbox_height=detection_data.bbox.height,
                timestamp=detection_data.timestamp,
                frame_id=detection_data.frame_id,
                additional_data=detection_data.additional_data
            )
            detections.append(db_detection)
        
        self.db.add_all(detections)
        await  self.db.commit()
        
        # Refresh all objects
        for detection in detections:
            await  self.db.refresh(detection)
        
        return detections
    
    async def get_detection(self, detection_id: int) -> Optional[Detection]:
        """Get detection by ID"""
        # Sửa từ sync query sang async
        result = await self.db.execute(
            select(Detection).filter(Detection.id == detection_id)
        )
        return result.scalar_one_or_none()
    
    async def get_detections(
        self,
        filters: DetectionFilter,
        skip: int = 0,
        limit: int = 100
    ) -> List[Detection]:
        """Get detections with filters"""
        # Sửa từ sync query sang async
        query = select(Detection)
        
        if filters.camera_id:
            query = query.filter(Detection.camera_id == filters.camera_id)
        
        if filters.class_names:
            query = query.filter(Detection.class_name.in_(filters.class_names))
        
        if filters.min_confidence:
            query = query.filter(Detection.confidence >= filters.min_confidence)
        
        if filters.max_confidence:
            query = query.filter(Detection.confidence <= filters.max_confidence)
        
        if filters.start_time:
            query = query.filter(Detection.timestamp >= filters.start_time)
        
        if filters.end_time:
            query = query.filter(Detection.timestamp <= filters.end_time)
        
        return query.order_by(desc(Detection.timestamp)).offset(skip).limit(limit).all()
    
    async def get_detection_stats(
        self,
        camera_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> DetectionStats:
        """Get detection statistics"""
        query = self.db.query(Detection)
        
        if camera_id:
            query = query.filter(Detection.camera_id == camera_id)
        
        if start_time:
            query = query.filter(Detection.timestamp >= start_time)
        
        if end_time:
            query = query.filter(Detection.timestamp <= end_time)
        
        # Total detections
        total_detections = query.count()
        
        # Detections by class
        class_stats = query.with_entities(
            Detection.class_name,
            func.count(Detection.id)
        ).group_by(Detection.class_name).all()
        
        detections_by_class = {class_name: count for class_name, count in class_stats}
        
        # Detections by hour
        hour_stats = query.with_entities(
            extract('hour', Detection.timestamp).label('hour'),
            func.count(Detection.id)
        ).group_by('hour').all()
        
        detections_by_hour = {str(int(hour)): count for hour, count in hour_stats}
        
        # Average confidence
        avg_confidence = query.with_entities(
            func.avg(Detection.confidence)
        ).scalar() or 0.0
        
        # Confidence distribution
        confidence_ranges = [
            ('0.0-0.2', 0.0, 0.2),
            ('0.2-0.4', 0.2, 0.4),
            ('0.4-0.6', 0.4, 0.6),
            ('0.6-0.8', 0.6, 0.8),
            ('0.8-1.0', 0.8, 1.0)
        ]
        
        confidence_distribution = {}
        for label, min_conf, max_conf in confidence_ranges:
            count = query.filter(
                and_(
                    Detection.confidence >= min_conf,
                    Detection.confidence < max_conf if max_conf < 1.0 
                    else Detection.confidence <= max_conf
                )
            ).count()
            confidence_distribution[label] = count
        
        # Top cameras
        camera_stats = self.db.query(
            Detection.camera_id,
            Camera.name,
            func.count(Detection.id).label('count')
        ).join(Camera).group_by(
            Detection.camera_id, Camera.name
        ).order_by(desc('count')).limit(10).all()
        
        top_cameras = [
            {
                "camera_id": camera_id,
                "camera_name": camera_name,
                "count": count
            }
            for camera_id, camera_name, count in camera_stats
        ]
        
        return DetectionStats(
            total_detections=total_detections,
            detections_by_class=detections_by_class,
            detections_by_hour=detections_by_hour,
            avg_confidence=float(avg_confidence),
            confidence_distribution=confidence_distribution,
            top_cameras=top_cameras
        )
    
    async def get_hourly_stats(
        self,
        camera_id: Optional[int] = None,
        date: Optional[datetime] = None
    ) -> List[HourlyDetectionStats]:
        """Get hourly detection statistics"""
        if not date:
            date = datetime.utcnow().date()
        
        start_time = datetime.combine(date, datetime.min.time())
        end_time = start_time + timedelta(days=1)
        
        query = self.db.query(Detection).filter(
            and_(
                Detection.timestamp >= start_time,
                Detection.timestamp < end_time
            )
        )
        
        if camera_id:
            query = query.filter(Detection.camera_id == camera_id)
        
        # Group by hour
        hourly_data = query.with_entities(
            extract('hour', Detection.timestamp).label('hour'),
            func.count(Detection.id).label('count'),
            func.avg(Detection.confidence).label('avg_conf')
        ).group_by('hour').all()
        
        # Get top classes for each hour
        hourly_stats = []
        for hour, count, avg_conf in hourly_data:
            # Get top classes for this hour
            hour_start = start_time + timedelta(hours=int(hour))
            hour_end = hour_start + timedelta(hours=1)
            
            class_query = query.filter(
                and_(
                    Detection.timestamp >= hour_start,
                    Detection.timestamp < hour_end
                )
            ).with_entities(
                Detection.class_name,
                func.count(Detection.id)
            ).group_by(Detection.class_name).order_by(
                desc(func.count(Detection.id))
            ).limit(5).all()
            
            top_classes = [
                {"class_name": class_name, "count": class_count}
                for class_name, class_count in class_query
            ]
            
            hourly_stats.append(HourlyDetectionStats(
                hour=int(hour),
                detection_count=count,
                avg_confidence=float(avg_conf or 0.0),
                top_classes=top_classes
            ))
        
        return sorted(hourly_stats, key=lambda x: x.hour)
    
    async def generate_detection_heatmap(
        self,
        camera_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        width: int = 100,
        height: int = 100
    ) -> Optional[DetectionHeatmap]:
        """Generate detection heatmap for a camera"""
        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.utcnow()
        
        # Get detections for the time range
        detections = self.db.query(Detection).filter(
            and_(
                Detection.camera_id == camera_id,
                Detection.timestamp >= start_time,
                Detection.timestamp <= end_time
            )
        ).all()
        
        if not detections:
            return None
        
        # Initialize heatmap grid
        heatmap_data = [[0 for _ in range(width)] for _ in range(height)]
        
        # Populate heatmap with detection centers
        for detection in detections:
            # Convert normalized coordinates to grid coordinates
            center_x = int((detection.bbox_x + detection.bbox_width / 2) * width)
            center_y = int((detection.bbox_y + detection.bbox_height / 2) * height)
            
            # Ensure coordinates are within bounds
            center_x = max(0, min(width - 1, center_x))
            center_y = max(0, min(height - 1, center_y))
            
            # Increment heatmap value with confidence weighting
            heatmap_data[center_y][center_x] += int(detection.confidence * 100)
        
        # Find max value for normalization
        max_value = max(max(row) for row in heatmap_data)
        
        return DetectionHeatmap(
            camera_id=camera_id,
            width=width,
            height=height,
            heatmap_data=heatmap_data,
            max_value=max_value,
            generated_at=datetime.utcnow()
        )
    
    async def cleanup_old_detections(self, days: int = 30) -> int:
        """Clean up old detection records"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted_count = self.db.query(Detection).filter(
            Detection.created_at < cutoff_date
        ).count()
        
        self.db.query(Detection).filter(
            Detection.created_at < cutoff_date
        ).delete()
        
        await  self.db.commit()
        return deleted_count
    
    async def get_recent_detections(
        self,
        camera_id: Optional[int] = None,
        minutes: int = 5,
        limit: int = 50
    ) -> List[Detection]:
        """Get recent detections"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        query = self.db.query(Detection).filter(
            Detection.timestamp >= cutoff_time
        )
        
        if camera_id:
            query = query.filter(Detection.camera_id == camera_id)
        
        return query.order_by(desc(Detection.timestamp)).limit(limit).all()
    
    async def create_daily_summary(
        self, 
        camera_id: int, 
        summary_date: datetime
    ) -> DetectionSummary:
        """Create daily detection summary"""
        start_date = datetime.combine(summary_date.date(), datetime.min.time())
        end_date = start_date + timedelta(days=1)
        
        # Get detections for the day
        detections = self.db.query(Detection).filter(
            and_(
                Detection.camera_id == camera_id,
                Detection.timestamp >= start_date,
                Detection.timestamp < end_date
            )
        ).all()
        
        if not detections:
            return DetectionSummary(
                camera_id=camera_id,
                summary_date=summary_date,
                total_detections=0,
                detections_by_class={},
                avg_confidence=0.0,
                peak_hour=None,
                peak_detections=0
            )
        
        # Calculate statistics
        total_detections = len(detections)
        
        # Group by class
        detections_by_class = {}
        for detection in detections:
            detections_by_class[detection.class_name] = (
                detections_by_class.get(detection.class_name, 0) + 1
            )
        
        # Average confidence
        avg_confidence = sum(d.confidence for d in detections) / total_detections
        
        # Peak hour analysis
        hourly_counts = {}
        for detection in detections:
            hour = detection.timestamp.hour
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
        
        peak_hour = max(hourly_counts.keys(), key=lambda h: hourly_counts[h]) if hourly_counts else None
        peak_detections = max(hourly_counts.values()) if hourly_counts else 0
        
        # Check if summary already exists
        existing_summary = self.db.query(DetectionSummary).filter(
            and_(
                DetectionSummary.camera_id == camera_id,
                DetectionSummary.summary_date == summary_date.date()
            )
        ).first()
        
        if existing_summary:
            # Update existing summary
            existing_summary.total_detections = total_detections
            existing_summary.detections_by_class = detections_by_class
            existing_summary.avg_confidence = avg_confidence
            existing_summary.peak_hour = peak_hour
            existing_summary.peak_detections = peak_detections
            existing_summary.updated_at = datetime.utcnow()
            
            await  self.db.commit()
            await self.db.refresh(existing_summary)
            return existing_summary
        else:
            # Create new summary
            summary = DetectionSummary(
                camera_id=camera_id,
                summary_date=summary_date.date(),
                total_detections=total_detections,
                detections_by_class=detections_by_class,
                avg_confidence=avg_confidence,
                peak_hour=peak_hour,
                peak_detections=peak_detections
            )
            
            self.db.add(summary)
            await  self.db.commit()
            await  self.db.refresh(summary)
            return summary