"""
Analytics and statistics service
"""

from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, extract, case

from ..models.camera import Camera
from ..models.detection import Detection, DetectionSummary
from ..models.tracking import Tracking, TrackingSummary
from ..models.face_recognition import FaceRecognition, KnownPerson

class AnalyticsService:
    """Service for analytics and statistics operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_dashboard_stats(
        self,
        camera_ids: Optional[List[int]] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get dashboard statistics for the last N hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Base queries with optional camera filtering
        detection_query = self.db.query(Detection).filter(
            Detection.timestamp >= cutoff_time
        )
        tracking_query = self.db.query(Tracking).filter(
            Tracking.timestamp >= cutoff_time
        )
        face_query = self.db.query(FaceRecognition).filter(
            FaceRecognition.timestamp >= cutoff_time
        )
        
        if camera_ids:
            detection_query = detection_query.filter(Detection.camera_id.in_(camera_ids))
            tracking_query = tracking_query.filter(Tracking.camera_id.in_(camera_ids))
            face_query = face_query.filter(FaceRecognition.camera_id.in_(camera_ids))
        
        # Detection statistics
        total_detections = detection_query.count()
        unique_classes = detection_query.with_entities(
            func.count(Detection.class_name.distinct())
        ).scalar() or 0
        
        # Tracking statistics
        total_tracks = tracking_query.with_entities(
            func.count(Tracking.track_id.distinct())
        ).scalar() or 0
        
        # Face recognition statistics
        total_faces = face_query.count()
        known_faces = face_query.filter(
            FaceRecognition.known_person_id.isnot(None)
        ).count()
        unknown_faces = total_faces - known_faces
        
        # Camera statistics
        total_cameras = self.db.query(func.count(Camera.id)).scalar() or 0
        active_cameras = self.db.query(func.count(Camera.id)).filter(
            Camera.status == 'active'
        ).scalar() or 0
        
        # Recent activity (last hour)
        recent_cutoff = datetime.utcnow() - timedelta(hours=1)
        recent_detections = detection_query.filter(
            Detection.timestamp >= recent_cutoff
        ).count()
        recent_tracks = tracking_query.filter(
            Tracking.timestamp >= recent_cutoff
        ).with_entities(func.count(Tracking.track_id.distinct())).scalar() or 0
        
        return {
            "overview": {
                "total_detections": total_detections,
                "total_tracks": total_tracks,
                "total_faces": total_faces,
                "known_faces": known_faces,
                "unknown_faces": unknown_faces,
                "unique_object_classes": unique_classes,
                "total_cameras": total_cameras,
                "active_cameras": active_cameras
            },
            "recent_activity": {
                "detections_last_hour": recent_detections,
                "tracks_last_hour": recent_tracks,
                "activity_rate": recent_detections / max(1, hours)  # per hour
            },
            "time_range": {
                "start_time": cutoff_time,
                "end_time": datetime.utcnow(),
                "duration_hours": hours
            }
        }
    
    async def get_hourly_trends(
        self,
        camera_ids: Optional[List[int]] = None,
        days: int = 7
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get hourly trends for the last N days"""
        start_time = datetime.utcnow() - timedelta(days=days)
        
        # Detection trends by hour
        detection_query = self.db.query(
            extract('hour', Detection.timestamp).label('hour'),
            func.count(Detection.id).label('count'),
            func.avg(Detection.confidence).label('avg_confidence')
        ).filter(Detection.timestamp >= start_time)
        
        if camera_ids:
            detection_query = detection_query.filter(Detection.camera_id.in_(camera_ids))
        
        detection_trends = detection_query.group_by('hour').all()
        
        # Tracking trends by hour
        tracking_query = self.db.query(
            extract('hour', Tracking.timestamp).label('hour'),
            func.count(Tracking.track_id.distinct()).label('count')
        ).filter(Tracking.timestamp >= start_time)
        
        if camera_ids:
            tracking_query = tracking_query.filter(Tracking.camera_id.in_(camera_ids))
        
        tracking_trends = tracking_query.group_by('hour').all()
        
        # Face recognition trends by hour
        face_query = self.db.query(
            extract('hour', FaceRecognition.timestamp).label('hour'),
            func.count(FaceRecognition.id).label('count'),
            func.sum(case(
                (FaceRecognition.known_person_id.isnot(None), 1),
                else_=0
            )).label('known_faces')
        ).filter(FaceRecognition.timestamp >= start_time)
        
        if camera_ids:
            face_query = face_query.filter(FaceRecognition.camera_id.in_(camera_ids))
        
        face_trends = face_query.group_by('hour').all()
        
        # Format results
        detection_hourly = [
            {
                "hour": int(hour),
                "detections": count,
                "avg_confidence": float(avg_conf or 0)
            }
            for hour, count, avg_conf in detection_trends
        ]
        
        tracking_hourly = [
            {
                "hour": int(hour),
                "tracks": count
            }
            for hour, count in tracking_trends
        ]
        
        face_hourly = [
            {
                "hour": int(hour),
                "total_faces": count,
                "known_faces": known_count or 0,
                "unknown_faces": count - (known_count or 0)
            }
            for hour, count, known_count in face_trends
        ]
        
        return {
            "detections": detection_hourly,
            "tracking": tracking_hourly,
            "faces": face_hourly
        }
    
    async def get_object_class_analytics(
        self,
        camera_ids: Optional[List[int]] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get object class analytics"""
        start_time = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(
            Detection.class_name,
            func.count(Detection.id).label('detection_count'),
            func.count(Tracking.track_id.distinct()).label('track_count'),
            func.avg(Detection.confidence).label('avg_confidence'),
            func.min(Detection.confidence).label('min_confidence'),
            func.max(Detection.confidence).label('max_confidence')
        ).outerjoin(
            Tracking,
            and_(
                Detection.camera_id == Tracking.camera_id,
                Detection.class_name == Tracking.object_class,
                func.abs(
                    extract('epoch', Detection.timestamp - Tracking.timestamp)
                ) < 1  # Within 1 second
            )
        ).filter(Detection.timestamp >= start_time)
        
        if camera_ids:
            query = query.filter(Detection.camera_id.in_(camera_ids))
        
        results = query.group_by(Detection.class_name).order_by(
            desc('detection_count')
        ).all()
        
        analytics = []
        for result in results:
            analytics.append({
                "class_name": result.class_name,
                "detection_count": result.detection_count,
                "track_count": result.track_count or 0,
                "avg_confidence": float(result.avg_confidence or 0),
                "min_confidence": float(result.min_confidence or 0),
                "max_confidence": float(result.max_confidence or 0),
                "tracking_rate": (
                    (result.track_count or 0) / max(result.detection_count, 1) * 100
                )
            })
        
        return analytics
    
    async def get_camera_performance(
        self,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get camera performance analytics"""
        start_time = datetime.utcnow() - timedelta(days=days)
        
        # Get camera stats with activity metrics
        camera_stats = self.db.query(
            Camera.id,
            Camera.name,
            Camera.status,
            func.count(Detection.id).label('detection_count'),
            func.count(Tracking.track_id.distinct()).label('track_count'),
            func.count(FaceRecognition.id).label('face_count'),
            func.avg(Detection.confidence).label('avg_confidence')
        ).outerjoin(Detection, and_(
            Camera.id == Detection.camera_id,
            Detection.timestamp >= start_time
        )).outerjoin(Tracking, and_(
            Camera.id == Tracking.camera_id,
            Tracking.timestamp >= start_time
        )).outerjoin(FaceRecognition, and_(
            Camera.id == FaceRecognition.camera_id,
            FaceRecognition.timestamp >= start_time
        )).group_by(
            Camera.id, Camera.name, Camera.status
        ).all()
        
        performance_data = []
        for stats in camera_stats:
            # Calculate uptime percentage (simplified)
            uptime_percentage = 100.0 if stats.status == 'active' else 0.0
            
            # Calculate activity score
            total_activity = (stats.detection_count or 0) + (stats.track_count or 0) + (stats.face_count or 0)
            activity_score = min(100, total_activity / 10)  # Normalize to 0-100
            
            performance_data.append({
                "camera_id": stats.id,
                "camera_name": stats.name,
                "status": stats.status,
                "detection_count": stats.detection_count or 0,
                "track_count": stats.track_count or 0,
                "face_count": stats.face_count or 0,
                "avg_confidence": float(stats.avg_confidence or 0),
                "uptime_percentage": uptime_percentage,
                "activity_score": activity_score,
                "total_events": total_activity
            })
        
        return sorted(performance_data, key=lambda x: x['total_events'], reverse=True)
    
    async def get_security_insights(
        self,
        camera_ids: Optional[List[int]] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get security-focused insights"""
        start_time = datetime.utcnow() - timedelta(days=days)
        
        # Face recognition insights
        face_query = self.db.query(FaceRecognition).filter(
            FaceRecognition.timestamp >= start_time
        )
        if camera_ids:
            face_query = face_query.filter(FaceRecognition.camera_id.in_(camera_ids))
        
        total_face_detections = face_query.count()
        known_person_detections = face_query.filter(
            FaceRecognition.known_person_id.isnot(None)
        ).count()
        
        # Most frequently detected known persons
        frequent_persons = self.db.query(
            KnownPerson.id,
            KnownPerson.name,
            func.count(FaceRecognition.id).label('detection_count'),
            func.max(FaceRecognition.timestamp).label('last_seen')
        ).join(FaceRecognition).filter(
            FaceRecognition.timestamp >= start_time
        ).group_by(
            KnownPerson.id, KnownPerson.name
        ).order_by(desc('detection_count')).limit(10).all()
        
        # Unusual activity detection (high activity outside normal hours)
        night_hours = [22, 23, 0, 1, 2, 3, 4, 5]  # 10 PM to 5 AM
        night_detections = self.db.query(func.count(Detection.id)).filter(
            and_(
                Detection.timestamp >= start_time,
                extract('hour', Detection.timestamp).in_(night_hours)
            )
        )
        if camera_ids:
            night_detections = night_detections.filter(Detection.camera_id.in_(camera_ids))
        
        night_activity_count = night_detections.scalar() or 0
        
        # Object class security relevance
        security_classes = ['person', 'car', 'truck', 'motorcycle', 'bicycle']
        security_query = self.db.query(
            Detection.class_name,
            func.count(Detection.id).label('count')
        ).filter(
            and_(
                Detection.timestamp >= start_time,
                Detection.class_name.in_(security_classes)
            )
        )
        if camera_ids:
            security_query = security_query.filter(Detection.camera_id.in_(camera_ids))
        
        security_detections = security_query.group_by(Detection.class_name).all()
        
        return {
            "face_recognition": {
                "total_detections": total_face_detections,
                "known_persons": known_person_detections,
                "unknown_persons": total_face_detections - known_person_detections,
                "recognition_rate": (
                    known_person_detections / max(total_face_detections, 1) * 100
                ),
                "frequent_persons": [
                    {
                        "person_id": person_id,
                        "name": name,
                        "detection_count": count,
                        "last_seen": last_seen
                    }
                    for person_id, name, count, last_seen in frequent_persons
                ]
            },
            "activity_patterns": {
                "night_activity_count": night_activity_count,
                "night_activity_percentage": (
                    night_activity_count / max(1, self.db.query(func.count(Detection.id)).filter(
                        Detection.timestamp >= start_time
                    ).scalar()) * 100
                ),
                "security_object_detections": {
                    class_name: count for class_name, count in security_detections
                }
            },
            "time_range": {
                "start_time": start_time,
                "end_time": datetime.utcnow(),
                "duration_days": days
            }
        }
    
    async def get_traffic_analysis(
        self,
        camera_ids: Optional[List[int]] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get traffic flow analysis"""
        start_time = datetime.utcnow() - timedelta(days=days)
        
        vehicle_classes = ['car', 'truck', 'bus', 'motorcycle', 'bicycle']
        
        # Vehicle detection trends
        vehicle_query = self.db.query(
            Detection.class_name,
            extract('hour', Detection.timestamp).label('hour'),
            func.count(Detection.id).label('count')
        ).filter(
            and_(
                Detection.timestamp >= start_time,
                Detection.class_name.in_(vehicle_classes)
            )
        )
        
        if camera_ids:
            vehicle_query = vehicle_query.filter(Detection.camera_id.in_(camera_ids))
        
        vehicle_trends = vehicle_query.group_by(
            Detection.class_name, 'hour'
        ).all()
        
        # Organize by vehicle type and hour
        traffic_by_hour = {}
        for class_name, hour, count in vehicle_trends:
            if class_name not in traffic_by_hour:
                traffic_by_hour[class_name] = {}
            traffic_by_hour[class_name][int(hour)] = count
        
        # Vehicle tracking analysis (speed, direction)
        vehicle_tracks = self.db.query(
            Tracking.object_class,
            Tracking.track_id,
            func.count(Tracking.id).label('frame_count'),
            func.max(Tracking.timestamp).label('last_seen'),
            func.min(Tracking.timestamp).label('first_seen')
        ).filter(
            and_(
                Tracking.timestamp >= start_time,
                Tracking.object_class.in_(vehicle_classes)
            )
        )
        
        if camera_ids:
            vehicle_tracks = vehicle_tracks.filter(Tracking.camera_id.in_(camera_ids))
        
        track_data = vehicle_tracks.group_by(
            Tracking.object_class, Tracking.track_id
        ).all()
        
        # Calculate average track duration by vehicle type
        avg_duration_by_type = {}
        for class_name, track_id, frame_count, last_seen, first_seen in track_data:
            if first_seen and last_seen:
                duration = (last_seen - first_seen).total_seconds()
                if class_name not in avg_duration_by_type:
                    avg_duration_by_type[class_name] = []
                avg_duration_by_type[class_name].append(duration)
        
        # Average durations
        for class_name in avg_duration_by_type:
            durations = avg_duration_by_type[class_name]
            avg_duration_by_type[class_name] = sum(durations) / len(durations)
        
        return {
            "vehicle_counts_by_hour": traffic_by_hour,
            "total_vehicle_detections": sum(
                sum(hourly_data.values()) for hourly_data in traffic_by_hour.values()
            ),
            "avg_track_duration_by_type": avg_duration_by_type,
            "peak_traffic_hours": self._find_peak_hours(traffic_by_hour),
            "vehicle_type_distribution": {
                vehicle_type: sum(hourly_data.values())
                for vehicle_type, hourly_data in traffic_by_hour.items()
            }
        }
    
    def _find_peak_hours(self, traffic_by_hour: Dict[str, Dict[int, int]]) -> List[Dict[str, Any]]:
        """Find peak traffic hours"""
        hourly_totals = {}
        for vehicle_type, hourly_data in traffic_by_hour.items():
            for hour, count in hourly_data.items():
                hourly_totals[hour] = hourly_totals.get(hour, 0) + count
        
        sorted_hours = sorted(hourly_totals.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {
                "hour": hour,
                "total_vehicles": count,
                "percentage": count / max(sum(hourly_totals.values()), 1) * 100
            }
            for hour, count in sorted_hours[:5]  # Top 5 hours
        ]
    
    async def get_anomaly_detection(
        self,
        camera_ids: Optional[List[int]] = None,
        days: int = 7,
        sensitivity: float = 2.0
    ) -> Dict[str, Any]:
        """Detect anomalies in activity patterns"""
        start_time = datetime.utcnow() - timedelta(days=days)
        
        # Get hourly activity for baseline
        hourly_activity = self.db.query(
            extract('hour', Detection.timestamp).label('hour'),
            extract('dow', Detection.timestamp).label('day_of_week'),  # 0=Sunday
            func.count(Detection.id).label('count')
        ).filter(Detection.timestamp >= start_time)
        
        if camera_ids:
            hourly_activity = hourly_activity.filter(Detection.camera_id.in_(camera_ids))
        
        activity_data = hourly_activity.group_by('hour', 'day_of_week').all()
        
        # Calculate baseline activity patterns
        baseline_by_hour = {}
        for hour, dow, count in activity_data:
            hour_key = f"{int(dow)}_{int(hour)}"  # "dayofweek_hour"
            if hour_key not in baseline_by_hour:
                baseline_by_hour[hour_key] = []
            baseline_by_hour[hour_key].append(count)
        
        # Calculate mean and standard deviation for each hour
        hour_stats = {}
        for hour_key, counts in baseline_by_hour.items():
            if len(counts) > 1:
                mean_count = sum(counts) / len(counts)
                variance = sum((x - mean_count) ** 2 for x in counts) / len(counts)
                std_dev = variance ** 0.5
                hour_stats[hour_key] = {
                    "mean": mean_count,
                    "std_dev": std_dev,
                    "samples": len(counts)
                }
        
        # Detect current anomalies (last 24 hours)
        recent_start = datetime.utcnow() - timedelta(hours=24)
        recent_activity = self.db.query(
            extract('hour', Detection.timestamp).label('hour'),
            extract('dow', Detection.timestamp).label('day_of_week'),
            func.count(Detection.id).label('count')
        ).filter(Detection.timestamp >= recent_start)
        
        if camera_ids:
            recent_activity = recent_activity.filter(Detection.camera_id.in_(camera_ids))
        
        recent_data = recent_activity.group_by('hour', 'day_of_week').all()
        
        anomalies = []
        for hour, dow, count in recent_data:
            hour_key = f"{int(dow)}_{int(hour)}"
            
            if hour_key in hour_stats:
                stats = hour_stats[hour_key]
                if stats['std_dev'] > 0:
                    z_score = abs(count - stats['mean']) / stats['std_dev']
                    
                    if z_score > sensitivity:
                        anomaly_type = "high" if count > stats['mean'] else "low"
                        anomalies.append({
                            "hour": int(hour),
                            "day_of_week": int(dow),
                            "actual_count": count,
                            "expected_count": round(stats['mean'], 1),
                            "z_score": round(z_score, 2),
                            "anomaly_type": anomaly_type,
                            "severity": "high" if z_score > 3 else "medium"
                        })
        
        return {
            "anomalies_detected": len(anomalies),
            "anomalies": sorted(anomalies, key=lambda x: x['z_score'], reverse=True),
            "baseline_period_days": days,
            "sensitivity_threshold": sensitivity,
            "analysis_timestamp": datetime.utcnow()
        }
    
    async def generate_daily_report(
        self,
        target_date: date,
        camera_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive daily report"""
        start_time = datetime.combine(target_date, datetime.min.time())
        end_time = start_time + timedelta(days=1)
        
        # Detection summary
        detection_query = self.db.query(Detection).filter(
            and_(
                Detection.timestamp >= start_time,
                Detection.timestamp < end_time
            )
        )
        if camera_ids:
            detection_query = detection_query.filter(Detection.camera_id.in_(camera_ids))
        
        total_detections = detection_query.count()
        detection_classes = detection_query.with_entities(
            Detection.class_name,
            func.count(Detection.id)
        ).group_by(Detection.class_name).all()
        
        # Tracking summary
        tracking_query = self.db.query(Tracking).filter(
            and_(
                Tracking.timestamp >= start_time,
                Tracking.timestamp < end_time
            )
        )
        if camera_ids:
            tracking_query = tracking_query.filter(Tracking.camera_id.in_(camera_ids))
        
        unique_tracks = tracking_query.with_entities(
            func.count(Tracking.track_id.distinct())
        ).scalar() or 0
        
        # Face recognition summary
        face_query = self.db.query(FaceRecognition).filter(
            and_(
                FaceRecognition.timestamp >= start_time,
                FaceRecognition.timestamp < end_time
            )
        )
        if camera_ids:
            face_query = face_query.filter(FaceRecognition.camera_id.in_(camera_ids))
        
        total_faces = face_query.count()
        known_faces = face_query.filter(
            FaceRecognition.known_person_id.isnot(None)
        ).count()
        
        # Peak activity hour
        hourly_detections = detection_query.with_entities(
            extract('hour', Detection.timestamp).label('hour'),
            func.count(Detection.id).label('count')
        ).group_by('hour').order_by(desc('count')).first()
        
        peak_hour = int(hourly_detections.hour) if hourly_detections else None
        peak_count = hourly_detections.count if hourly_detections else 0
        
        return {
            "date": target_date.isoformat(),
            "summary": {
                "total_detections": total_detections,
                "unique_tracks": unique_tracks,
                "total_faces": total_faces,
                "known_faces": known_faces,
                "unknown_faces": total_faces - known_faces
            },
            "detection_breakdown": {
                class_name: count for class_name, count in detection_classes
            },
            "peak_activity": {
                "hour": peak_hour,
                "detection_count": peak_count
            },
            "face_recognition_rate": (
                known_faces / max(total_faces, 1) * 100
            ),
            "cameras_analyzed": camera_ids or "all",
            "generated_at": datetime.utcnow()
        }