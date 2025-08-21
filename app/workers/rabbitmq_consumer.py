# app/workers/rabbitmq_consumer.py
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional
import aio_pika
from aio_pika import IncomingMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.detection_service import DetectionService
from app.services.tracking_service import TrackingService
from app.services.analytics_service import AnalyticsService
from app.config import settings

logger = logging.getLogger(__name__)

class RabbitMQConsumer:
    def __init__(self):
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None

    async def connect(self):
        try:
            rabbitmq_url = f"amqp://{getattr(settings, 'RABBITMQ_USER', 'guest')}:{getattr(settings, 'RABBITMQ_PASS', 'guest')}@{getattr(settings, 'RABBITMQ_HOST', 'localhost')}:{getattr(settings, 'RABBITMQ_PORT', 5672)}/"
            self.connection = await aio_pika.connect_robust(rabbitmq_url)
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=1)
            logger.info("Connected to RabbitMQ successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False

    async def setup_queues(self):
        try:
            exchange = await self.channel.declare_exchange(
                'smart_camera_exchange', aio_pika.ExchangeType.TOPIC, durable=True
            )
            
            # Queues
            detection_queue = await self.channel.declare_queue('detection_queue', durable=True)
            tracking_queue = await self.channel.declare_queue('tracking_queue', durable=True)
            face_recognition_queue = await self.channel.declare_queue('face_recognition_queue', durable=True)
            camera_event_queue = await self.channel.declare_queue('camera_event_queue', durable=True)
            
            # Bind queues
            await detection_queue.bind(exchange, 'camera.detection.*')
            await tracking_queue.bind(exchange, 'camera.tracking.*')
            await face_recognition_queue.bind(exchange, 'camera.face.*')
            await camera_event_queue.bind(exchange, 'camera.event')
            
            logger.info("RabbitMQ queues setup completed")
            return {
                'exchange': exchange,
                'detection_queue': detection_queue,
                'tracking_queue': tracking_queue,
                'face_recognition_queue': face_recognition_queue,
                'camera_event_queue': camera_event_queue
            }
        except Exception as e:
            logger.error(f"Failed to setup queues: {e}")
            raise

    async def process_camera_event(self, message: IncomingMessage):
        async with message.process():
            try:
                body = json.loads(message.body.decode())
                action = body.get("action")
                camera = body.get("camera")
                
                if action == "add":
                    await self.send_to_ros("/camera/add", camera)
                elif action == "remove":
                    await self.send_to_ros("/camera/remove", camera)
                
                logger.info(f"Processed camera event: {action} {camera}")
            except Exception as e:
                logger.error(f"Error processing camera event: {e}")

    async def send_to_ros(self, topic: str, payload: dict):
        # TODO: implement ROS publishing
        logger.info(f"[ROS] Publishing to {topic}: {payload}")

    async def process_detection_message(self, message: IncomingMessage):
        async with message.process():
            try:
                body = json.loads(message.body.decode())
                logger.info(f"Received detection message: {body}")
                camera_id = body.get('camera_id')
                timestamp = datetime.fromisoformat(body.get('timestamp', datetime.now().isoformat()))
                objects = body.get('objects', [])
                raw_data = body.get('raw_data', '')

                if not camera_id:
                    logger.error("Missing camera_id in detection message")
                    return

                async for db in get_db_session():
                    detection_service = DetectionService(db)
                    from app.schemas.detection import DetectionCreate

                    for obj in objects:
                        detection_data = {
                            'camera_id': camera_id,
                            'class_name': obj.get('class_name', 'unknown'),
                            'confidence': obj.get('confidence', 0.0),
                            'bbox': obj.get('bbox', {'x':0,'y':0,'width':0,'height':0}),
                            'timestamp': timestamp,
                            'frame_id': body.get('frame_id', ''),
                            'additional_data': {'raw_data': raw_data}
                        }
                        detection_create = DetectionCreate(**detection_data)
                        detection = await detection_service.create_detection(detection_create)
                        logger.info(f"Created detection record: {detection.id}")

            except Exception as e:
                logger.error(f"Error processing detection message: {e}")

    async def process_tracking_message(self, message: IncomingMessage):
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

                async for db in get_db_session():
                    for track in tracks:
                        track_data = {
                            'camera_id': camera_id,
                            'track_id': track.get('track_id'),
                            'object_type': track.get('object_type', 'person'),
                            'confidence': track.get('confidence', 0.0),
                            'timestamp': timestamp,
                            'location': track.get('location', {})
                        }
                        logger.info(f"Would process tracking data: {track_data}")

            except Exception as e:
                logger.error(f"Error processing tracking message: {e}")

    async def process_face_recognition_message(self, message: IncomingMessage):
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

                async for db in get_db_session():
                    for face in faces:
                        face_data = {
                            'camera_id': camera_id,
                            'person_id': face.get('person_id'),
                            'confidence': face.get('confidence', 0.0),
                            'timestamp': timestamp,
                            'face_embedding': face.get('face_embedding'),
                            'image_crop': face.get('image_crop')
                        }
                        logger.info(f"Face recognition data: {face_data}")

            except Exception as e:
                logger.error(f"Error processing face recognition message: {e}")

    async def start_consuming(self):
        queues = await self.setup_queues()

        # Camera event consumer
        await queues['camera_event_queue'].consume(self.process_camera_event, no_ack=False)

        # Detection/tracking/face consumers
        await queues['detection_queue'].consume(self.process_detection_message, no_ack=False)
        await queues['tracking_queue'].consume(self.process_tracking_message, no_ack=False)
        await queues['face_recognition_queue'].consume(self.process_face_recognition_message, no_ack=False)

        logger.info("Started consuming from all queues")
        await asyncio.Future()  # keep running

    async def close(self):
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("RabbitMQ connection closed")

consumer = RabbitMQConsumer()

async def run_consumer():
    if await consumer.connect():
        await consumer.start_consuming()

if __name__ == "__main__":
    asyncio.run(run_consumer())
