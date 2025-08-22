import json
import logging
import asyncio
from datetime import datetime
from typing import Optional
import aio_pika
from aio_pika import IncomingMessage

from app.core.database import get_db_session
from app.services.detection_service import DetectionService
from app.services.tracking_service import TrackingService
from app.config import settings

logging.basicConfig(level=logging.INFO)
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
        await camera_event_queue.bind(exchange, 'camera.*')  # bind tất cả camera events

        logger.info("RabbitMQ queues setup completed")
        return {
            'exchange': exchange,
            'detection_queue': detection_queue,
            'tracking_queue': tracking_queue,
            'face_recognition_queue': face_recognition_queue,
            'camera_event_queue': camera_event_queue
        }

    async def process_camera_event(self, message: IncomingMessage):
        async with message.process():
            body = json.loads(message.body.decode())
            logger.info(f"Camera Event received: {body}")
            # TODO: gửi tới ROS
            logger.info(f"[ROS] Would publish to ROS: {body}")

    async def start_consuming(self):
        queues = await self.setup_queues()
        await queues['camera_event_queue'].consume(self.process_camera_event, no_ack=False)
        await queues['detection_queue'].consume(self.detection_callback, no_ack=False)
        await queues['tracking_queue'].consume(self.tracking_callback, no_ack=False)
        await queues['face_recognition_queue'].consume(self.face_callback, no_ack=False)
        logger.info("Started consuming from all queues")
        await asyncio.Future()  # keep running

    async def detection_callback(self, message: IncomingMessage):
        async with message.process():
            body = json.loads(message.body.decode())
            logger.info(f"Detection message: {body}")

    async def tracking_callback(self, message: IncomingMessage):
        async with message.process():
            body = json.loads(message.body.decode())
            logger.info(f"Tracking message: {body}")

    async def face_callback(self, message: IncomingMessage):
        async with message.process():
            body = json.loads(message.body.decode())
            logger.info(f"Face message: {body}")

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
