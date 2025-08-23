# app/services/stream_service.py
import asyncio
import json
import base64
import logging
from typing import Dict, Optional, AsyncGenerator

import aio_pika
from fastapi import Depends
from fastapi.responses import StreamingResponse

from app.schemas.camera import CameraStreamInfo, CameraStatus
from app.services.rabbitmq_manager import rabbitmq_manager

logger = logging.getLogger(__name__)

# Dependency chung cho FastAPI
async def get_rabbitmq_connection() -> aio_pika.abc.AbstractRobustConnection:
    return await rabbitmq_manager.get_connection()

async def get_stream_service(
    connection: aio_pika.abc.AbstractRobustConnection = Depends(get_rabbitmq_connection)
):
    service = StreamService(connection)
    await service.initialize()
    return service

class StreamService:
    """Service quản lý stream camera và metadata"""
    def __init__(self, connection: aio_pika.abc.AbstractRobustConnection):
        self.connection = connection
        self.channel: Optional[aio_pika.abc.AbstractChannel] = None
        self._declared_queues: Dict[str, bool] = {}

    async def initialize(self):
        """Khởi tạo channel chung"""
        if not self.channel or self.channel.is_closed:
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=1)

    async def _ensure_queues_declared(self, camera_id: str):
        """Declare metadata + stream queues chỉ 1 lần"""
        if camera_id in self._declared_queues:
            return

        if not self.channel:
            await self.initialize()

        info_queue_name = f"camera.info.{camera_id}"
        await self.channel.declare_queue(info_queue_name, durable=False, auto_delete=True)

        stream_queue_name = f"camera.stream.{camera_id}"
        await self.channel.declare_queue(
            stream_queue_name,
            durable=False,
            auto_delete=True,
            arguments={
                "x-max-length": 5,
                "x-overflow": "drop-head",
                "x-message-ttl": 2000
            }
        )
        self._declared_queues[camera_id] = True
        logger.info(f"Declared queues for camera {camera_id}")

    async def get_stream_info(self, camera_id: str) -> Optional[CameraStreamInfo]:
        """Lấy metadata từ queue camera.info"""
        await self._ensure_queues_declared(camera_id)
        queue_name = f"camera.info.{camera_id}"
        try:
            message = await self.channel.get(queue_name, timeout=3)
            if not message:
                logger.warning(f"No info for camera {camera_id}")
                return CameraStreamInfo(
                    camera_id=camera_id,
                    stream_url=f"/api/v1/cameras/{camera_id}/stream",
                    status=CameraStatus.INACTIVE,
                    fps=None, resolution=None, codec=None, bitrate=None
                )
            async with message.process():
                payload = json.loads(message.body.decode('utf-8'))
                width, height = payload.get('width'), payload.get('height')
                return CameraStreamInfo(
                    camera_id=camera_id,
                    stream_url=f"/api/v1/cameras/{camera_id}/stream",
                    status=CameraStatus.ACTIVE,
                    fps=payload.get("fps"),
                    resolution=f"{width}x{height}" if width and height else None,
                    codec=payload.get("codec"),
                    bitrate=payload.get("bitrate")
                )
        except Exception as e:
            logger.error(f"Error getting stream info for camera {camera_id}: {e}")
            return None

    async def stream_generator(self, camera_id: str) -> AsyncGenerator[bytes, None]:
        """Generator stream video frames"""
        await self._ensure_queues_declared(camera_id)
        queue_name = f"camera.stream.{camera_id}"
        try:
            queue = await self.channel.get_queue(queue_name)
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        try:
                            payload = json.loads(message.body.decode('utf-8'))
                            frame_base64 = payload.get('frame')
                            if not frame_base64:
                                continue
                            frame_bytes = base64.b64decode(frame_base64)
                            if not (frame_bytes.startswith(b'\xff\xd8') and frame_bytes.endswith(b'\xff\xd9')):
                                continue
                            yield (
                                b'--frame\r\n'
                                b'Content-Type: image/jpeg\r\n'
                                b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n' +
                                frame_bytes + b'\r\n'
                            )
                        except Exception as e:
                            logger.warning(f"Skipping invalid frame for {camera_id}: {e}")
        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for camera {camera_id}")
            raise
        except Exception as e:
            logger.error(f"Error in stream generator for camera {camera_id}: {e}")
            raise
        finally:
            logger.info(f"Stream generator stopped for camera {camera_id}")

    async def create_streaming_response(self, camera_id: str) -> StreamingResponse:
        return StreamingResponse(
            self.stream_generator(camera_id),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "Connection": "keep-alive",
                "X-Content-Type-Options": "nosniff",
                "Access-Control-Allow-Origin": "*"
            }
        )

    async def check_camera_active(self, camera_id: str) -> bool:
        """Check camera có đang hoạt động"""
        try:
            await self._ensure_queues_declared(camera_id)
            queue = await self.channel.get_queue(f"camera.stream.{camera_id}")
            info = await queue.info()
            return info.message_count > 0
        except Exception as e:
            logger.error(f"Error checking camera {camera_id} status: {e}")
            return False
