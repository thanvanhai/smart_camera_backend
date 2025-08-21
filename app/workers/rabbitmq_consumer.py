# app/workers/rabbitmq_consumer.py
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import aio_pika
from aio_pika import IncomingMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session  # Fixed import path
from app.services.detection_service import DetectionService  # Fixed import path
from app.services.tracking_service import TrackingService
from app.services.analytics_service import AnalyticsService
from app.config import settings

logger = logging.getLogger(__name__)

class RabbitMQConsumer:
    def __init__(self):
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        # Don't initialize services here - they need async db sessions
        # self.detection_service = DetectionService()  # REMOVED
        # self.tracking_service = TrackingService()    # REMOVED  
        # self.analytics_service = AnalyticsService()  # REMOVED
        
    async def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            # Use the same connection URL pattern as your settings
            rabbitmq_url = f"amqp://{getattr(settings, 'RABBITMQ_USER', 'guest')}:{getattr(settings, 'RABBITMQ_PASS', 'guest')}@{getattr(settings, 'RABBITMQ_HOST', 'localhost')}:{getattr(settings, 'RABBITMQ_PORT', 5672)}/"
            
            self.connection = await aio_pika.connect_robust(rabbitmq_url)
            self.channel = await self.connection.channel()
            
            # Set QoS to process one message at a time
            await self.channel.set_qos(prefetch_count=1)
            
            logger.info("Connected to RabbitMQ successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    async def setup_queues(self):
        """Setup RabbitMQ queues and exchanges"""
        try:
            # Declare exchange
            exchange = await self.channel.declare_exchange(
                'smart_camera_exchange',
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            # Declare queues
            detection_queue = await self.channel.declare_queue(
                'detection_queue',
                durable=True
            )
            
            tracking_queue = await self.channel.declare_queue(
                'tracking_queue',
                durable=True
            )
            
            face_recognition_queue = await self.channel.declare_queue(
                'face_recognition_queue',
                durable=True
            )
            
            # Bind queues to exchange
            await detection_queue.bind(exchange, 'camera.detection.*')
            await tracking_queue.bind(exchange, 'camera.tracking.*')
            await face_recognition_queue.bind(exchange, 'camera.face.*')
            
            logger.info("RabbitMQ queues setup completed")
            
            return {
                'exchange': exchange,
                'detection_queue': detection_queue,
                'tracking_queue': tracking_queue,
                'face_recognition_queue': face_recognition_queue
            }
            
        except Exception as e:
            logger.error(f"Failed to setup queues: {e}")
            raise
    
    async def process_detection_message(self, message: IncomingMessage):
        """Process detection messages from ROS"""
        async with message.process():
            try:
                # Parse message
                body = json.loads(message.body.decode())
                logger.info(f"Received detection message: {body}")
                
                # Extract data
                camera_id = body.get('camera_id')
                timestamp = datetime.fromisoformat(body.get('timestamp', datetime.now().isoformat()))
                objects = body.get('objects', [])
                raw_data = body.get('raw_data', '')
                
                # Validate required fields
                if not camera_id:
                    logger.error("Missing camera_id in detection message")
                    return
                
                # Create detection record with proper async session
                async for db in get_db_session():  # Fixed: use async for
                    detection_service = DetectionService(db)  # Create service with db session
                    
                    # Process each object detection
                    for obj in objects:
                        detection_data = {
                            'camera_id': camera_id,
                            'class_name': obj.get('class_name', 'unknown'),
                            'confidence': obj.get('confidence', 0.0),
                            'bbox': obj.get('bbox', {'x': 0, 'y': 0, 'width': 0, 'height': 0}),
                            'timestamp': timestamp,
                            'frame_id': body.get('frame_id', ''),
                            'additional_data': {'raw_data': raw_data}
                        }
                        
                        # Convert to DetectionCreate schema if needed
                        from app.schemas.detection import DetectionCreate
                        detection_create = DetectionCreate(**detection_data)
                        
                        detection = await detection_service.create_detection(detection_create)
                        logger.info(f"Created detection record: {detection.id}")
                    
                    # Update analytics if you have analytics service
                    # await self.analytics_service.update_detection_stats(db, camera_id, len(objects))
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse detection message JSON: {e}")
            except Exception as e:
                logger.error(f"Error processing detection message: {e}")
    
    async def process_tracking_message(self, message: IncomingMessage):
        """Process tracking messages from ROS"""
        async with message.process():
            try:
                body = json.loads(message.body.decode())
                logger.info(f"Received tracking message: {body}")
                
                camera_id = body.get('camera_id')
                tracks = body.get('tracks', [])
                timestamp = datetime.fromisoformat(body.get('timestamp', datetime.now().isoformat()))
                
                if not camera_id:
                    logger.error("Missing camera_id in tracking message")
                    return
                
                async for db in get_db_session():  # Fixed: use async for
                    # tracking_service = TrackingService(db)  # You'll need to update TrackingService too
                    
                    for track in tracks:
                        track_data = {
                            'camera_id': camera_id,
                            'track_id': track.get('track_id'),
                            'object_type': track.get('object_type', 'person'),
                            'confidence': track.get('confidence', 0.0),
                            'timestamp': timestamp,
                            'location': track.get('location', {})
                        }
                        
                        # await tracking_service.create_tracking(track_data)
                        logger.info(f"Would process tracking data: {track_data}")
                    
                    logger.info(f"Processed {len(tracks)} tracking records")
                    
                    # Update analytics
                    # await self.analytics_service.update_tracking_stats(db, camera_id, len(tracks))
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse tracking message JSON: {e}")
            except Exception as e:
                logger.error(f"Error processing tracking message: {e}")
    
    async def process_face_recognition_message(self, message: IncomingMessage):
        """Process face recognition messages from ROS"""
        async with message.process():
            try:
                body = json.loads(message.body.decode())
                logger.info(f"Received face recognition message: {body}")
                
                camera_id = body.get('camera_id')
                faces = body.get('faces', [])
                timestamp = datetime.fromisoformat(body.get('timestamp', datetime.now().isoformat()))
                
                if not camera_id:
                    logger.error("Missing camera_id in face recognition message")
                    return
                
                async for db in get_db_session():  # Fixed: use async for
                    for face in faces:
                        face_data = {
                            'camera_id': camera_id,
                            'person_id': face.get('person_id'),
                            'confidence': face.get('confidence', 0.0),
                            'timestamp': timestamp,
                            'face_embedding': face.get('face_embedding'),
                            'image_crop': face.get('image_crop')
                        }
                        
                        # Save to face_recognitions table via service
                        # (You'll need to implement this in face recognition service)
                        logger.info(f"Face recognition data: {face_data}")
                    
                    logger.info(f"Processed {len(faces)} face recognition records")
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse face recognition message JSON: {e}")
            except Exception as e:
                logger.error(f"Error processing face recognition message: {e}")
    
    async def start_consuming(self):
        """Start consuming messages from all queues"""
        try:
            queues = await self.setup_queues()
            
            # Start consuming from detection queue
            await queues['detection_queue'].consume(
                self.process_detection_message,
                no_ack=False
            )
            
            # Start consuming from tracking queue
            await queues['tracking_queue'].consume(
                self.process_tracking_message,
                no_ack=False
            )
            
            # Start consuming from face recognition queue
            await queues['face_recognition_queue'].consume(
                self.process_face_recognition_message,
                no_ack=False
            )
            
            logger.info("Started consuming from all queues")
            
            # Keep the consumer running
            await asyncio.Future()
            
        except Exception as e:
            logger.error(f"Error in start_consuming: {e}")
            raise
    
    async def close(self):
        """Close RabbitMQ connection"""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("RabbitMQ connection closed")

# Consumer instance
consumer = RabbitMQConsumer()

async def run_consumer():
    """Run the RabbitMQ consumer"""
    try:
        if await consumer.connect():
            await consumer.start_consuming()
    except KeyboardInterrupt:
        logger.info("Consumer interrupted by user")
    except Exception as e:
        logger.error(f"Consumer error: {e}")
    finally:
        await consumer.close()

if __name__ == "__main__":
    # For testing purposes
    asyncio.run(run_consumer())