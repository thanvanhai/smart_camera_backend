# app/services/rabbitmq_service.py
import json
import aio_pika
from app.services.rabbitmq_manager import rabbitmq_manager

async def publish_camera_event(payload: dict):
    """
    Publish camera events (created/removed) to RabbitMQ.
    Dùng chung connection singleton.
    """
    connection = await rabbitmq_manager.get_connection()
    channel = await connection.channel()

    exchange = await channel.declare_exchange(
        "camera.events",
        aio_pika.ExchangeType.FANOUT,
        durable=True
    )

    body = json.dumps(payload).encode()
    await exchange.publish(
        aio_pika.Message(body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
        routing_key=""  # fanout
    )
