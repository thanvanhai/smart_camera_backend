# app/workers/rabbitmq_utils.py
import json
import asyncio
import aio_pika
from app.config import settings

async def publish_camera_event(event_type: str, camera: dict):
    """Send camera.add or camera.remove event to RabbitMQ"""
    rabbitmq_url = f"amqp://{getattr(settings, 'RABBITMQ_USER', 'guest')}:{getattr(settings, 'RABBITMQ_PASS', 'guest')}@{getattr(settings, 'RABBITMQ_HOST', 'localhost')}:{getattr(settings, 'RABBITMQ_PORT', 5672)}/"
    connection = await aio_pika.connect_robust(rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(
            "smart_camera_exchange",
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )
        # Chỉ lấy những field JSON-serializable
        message_body = {
            "camera_id": camera.get("camera_id"),
            "name": camera.get("name"),
            "stream_url": camera.get("stream_url"),
            "timestamp": None
        }
        message_body = json.dumps(message_body).encode()
        routing_key = f"camera.{event_type}"
        await exchange.publish(aio_pika.Message(body=message_body), routing_key=routing_key)
