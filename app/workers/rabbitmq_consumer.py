import asyncio
import aio_pika
import logging

logger = logging.getLogger(__name__)

RABBITMQ_URL = "amqp://guest:guest@localhost/"  # chỉnh theo .env nếu cần
QUEUE_NAME = "smart_camera_events"


async def handle_message(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            body = message.body.decode()
            logger.info(f"[RabbitMQ] Received message: {body}")
            # TODO: Xử lý nội dung message tại đây
        except Exception as e:
            logger.error(f"Error processing message: {e}")


async def start_background_consumers():
    """
    Hàm khởi động consumer chạy nền khi backend start
    """
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()
        queue = await channel.declare_queue(QUEUE_NAME, durable=True)

        logger.info(f"[RabbitMQ] Consumer started, waiting for messages in {QUEUE_NAME}...")

        await queue.consume(handle_message)
    except Exception as e:
        logger.error(f"[RabbitMQ] Failed to start consumer: {e}")
        await asyncio.sleep(5)
        # Thử reconnect lại
        asyncio.create_task(start_background_consumers())
