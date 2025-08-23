# app/services/rabbitmq_manager.py
import logging
from typing import Optional
import aio_pika
from app.config import settings

logger = logging.getLogger(__name__)

class RabbitMQManager:
    """Singleton RabbitMQ connection manager cho toàn app."""
    _instance = None
    _connection: Optional[aio_pika.abc.AbstractRobustConnection] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_connection(self) -> aio_pika.abc.AbstractRobustConnection:
        """Trả về connection duy nhất, tạo mới nếu chưa có."""
        if self._connection is None or self._connection.is_closed:
            url = (
                f"amqp://{getattr(settings, 'RABBITMQ_USER', 'guest')}:"
                f"{getattr(settings, 'RABBITMQ_PASS', 'guest')}@"
                f"{getattr(settings, 'RABBITMQ_HOST', 'localhost')}:"
                f"{getattr(settings, 'RABBITMQ_PORT', 5672)}/"
            )
            logger.info("Connecting to RabbitMQ...")
            self._connection = await aio_pika.connect_robust(
                url,
                client_properties={"connection_name": "FastAPI-SharedConnection"}
            )
            logger.info("RabbitMQ connected")
        return self._connection

    async def close_connection(self):
        """Đóng connection khi shutdown app."""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("RabbitMQ connection closed")
            self._connection = None

# Singleton instance
rabbitmq_manager = RabbitMQManager()
