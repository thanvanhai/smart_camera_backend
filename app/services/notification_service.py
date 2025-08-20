"""
Notification and alert service
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Callable
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from enum import Enum

from ..core.rabbitmq import RabbitMQManager
from ..models.camera import Camera
from ..models.detection import Detection
from ..models.tracking import Tracking
from ..models.face_recognition import FaceRecognition, KnownPerson

class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(str, Enum):
    DETECTION = "detection"
    TRACKING = "tracking"
    FACE_RECOGNITION = "face_recognition"
    CAMERA_STATUS = "camera_status"
    SYSTEM = "system"

class NotificationChannel(str, Enum):
    WEBSOCKET = "websocket"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    RABBITMQ = "rabbitmq"

class NotificationService:
    """Service for managing notifications and alerts"""
    
    def __init__(self, db: Session, rabbitmq: Optional[RabbitMQManager] = None):
        self.db = db
        self.rabbitmq = rabbitmq
        self.alert_rules = {}
        self.notification_channels = {}
        self.websocket_connections = set()
    
    async def setup_alert_rules(self):
        """Setup default alert rules"""
        self.alert_rules = {
            "person_detection": {
                "enabled": True,
                "conditions": {
                    "class_name": "person",
                    "min_confidence": 0.7
                },
                "severity": AlertSeverity.MEDIUM,
                "channels": [NotificationChannel.WEBSOCKET]
            },
            "high_confidence_detection": {
                "enabled": True,
                "conditions": {
                    "min_confidence": 0.9
                },
                "severity": AlertSeverity.LOW,
                "channels": [NotificationChannel.WEBSOCKET]
            },
            "unknown_person": {
                "enabled": True,
                "conditions": {
                    "face_detection": True,
                    "known_person": False
                },
                "severity": AlertSeverity.MEDIUM,
                "channels": [NotificationChannel.WEBSOCKET, NotificationChannel.EMAIL]
            },
            "known_person_blacklist": {
                "enabled": True,
                "conditions": {
                    "known_person": True,
                    "blacklisted": True
                },
                "severity": AlertSeverity.HIGH,
                "channels": [NotificationChannel.WEBSOCKET, NotificationChannel.EMAIL, NotificationChannel.SMS]
            },
            "loitering_detection": {
                "enabled": True,
                "conditions": {
                    "track_duration_minutes": 10,
                    "movement_threshold": 0.1
                },
                "severity": AlertSeverity.HIGH,
                "channels": [NotificationChannel.WEBSOCKET, NotificationChannel.EMAIL]
            },
            "camera_offline": {
                "enabled": True,
                "conditions": {
                    "offline_minutes": 5
                },
                "severity": AlertSeverity.CRITICAL,
                "channels": [NotificationChannel.WEBSOCKET, NotificationChannel.EMAIL]
            },
            "intrusion_detection": {
                "enabled": True,
                "conditions": {
                    "restricted_area": True,
                    "time_range": "22:00-06:00"
                },
                "severity": AlertSeverity.CRITICAL,
                "channels": [NotificationChannel.WEBSOCKET, NotificationChannel.EMAIL, NotificationChannel.SMS]
            }
        }
    
    async def process_detection_alert(self, detection: Detection) -> List[Dict[str, Any]]:
        """Process detection for potential alerts"""
        alerts = []
        camera = await self._get_camera(detection.camera_id)
        
        if not camera:
            return alerts
        
        # Check person detection rule
        if self._check_rule_enabled("person_detection"):
            rule = self.alert_rules["person_detection"]
            if (detection.class_name == rule["conditions"]["class_name"] and
                detection.confidence >= rule["conditions"]["min_confidence"]):
                
                alert = await self._create_alert(
                    alert_type=AlertType.DETECTION,
                    severity=rule["severity"],
                    title=f"Person detected on {camera.name}",
                    message=f"Person detected with {detection.confidence:.2f} confidence",
                    camera_id=detection.camera_id,
                    detection_id=detection.id,
                    metadata={
                        "confidence": detection.confidence,
                        "bbox": {
                            "x": detection.bbox_x,
                            "y": detection.bbox_y,
                            "width": detection.bbox_width,
                            "height": detection.bbox_height
                        }
                    }
                )
                alerts.append(alert)
                await self._send_alert(alert, rule["channels"])
        
        # Check high confidence detection rule
        if self._check_rule_enabled("high_confidence_detection"):
            rule = self.alert_rules["high_confidence_detection"]
            if detection.confidence >= rule["conditions"]["min_confidence"]:
                alert = await self._create_alert(
                    alert_type=AlertType.DETECTION,
                    severity=rule["severity"],
                    title=f"High confidence detection on {camera.name}",
                    message=f"{detection.class_name} detected with {detection.confidence:.2f} confidence",
                    camera_id=detection.camera_id,
                    detection_id=detection.id,
                    metadata={"confidence": detection.confidence}
                )
                alerts.append(alert)
                await self._send_alert(alert, rule["channels"])
        
        return alerts
    
    async def process_face_recognition_alert(
        self, 
        face_recognition: FaceRecognition
    ) -> List[Dict[str, Any]]:
        """Process face recognition for potential alerts"""
        alerts = []
        camera = await self._get_camera(face_recognition.camera_id)
        
        if not camera:
            return alerts
        
        # Unknown person alert
        if (self._check_rule_enabled("unknown_person") and 
            face_recognition.known_person_id is None):
            
            rule = self.alert_rules["unknown_person"]
            alert = await self._create_alert(
                alert_type=AlertType.FACE_RECOGNITION,
                severity=rule["severity"],
                title=f"Unknown person detected on {camera.name}",
                message="Unrecognized face detected",
                camera_id=face_recognition.camera_id,
                face_recognition_id=face_recognition.id,
                metadata={
                    "confidence": face_recognition.confidence,
                    "age_estimate": face_recognition.age_estimate,
                    "gender_estimate": face_recognition.gender_estimate
                }
            )
            alerts.append(alert)
            await self._send_alert(alert, rule["channels"])
        
        # Known person (blacklist) alert
        elif (self._check_rule_enabled("known_person_blacklist") and 
              face_recognition.known_person_id is not None):
            
            known_person = self.db.query(KnownPerson).filter(
                KnownPerson.id == face_recognition.known_person_id
            ).first()
            
            if (known_person and 
                known_person.metadata and 
                known_person.metadata.get('blacklisted', False)):
                
                rule = self.alert_rules["known_person_blacklist"]
                alert = await self._create_alert(
                    alert_type=AlertType.FACE_RECOGNITION,
                    severity=rule["severity"],
                    title=f"Blacklisted person detected on {camera.name}",
                    message=f"Blacklisted person '{known_person.name}' detected",
                    camera_id=face_recognition.camera_id,
                    face_recognition_id=face_recognition.id,
                    metadata={
                        "known_person_name": known_person.name,
                        "confidence": face_recognition.confidence
                    }
                )
                alerts.append(alert)
                await self._send_alert(alert, rule["channels"])
        
        return alerts
    
    async def process_tracking_alert(
        self, 
        track_id: str, 
        camera_id: int
    ) -> List[Dict[str, Any]]:
        """Process tracking data for loitering alerts"""
        alerts = []
        
        if not self._check_rule_enabled("loitering_detection"):
            return alerts
        
        # Get track data
        track_data = self.db.query(Tracking).filter(
            and_(
                Tracking.track_id == track_id,
                Tracking.camera_id == camera_id
            )
        ).order_by(Tracking.timestamp).all()
        
        if len(track_data) < 2:
            return alerts
        
        # Calculate track duration and movement
        first_seen = track_data[0].timestamp
        last_seen = track_data[-1].timestamp
        duration_minutes = (last_seen - first_seen).total_seconds() / 60
        
        rule = self.alert_rules["loitering_detection"]
        min_duration = rule["conditions"]["track_duration_minutes"]
        
        if duration_minutes >= min_duration:
            # Calculate movement area
            x_coords = [t.bbox_x for t in track_data]
            y_coords = [t.bbox_y for t in track_data]
            movement_area = (
                (max(x_coords) - min(x_coords)) * 
                (max(y_coords) - min(y_coords))
            )
            
            movement_threshold = rule["conditions"]["movement_threshold"]
            
            if movement_area <= movement_threshold:
                camera = await self._get_camera(camera_id)
                alert = await self._create_alert(
                    alert_type=AlertType.TRACKING,
                    severity=rule["severity"],
                    title=f"Loitering detected on {camera.name if camera else 'Unknown'}",
                    message=f"Object has been stationary for {duration_minutes:.1f} minutes",
                    camera_id=camera_id,
                    metadata={
                        "track_id": track_id,
                        "duration_minutes": duration_minutes,
                        "movement_area": movement_area,
                        "object_class": track_data[0].object_class
                    }
                )
                alerts.append(alert)
                await self._send_alert(alert, rule["channels"])
        
        return alerts
    
    async def process_camera_status_alert(
        self, 
        camera: Camera
    ) -> List[Dict[str, Any]]:
        """Process camera status for offline alerts"""
        alerts = []
        
        if not self._check_rule_enabled("camera_offline"):
            return alerts
        
        if not camera.last_seen:
            return alerts
        
        rule = self.alert_rules["camera_offline"]
        offline_minutes = rule["conditions"]["offline_minutes"]
        cutoff_time = datetime.utcnow() - timedelta(minutes=offline_minutes)
        
        if camera.last_seen < cutoff_time and camera.status == 'active':
            alert = await self._create_alert(
                alert_type=AlertType.CAMERA_STATUS,
                severity=rule["severity"],
                title=f"Camera offline: {camera.name}",
                message=f"Camera has been offline for more than {offline_minutes} minutes",
                camera_id=camera.id,
                metadata={
                    "last_seen": camera.last_seen.isoformat(),
                    "offline_duration": (datetime.utcnow() - camera.last_seen).total_seconds() / 60
                }
            )
            alerts.append(alert)
            await self._send_alert(alert, rule["channels"])
        
        return alerts
    
    async def send_real_time_detection(self, detection: Detection):
        """Send real-time detection to WebSocket clients"""
        camera = await self._get_camera(detection.camera_id)
        
        message = {
            "type": "detection",
            "timestamp": detection.timestamp.isoformat(),
            "camera": {
                "id": detection.camera_id,
                "name": camera.name if camera else "Unknown"
            },
            "detection": {
                "id": detection.id,
                "class_name": detection.class_name,
                "confidence": detection.confidence,
                "bbox": {
                    "x": detection.bbox_x,
                    "y": detection.bbox_y,
                    "width": detection.bbox_width,
                    "height": detection.bbox_height
                }
            }
        }
        
        await self._broadcast_websocket(message)
    
    async def send_real_time_tracking(self, tracking: Tracking):
        """Send real-time tracking to WebSocket clients"""
        camera = await self._get_camera(tracking.camera_id)
        
        message = {
            "type": "tracking",
            "timestamp": tracking.timestamp.isoformat(),
            "camera": {
                "id": tracking.camera_id,
                "name": camera.name if camera else "Unknown"
            },
            "tracking": {
                "track_id": tracking.track_id,
                "object_class": tracking.object_class,
                "confidence": tracking.confidence,
                "bbox": {
                    "x": tracking.bbox_x,
                    "y": tracking.bbox_y,
                    "width": tracking.bbox_width,
                    "height": tracking.bbox_height
                },
                "velocity": {
                    "x": tracking.velocity_x,
                    "y": tracking.velocity_y
                } if tracking.velocity_x is not None else None
            }
        }
        
        await self._broadcast_websocket(message)
    
    async def add_websocket_connection(self, websocket):
        """Add WebSocket connection"""
        self.websocket_connections.add(websocket)
    
    async def remove_websocket_connection(self, websocket):
        """Remove WebSocket connection"""
        self.websocket_connections.discard(websocket)
    
    async def _create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        camera_id: Optional[int] = None,
        detection_id: Optional[int] = None,
        tracking_id: Optional[int] = None,
        face_recognition_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create alert object"""
        return {
            "id": f"alert_{datetime.utcnow().timestamp()}",
            "type": alert_type.value,
            "severity": severity.value,
            "title": title,
            "message": message,
            "camera_id": camera_id,
            "detection_id": detection_id,
            "tracking_id": tracking_id,
            "face_recognition_id": face_recognition_id,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
            "acknowledged": False
        }
    
    async def _send_alert(
        self, 
        alert: Dict[str, Any], 
        channels: List[NotificationChannel]
    ):
        """Send alert through specified channels"""
        for channel in channels:
            if channel == NotificationChannel.WEBSOCKET:
                await self._send_websocket_alert(alert)
            elif channel == NotificationChannel.EMAIL:
                await self._send_email_alert(alert)
            elif channel == NotificationChannel.SMS:
                await self._send_sms_alert(alert)
            elif channel == NotificationChannel.WEBHOOK:
                await self._send_webhook_alert(alert)
            elif channel == NotificationChannel.RABBITMQ:
                await self._send_rabbitmq_alert(alert)
    
    async def _send_websocket_alert(self, alert: Dict[str, Any]):
        """Send alert via WebSocket"""
        message = {
            "type": "alert",
            **alert
        }
        await self._broadcast_websocket(message)
    
    async def _broadcast_websocket(self, message: Dict[str, Any]):
        """Broadcast message to all WebSocket connections"""
        if not self.websocket_connections:
            return
        
        disconnected = set()
        for websocket in self.websocket_connections.copy():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception:
                disconnected.add(websocket)
        
        # Remove disconnected websockets
        for websocket in disconnected:
            self.websocket_connections.discard(websocket)
    
    async def _send_email_alert(self, alert: Dict[str, Any]):
        """Send alert via email (placeholder)"""
        try:
            # TODO: Replace with real email service (SMTP, SendGrid, etc.)
            print(f"[EMAIL] To: admin@example.com | Subject: {alert['title']} | Message: {alert['message']}")
        except Exception as e:
            print(f"Email alert failed: {e}")

    async def _send_sms_alert(self, alert: Dict[str, Any]):
        """Send alert via SMS (placeholder)"""
        try:
            # TODO: Replace with real SMS service (Twilio, etc.)
            print(f"[SMS] To: +84123456789 | {alert['title']} - {alert['message']}")
        except Exception as e:
            print(f"SMS alert failed: {e}")

    async def _send_webhook_alert(self, alert: Dict[str, Any]):
        """Send alert via Webhook (placeholder)"""
        import aiohttp
        try:
            webhook_url = "http://localhost:8000/webhook/alerts"
            async with aiohttp.ClientSession() as session:
                await session.post(webhook_url, json=alert, timeout=5)
            print(f"[WEBHOOK] Sent alert to {webhook_url}")
        except Exception as e:
            print(f"Webhook alert failed: {e}")

    async def _send_rabbitmq_alert(self, alert: Dict[str, Any]):
        """Send alert via RabbitMQ"""
        try:
            if not self.rabbitmq:
                print("RabbitMQ connection not available, skipping...")
                return
            await self.rabbitmq.publish(
                exchange="alerts",
                routing_key="alerts.event",
                body=json.dumps(alert)
            )
            print("[RABBITMQ] Alert published")
        except Exception as e:
            print(f"RabbitMQ alert failed: {e}")

    def _check_rule_enabled(self, rule_name: str) -> bool:
        """Check if a rule is enabled"""
        rule = self.alert_rules.get(rule_name)
        return bool(rule and rule.get("enabled", False))

    async def _get_camera(self, camera_id: int) -> Optional[Camera]:
        """Get camera by ID"""
        return self.db.query(Camera).filter(Camera.id == camera_id).first()
