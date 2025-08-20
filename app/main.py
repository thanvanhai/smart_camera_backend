import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.config import settings
from app.core.database import init_database, close_database
from app.core.rabbitmq import init_rabbitmq, close_rabbitmq, ros2_consumer
from app.api.v1 import cameras, detections, tracking, analytics, websocket
from app.workers.rabbitmq_consumer import start_background_consumers
from app.services.camera_service import CameraService

# Setup structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.iso_utc_timestamps_formatter(),
        structlog.processors.JSONRenderer() if settings.log_format == "json" 
        else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Smart Camera Backend", version=settings.app_version)
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized")
        
        # Initialize RabbitMQ
        await init_rabbitmq()
        logger.info("RabbitMQ initialized")
        
        # Start background consumers
        asyncio.create_task(start_background_consumers())
        logger.info("Background consumers started")
        
        logger.info("Application startup completed successfully")
        
    except Exception as e:
        logger.error("Application startup failed", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Smart Camera Backend")
    
    try:
        # Close RabbitMQ connections
        await close_rabbitmq()
        logger.info("RabbitMQ connections closed")
        
        # Close database connections
        await close_database()
        logger.info("Database connections closed")
        
        logger.info("Application shutdown completed successfully")
        
    except Exception as e:
        logger.error("Application shutdown failed", error=str(e))


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Backend API for Smart Camera System with AI-powered detection, tracking, and face recognition",
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.debug else ["localhost", "127.0.0.1"]
)


# Middleware for logging requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    start_time = datetime.utcnow()
    
    # Log request
    logger.info(
        "HTTP Request",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = (datetime.utcnow() - start_time).total_seconds()
    
    # Log response
    logger.info(
        "HTTP Response",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=f"{process_time:.3f}s",
    )
    
    # Add processing time header
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(
        "Unhandled exception",
        method=request.method,
        url=str(request.url),
        error=str(exc),
        error_type=type(exc).__name__,
    )
    
    if settings.debug:
        import traceback
        logger.error("Exception traceback", traceback=traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with service dependencies."""
    from app.core.database import db_manager
    from app.core.rabbitmq import rabbitmq_manager
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": settings.environment,
        "services": {}
    }
    
    # Check database
    try:
        db_healthy = await db_manager.health_check()
        health_status["services"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "connected": db_healthy
        }
    except Exception as e:
        health_status["services"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check RabbitMQ
    try:
        rabbitmq_healthy = await rabbitmq_manager.health_check()
        health_status["services"]["rabbitmq"] = {
            "status": "healthy" if rabbitmq_healthy else "unhealthy",
            "connected": rabbitmq_healthy
        }
    except Exception as e:
        health_status["services"]["rabbitmq"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check ROS2 consumer
    health_status["services"]["ros2_consumer"] = {
        "status": "healthy" if ros2_consumer.is_running else "unhealthy",
        "running": ros2_consumer.is_running
    }
    
    # Overall status
    all_healthy = all(
        service.get("status") == "healthy" 
        for service in health_status["services"].values()
    )
    
    if not all_healthy:
        health_status["status"] = "degraded"
    
    return health_status


# API Routes
app.include_router(
    cameras.router,
    prefix=f"{settings.api_prefix}/cameras",
    tags=["cameras"]
)

app.include_router(
    detections.router,
    prefix=f"{settings.api_prefix}/detections",
    tags=["detections"]
)

app.include_router(
    tracking.router,
    prefix=f"{settings.api_prefix}/tracking",
    tags=["tracking"]
)

app.include_router(
    analytics.router,
    prefix=f"{settings.api_prefix}/analytics",
    tags=["analytics"]
)

app.include_router(
    websocket.router,
    prefix="",
    tags=["websocket"]
)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Smart Camera System Backend API",
        "docs_url": "/docs" if settings.debug else None,
        "health_check": "/health",
        "api_prefix": settings.api_prefix,
        "timestamp": datetime.utcnow().isoformat(),
    }


# Metrics endpoint (if enabled)
if settings.enable_metrics:
    from prometheus_client import generate_latest, CollectorRegistry, Counter, Histogram
    
    # Create metrics
    REQUEST_COUNT = Counter(
        'http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status']
    )
    
    REQUEST_DURATION = Histogram(
        'http_request_duration_seconds',
        'HTTP request duration',
        ['method', 'endpoint']
    )
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(
            content=generate_latest(),
            media_type="text/plain"
        )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )