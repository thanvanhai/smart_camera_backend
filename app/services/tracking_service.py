"""
Tracking analysis service
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, distinct
import math

from ..models.tracking import Tracking, TrackingSummary
from ..models.camera import Camera
from ..schemas.tracking import (
    TrackingCreate, TrackingFilter, TrackingStats,
    TrackingPath, ActiveTrack, TrackingAlert, TrackingHeatmap
)

class TrackingService:
    """Service for tracking analysis operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_tracking(self, tracking_data: TrackingCreate) -> Tracking:
        """Create a new tracking record"""
        db_tracking = Tracking(
            camera_id=tracking_data.camera_id,
            track_id=tracking_data.track_id,
            object_class=tracking_data.object_class,
            bbox_x=tracking_data.bbox_x,
            bbox_y=tracking_data.bbox_y,
            bbox_width=tracking_data.bbox_width,
            bbox_height=tracking_data.bbox_height,
            confidence=tracking_data.confidence,
            timestamp=tracking_data.timestamp,
            frame_id=tracking_data.frame_id,
            velocity_x=tracking_data.velocity_x,
            velocity_y=tracking_data.velocity_y,
            additional_data=tracking_data.additional_data
        )
        
        self.db.add(db_tracking)
        self.db.commit()
        self.db.refresh(db_tracking)
        return db_tracking
    
    async def get_tracking(self, tracking_id: int) -> Optional[Tracking]:
        """Get tracking by ID"""
        return self.db.query(Tracking).filter(
            Tracking.id == tracking_id
        ).first()
    
    async def get_trackings(
        self,
        filters: TrackingFilter,
        skip: int = 0,
        limit: int = 100
    ) -> List[Tracking]:
        """Get tracking records with filters"""
        query = self.db.query(Tracking)
        
        if filters.camera_id:
            query = query.filter(Tracking.camera_id == filters.camera_id)
        
        if filters.track_ids:
            query = query.filter(Tracking.track_id.in_(filters.track_ids))
        
        if filters.object_classes:
            query = query.filter(Tracking.object_class.in_(filters.object_classes))
        
        if filters.min_confidence:
            query = query.filter(Tracking.confidence >= filters.min_confidence)
        
        if filters.start_time:
            query = query.filter(Tracking.timestamp >= filters.start_time)
        
        if filters.end_time:
            query = query.filter(Tracking.timestamp <= filters.end_time)
        
        return query.order_by(desc(Tracking.timestamp)).offset(skip).limit(limit).all()
    
    async def get_tracking_path(
        self,
        track_id: str,
        camera_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Optional[TrackingPath]:
        """Get complete tracking path for a track"""
        query = self.db.query(Tracking).filter(
            and_(
                Tracking.track_id == track_id,
                Tracking.camera_id == camera_id
            )
        )
        
        if start_time:
            query = query.filter(Tracking.timestamp >= start_time)
        if end_time:
            query = query.filter(Tracking.timestamp <= end_time)
        
        trackings = query.order_by(Tracking.timestamp).all()
        
        if not trackings:
            return None
        
        # Build path points
        path_points = []
        total_distance = 0.0
        prev_x, prev_y = None, None
        
        for tracking in trackings:
            center_x = tracking.bbox_x + tracking.bbox_width / 2
            center_y = tracking.bbox_y + tracking.bbox_height / 2
            
            path_points.append({
                "x": center_x,
                "y": center_y,
                "timestamp": tracking.timestamp,
                "confidence": tracking.confidence
            })
            
            # Calculate distance
            if prev_x is not None and prev_y is not None:
                distance = math.sqrt(
                    (center_x - prev_x) ** 2 + (center_y - prev_y) ** 2
                )
                total_distance += distance
            
            prev_x, prev_y = center_x, center_y
        
        # Calculate average velocity
        time_duration = (trackings[-1].timestamp - trackings[0].timestamp).total_seconds()
        avg_velocity = total_distance / time_duration if time_duration > 0 else 0.0
        
        return TrackingPath(
            track_id=track_id,
            object_class=trackings[0].object_class,
            camera_id=camera_id,
            path_points=path_points,
            start_time=trackings[0].timestamp,
            end_time=trackings[-1].timestamp,
            total_distance=total_distance,
            avg_velocity=avg_velocity
        )
    
    async def get_active_tracks(
        self,
        camera_id: Optional[int] = None,
        minutes: int = 5
    ) -> List[ActiveTrack]:
        """Get currently active tracks"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        query = self.db.query(
            Tracking.track_id,
            Tracking.camera_id,
            Tracking.object_class,
            func.min(Tracking.timestamp).label('first_seen'),
            func.max(Tracking.timestamp).label('last_seen'),
            func.count(Tracking.id).label('frame_count'),
            func.avg(Tracking.confidence).label('avg_confidence')
        ).filter(
            Tracking.timestamp >= cutoff_time
        ).group_by(
            Tracking.track_id, 
            Tracking.camera_id, 
            Tracking.object_class
        )
        
        if camera_id:
            query = query.filter(Tracking.camera_id == camera_id)
        
        active_data = query.all()
        
        active_tracks = []
        for data in active_data:
            # Get latest bbox for this track
            latest_tracking = self.db.query(Tracking).filter(
                and_(
                    Tracking.track_id == data.track_id,
                    Tracking.camera_id == data.camera_id
                )
            ).order_by(desc(Tracking.timestamp)).first()
            
            current_bbox = {
                "x": latest_tracking.bbox_x,
                "y": latest_tracking.bbox_y,
                "width": latest_tracking.bbox_width,
                "height": latest_tracking.bbox_height
            }
            
            current_velocity = None
            if latest_tracking.velocity_x is not None and latest_tracking.velocity_y is not None:
                current_velocity = {
                    "x": latest_tracking.velocity_x,
                    "y": latest_tracking.velocity_y
                }
            
            active_tracks.append(ActiveTrack(
                track_id=data.track_id,
                camera_id=data.camera_id,
                object_class=data.object_class,
                current_bbox=current_bbox,
                confidence=float(data.avg_confidence),
                first_seen=data.first_seen,
                last_seen=data.last_seen,
                frame_count=data.frame_count,
                current_velocity=current_velocity
            ))
        
        return active_tracks
    
    async def get_tracking_stats(
        self,
        camera_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> TrackingStats:
        """Get tracking statistics"""
        query = self.db.query(Tracking)
        
        if camera_id:
            query = query.filter(Tracking.camera_id == camera_id)
        if start_time:
            query = query.filter(Tracking.timestamp >= start_time)
        if end_time:
            query = query.filter(Tracking.timestamp <= end_time)
        
        # Total unique tracks
        total_tracks = query.with_entities(
            func.count(distinct(Tracking.track_id))
        ).scalar() or 0
        
        # Active tracks (last 5 minutes)
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        active_tracks = query.filter(
            Tracking.timestamp >= cutoff_time
        ).with_entities(
            func.count(distinct(Tracking.track_id))
        ).scalar() or 0
        
        # Tracks by class
        class_stats = query.with_entities(
            Tracking.object_class,
            func.count(distinct(Tracking.track_id))
        ).group_by(Tracking.object_class).all()
        
        tracks_by_class = {class_name: count for class_name, count in class_stats}
        
        # Track duration statistics
        track_durations = self.db.query(
            (func.max(Tracking.timestamp) - func.min(Tracking.timestamp)).label('duration')
        ).filter(
            Tracking.camera_id == camera_id if camera_id else True
        ).group_by(Tracking.track_id).all()
        
        durations_seconds = [
            d.duration.total_seconds() for d in track_durations if d.duration
        ]
        
        avg_track_duration = (
            sum(durations_seconds) / len(durations_seconds) 
            if durations_seconds else 0.0
        )
        longest_track_duration = max(durations_seconds) if durations_seconds else 0.0
        
        # Total distance calculation (simplified)
        total_distance_traveled = 0.0  # Would need more complex calculation
        
        # Tracks by camera
        camera_stats = self.db.query(
            Tracking.camera_id,
            Camera.name,
            func.count(distinct(Tracking.track_id))
        ).join(Camera).group_by(
            Tracking.camera_id, Camera.name
        ).all()
        
        tracks_by_camera = [
            {
                "camera_id": camera_id,
                "camera_name": camera_name,
                "track_count": count
            }
            for camera_id, camera_name, count in camera_stats
        ]
        
        return TrackingStats(
            total_tracks=total_tracks,
            active_tracks=active_tracks,
            tracks_by_class=tracks_by_class,
            avg_track_duration=avg_track_duration,
            longest_track_duration=longest_track_duration,
            total_distance_traveled=total_distance_traveled,
            tracks_by_camera=tracks_by_camera
        )
    
    async def detect_loitering(
        self,
        camera_id: int,
        min_duration_minutes: int = 10,
        area_threshold: float = 0.1
    ) -> List[TrackingAlert]:
        """Detect loitering behavior"""
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        
        # Get tracks that have been active for minimum duration
        potential_loiterers = self.db.query(
            Tracking.track_id,
            func.min(Tracking.timestamp).label('first_seen'),
            func.max(Tracking.timestamp).label('last_seen'),
            Tracking.object_class
        ).filter(
            and_(
                Tracking.camera_id == camera_id,
                Tracking.timestamp >= cutoff_time
            )
        ).group_by(
            Tracking.track_id, Tracking.object_class
        ).having(
            (func.max(Tracking.timestamp) - func.min(Tracking.timestamp)) >= 
            timedelta(minutes=min_duration_minutes)
        ).all()
        
        alerts = []
        for track_data in potential_loiterers:
            # Calculate movement area for this track
            track_positions = self.db.query(
                Tracking.bbox_x, Tracking.bbox_y
            ).filter(
                and_(
                    Tracking.track_id == track_data.track_id,
                    Tracking.camera_id == camera_id
                )
            ).all()
            
            if len(track_positions) < 2:
                continue
            
            # Calculate bounding area of movement
            x_coords = [pos.bbox_x for pos in track_positions]
            y_coords = [pos.bbox_y for pos in track_positions]
            
            movement_area = (
                (max(x_coords) - min(x_coords)) * 
                (max(y_coords) - min(y_coords))
            )
            
            if movement_area <= area_threshold:
                duration = (track_data.last_seen - track_data.first_seen).total_seconds() / 60
                
                alerts.append(TrackingAlert(
                    track_id=track_data.track_id,
                    camera_id=camera_id,
                    alert_type="loitering",
                    object_class=track_data.object_class,
                    duration=duration,
                    severity="medium" if duration < 20 else "high",
                    message=f"Object loitering detected for {duration:.1f} minutes",
                    metadata={
                        "movement_area": movement_area,
                        "first_seen": track_data.first_seen.isoformat(),
                        "last_seen": track_data.last_seen.isoformat()
                    },
                    timestamp=datetime.utcnow()
                ))
        
        return alerts
    
    async def generate_movement_heatmap(
        self,
        camera_id: int,
        object_class: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        width: int = 100,
        height: int = 100
    ) -> Optional[TrackingHeatmap]:
        """Generate movement heatmap"""
        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.utcnow()
        
        query = self.db.query(Tracking).filter(
            and_(
                Tracking.camera_id == camera_id,
                Tracking.timestamp >= start_time,
                Tracking.timestamp <= end_time
            )
        )
        
        if object_class:
            query = query.filter(Tracking.object_class == object_class)
        
        trackings = query.all()
        
        if not trackings:
            return None
        
        # Initialize heatmap
        heatmap_data = [[0 for _ in range(width)] for _ in range(height)]
        
        # Populate heatmap with tracking centers
        for tracking in trackings:
            center_x = int((tracking.bbox_x + tracking.bbox_width / 2) * width)
            center_y = int((tracking.bbox_y + tracking.bbox_height / 2) * height)
            
            center_x = max(0, min(width - 1, center_x))
            center_y = max(0, min(height - 1, center_y))
            
            heatmap_data[center_y][center_x] += 1
        
        max_intensity = max(max(row) for row in heatmap_data)
        
        return TrackingHeatmap(
            camera_id=camera_id,
            object_class=object_class,
            time_range={
                "start_time": start_time,
                "end_time": end_time
            },
            heatmap_data=heatmap_data,
            width=width,
            height=height,
            max_intensity=max_intensity,
            generated_at=datetime.utcnow()
        )
    
    async def create_tracking_summary(
        self,
        track_id: str,
        camera_id: int
    ) -> Optional[TrackingSummary]:
        """Create tracking summary for a completed track"""
        trackings = self.db.query(Tracking).filter(
            and_(
                Tracking.track_id == track_id,
                Tracking.camera_id == camera_id
            )
        ).order_by(Tracking.timestamp).all()
        
        if not trackings:
            return None
        
        first_seen = trackings[0].timestamp
        last_seen = trackings[-1].timestamp
        total_frames = len(trackings)
        avg_confidence = sum(t.confidence for t in trackings) / total_frames
        
        # Calculate path length
        path_length = 0.0
        max_velocity = 0.0
        
        for i in range(1, len(trackings)):
            prev = trackings[i-1]
            curr = trackings[i]
            
            # Distance between centers
            prev_center_x = prev.bbox_x + prev.bbox_width / 2
            prev_center_y = prev.bbox_y + prev.bbox_height / 2
            curr_center_x = curr.bbox_x + curr.bbox_width / 2
            curr_center_y = curr.bbox_y + curr.bbox_height / 2
            
            distance = math.sqrt(
                (curr_center_x - prev_center_x) ** 2 + 
                (curr_center_y - prev_center_y) ** 2
            )
            path_length += distance
            
            # Calculate velocity
            time_diff = (curr.timestamp - prev.timestamp).total_seconds()
            if time_diff > 0:
                velocity = distance / time_diff
                max_velocity = max(max_velocity, velocity)
        
        # Check if summary already exists
        existing_summary = self.db.query(TrackingSummary).filter(
            and_(
                TrackingSummary.track_id == track_id,
                TrackingSummary.camera_id == camera_id
            )
        ).first()
        
        if existing_summary:
            # Update existing
            existing_summary.last_seen = last_seen
            existing_summary.total_frames = total_frames
            existing_summary.avg_confidence = avg_confidence
            existing_summary.path_length = path_length
            existing_summary.max_velocity = max_velocity
            existing_summary.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(existing_summary)
            return existing_summary
        else:
            # Create new summary
            summary = TrackingSummary(
                camera_id=camera_id,
                track_id=track_id,
                object_class=trackings[0].object_class,
                first_seen=first_seen,
                last_seen=last_seen,
                total_frames=total_frames,
                avg_confidence=avg_confidence,
                path_length=path_length,
                max_velocity=max_velocity,
                summary_date=first_seen.date()
            )
            
            self.db.add(summary)
            self.db.commit()
            self.db.refresh(summary)
            return summary
    
    async def cleanup_old_tracking_data(self, days: int = 7) -> int:
        """Clean up old tracking records"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted_count = self.db.query(Tracking).filter(
            Tracking.created_at < cutoff_date
        ).count()
        
        self.db.query(Tracking).filter(
            Tracking.created_at < cutoff_date
        ).delete()
        
        self.db.commit()
        return deleted_count