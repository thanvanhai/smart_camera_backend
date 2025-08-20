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
        logger.info("Attempting to reconnect to RabbitMQ", attempt=self._reconnect_attempts)
        
        await self.disconnect()
        await asyncio.sleep(5 * self._reconnect_attempts)  # Exponential backoff
        
        return await self.connect()
    
    async def declare_queue(self, queue_name: str, routing_key: str = None) -> AbstractQueue:
        """Declare a queue and bind it to the exchange."""
        if not self._is_connected:
            raise ConnectionError("Not connected to RabbitMQ")
        
        try:
            queue = await self.channel.declare_queue(
                queue_name,
                durable=True,
                auto_delete=False
            )
            
            # Bind queue to exchange with routing key
            if routing_key:
                await queue.bind(self.exchange, routing_key)
                logger.info("Queue bound to exchange", queue=queue_name, routing_key=routing_key)
            
            self.queues[queue_name] = queue
            return queue
            
        except Exception as e:
            logger.error("Failed to declare queue", queue=queue_name, error=str(e))
            raise
    
    async def publish_message(self, message: Dict[str, Any], routing_key: str) -> bool:
        """Publish a message to the exchange."""
        if not self._is_connected:
            logger.warning("Not connected to RabbitMQ, attempting reconnect")
            if not await self.reconnect():
                return False
        
        try:
            message_body = json.dumps(message, default=str)
            
            await self.exchange.publish(
                Message(
                    message_body.encode(),
                    content_type="application/json",
                    timestamp=datetime.utcnow(),
                    delivery_mode=2,  # Persistent message
                ),
                routing_key=routing_key
            )
            
            logger.debug("Message published", routing_key=routing_key, message_size=len(message_body))
            return True
            
        except Exception as e:
            logger.error("Failed to publish message", routing_key=routing_key, error=str(e))
            self._is_connected = False
            return False
    
    async def consume_queue(self, queue_name: str, callback: Callable) -> bool:
        """Start consuming messages from a queue."""
        if not self._is_connected:
            if not await self.reconnect():
                return False
        
        if queue_name not in self.queues:
            logger.error("Queue not found", queue=queue_name)
            return False
        
        try:
            queue = self.queues[queue_name]
            
            async def message_handler(message: aio_pika.abc.AbstractIncomingMessage):
                async with message.process():
                    try:
                        # Parse message body
                        message_data = json.loads(message.body.decode())
                        
                        logger.debug("Message received", queue=queue_name, message_size=len(message.body))
                        
                        # Call the callback function
                        await callback(message_data)
                        
                    except json.JSONDecodeError as e:
                        logger.error("Failed to parse message JSON", queue=queue_name, error=str(e))
                    except Exception as e:
                        logger.error("Error processing message", queue=queue_name, error=str(e))
                        raise  # Re-raise to trigger message requeue
            
            await queue.consume(message_handler)
            self.consumers[queue_name] = callback
            
            logger.info("Started consuming queue", queue=queue_name)
            return True
            
        except Exception as e:
            logger.error("Failed to start consuming queue", queue=queue_name, error=str(e))
            return False
    
    async def stop_consuming(self, queue_name: str):
        """Stop consuming messages from a queue."""
        if queue_name in self.queues:
            try:
                await self.queues[queue_name].cancel()
                if queue_name in self.consumers:
                    del self.consumers[queue_name]
                logger.info("Stopped consuming queue", queue=queue_name)
            except Exception as e:
                logger.error("Error stopping queue consumer", queue=queue_name, error=str(e))
    
    async def health_check(self) -> bool:
        """Check RabbitMQ connection health."""
        try:
            if not self._is_connected or not self.connection or self.connection.is_closed:
                return False
            
            # Try to declare a temporary queue as health check
            temp_queue = await self.channel.declare_queue("", exclusive=True)
            await temp_queue.delete()
            
            return True
            
        except Exception as e:
            logger.error("RabbitMQ health check failed", error=str(e))
            self._is_connected = False
            return False
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to RabbitMQ."""
        return self._is_connected


# Global RabbitMQ manager instance
rabbitmq_manager = RabbitMQManager()


class ROS2MessageConsumer:
    """Consumer for ROS2 messages from the bridge node."""
    
    def __init__(self, rabbitmq_manager: RabbitMQManager):
        self.rabbitmq = rabbitmq_manager
        self.message_handlers: Dict[str, Callable] = {}
        self._running = False
    
    def register_handler(self, message_type: str, handler: Callable):
        """Register a handler for specific message type."""
        self.message_handlers[message_type] = handler
        logger.info("Registered message handler", message_type=message_type)
    
    async def start_consuming(self):
        """Start consuming ROS2 messages."""
        if self._running:
            logger.warning("Consumer is already running")
            return
        
        try:
            # Connect to RabbitMQ
            if not await self.rabbitmq.connect():
                raise ConnectionError("Failed to connect to RabbitMQ")
            
            # Declare queues for different message types
            await self._setup_queues()
            
            # Start consuming from queues
            await self._start_queue_consumers()
            
            self._running = True
            logger.info("ROS2 message consumer started")
            
        except Exception as e:
            logger.error("Failed to start ROS2 consumer", error=str(e))
            raise
    
    async def stop_consuming(self):
        """Stop consuming ROS2 messages."""
        if not self._running:
            return
        
        try:
            # Stop all consumers
            for queue_name in self.rabbitmq.queues.keys():
                await self.rabbitmq.stop_consuming(queue_name)
            
            # Disconnect from RabbitMQ
            await self.rabbitmq.disconnect()
            
            self._running = False
            logger.info("ROS2 message consumer stopped")
            
        except Exception as e:
            logger.error("Error stopping ROS2 consumer", error=str(e))
    
    async def _setup_queues(self):
        """Setup queues for different ROS2 message types."""
        # Detection queue
        await self.rabbitmq.declare_queue(
            settings.rabbitmq_queue_detections,
            "ros2.detections"
        )
        
        # Tracking queue
        await self.rabbitmq.declare_queue(
            settings.rabbitmq_queue_tracking,
            "ros2.tracking"
        )
        
        # Face recognition queue
        await self.rabbitmq.declare_queue(
            settings.rabbitmq_queue_faces,
            "ros2.faces"
        )
    
    async def _start_queue_consumers(self):
        """Start consuming from all queues."""
        # Detection messages
        await self.rabbitmq.consume_queue(
            settings.rabbitmq_queue_detections,
            self._handle_detection_message
        )
        
        # Tracking messages
        await self.rabbitmq.consume_queue(
            settings.rabbitmq_queue_tracking,
            self._handle_tracking_message
        )
        
        # Face recognition messages
        await self.rabbitmq.consume_queue(
            settings.rabbitmq_queue_faces,
            self._handle_face_message
        )
    
    async def _handle_detection_message(self, message_data: Dict[str, Any]):
        """Handle detection message from ROS2."""
        try:
            if "detections" in self.message_handlers:
                await self.message_handlers["detections"](message_data)
            else:
                logger.debug("No handler registered for detections")
                
        except Exception as e:
            logger.error("Error handling detection message", error=str(e))
            raise
    
    async def _handle_tracking_message(self, message_data: Dict[str, Any]):
        """Handle tracking message from ROS2."""
        try:
            if "tracking" in self.message_handlers:
                await self.message_handlers["tracking"](message_data)
            else:
                logger.debug("No handler registered for tracking")
                
        except Exception as e:
            logger.error("Error handling tracking message", error=str(e))
            raise
    
    async def _handle_face_message(self, message_data: Dict[str, Any]):
        """Handle face recognition message from ROS2."""
        try:
            if "faces" in self.message_handlers:
                await self.message_handlers["faces"](message_data)
            else:
                logger.debug("No handler registered for faces")
                
        except Exception as e:
            logger.error("Error handling face message", error=str(e))
            raise
    
    @property
    def is_running(self) -> bool:
        """Check if consumer is running."""
        return self._running


# Global ROS2 consumer instance
ros2_consumer = ROS2MessageConsumer(rabbitmq_manager)


# Utility functions for RabbitMQ operations
async def init_rabbitmq():
    """Initialize RabbitMQ connection on application startup."""
    try:
        await rabbitmq_manager.connect()
        logger.info("RabbitMQ initialization completed")
    except Exception as e:
        logger.error("RabbitMQ initialization failed", error=str(e))
        raise


async def close_rabbitmq():
    """Close RabbitMQ connection on application shutdown."""
    try:
        await ros2_consumer.stop_consuming()
        await rabbitmq_manager.disconnect()
        logger.info("RabbitMQ shutdown completed")
    except Exception as e:
        logger.error("RabbitMQ shutdown failed", error=str(e))