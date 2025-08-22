# app/services/rabbitmq_service.py
import json
import aio_pika
from app.config import settings

async def publish_camera_event(event_type: str, camera: dict):
    """
    Publish camera events (created/removed) to RabbitMQ using aio-pika
    """
    rabbitmq_url = (
        f"amqp://{getattr(settings, 'RABBITMQ_USER', 'guest')}:" 
        f"{getattr(settings, 'RABBITMQ_PASS', 'guest')}@"
        f"{getattr(settings, 'RABBITMQ_HOST', 'localhost')}:" 
        f"{getattr(settings, 'RABBITMQ_PORT', 5672)}/"
    )

    connection = await aio_pika.connect_robust(rabbitmq_url)
    async with connection:
        channel = await connection.channel()

        # ✅ khớp với bridge_node.py
        exchange = await channel.declare_exchange(
            "camera.events",          # fanout exchange name
            aio_pika.ExchangeType.FANOUT,
            durable=True,
        )

        # payload phải có action để ROS biết add/remove
        message_body = {
            "action": event_type,                  # "created" hoặc "removed"
            "camera_id": str(camera.get("camera_id")),
            "camera_url": str(camera.get("camera_url"))# chú ý stream_url đã được xử lý trong _build_camera_created_message ở app/api/v1/cameras.py
        }

        body = json.dumps(message_body).encode()

        # với FANOUT thì routing_key = ""
        await exchange.publish(
            aio_pika.Message(body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
            routing_key=""
        )
