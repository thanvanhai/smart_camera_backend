import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Callable, Optional
import structlog
import aio_pika
from aio_pika import Message, ExchangeType
from aio_pika.abc import AbstractConnection, AbstractChannel, AbstractQueue

from app.config import settings

logger = structlog.get_logger(__name__)


class RabbitMQManager:
    """RabbitMQ connection and message handling manager."""
    
    def __init__(self):
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.exchange = None
        self.queues: Dict[str, AbstractQueue] = {}
        self.consumers: Dict[str, Callable] = {}
        self._is_connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
    
    async def connect(self) -> bool:
        """Establish connection to RabbitMQ server."""
        try:
            logger.info("Connecting to RabbitMQ", url=settings.rabbitmq_url)
            
            self.connection = await aio_pika.connect_robust(
                settings.rabbitmq_url,
                heartbeat=30,
                blocked_connection_timeout=300,
            )
            
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                settings.rabbitmq_exchange,
                ExchangeType.TOPIC,
                durable=True
            )
            
            self._is_connected = True
            self._reconnect_attempts = 0
            
            logger.info("RabbitMQ connection established successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to connect to RabbitMQ", error=str(e))
            self._is_connected = False
            return False
    
    async def disconnect(self):
        """Close RabbitMQ connection."""
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
                logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error("Error closing RabbitMQ connection", error=str(e))
        finally:
            self._is_connected = False
            self.connection = None
            self.channel = None
            self.exchange = None
            self.queues.clear()
    
    async def reconnect(self) -> bool:
        """Attempt to reconnect to RabbitMQ."""
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error("Max reconnection attempts reached", attempts=self._reconnect_attempts)
            return False
        
        self._reconnect_attempts += 1