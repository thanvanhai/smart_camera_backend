smart_camera_backend/
├── docker-compose.yml          # Infrastructure setup
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── .gitignore
├── README.md
│
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI application entry point
│   ├── config.py            # Configuration management
│   │
│   ├── core/                # Core business logic
│   │   ├── __init__.py
│   │   ├── security.py      # Authentication & authorization
│   │   ├── database.py      # Database connection & models
│   │   └── rabbitmq.py     # RabbitMQ connection & consumer
│   │
│   ├── models/              # Database models
│   │   ├── __init__.py
│   │   ├── camera.py        # Camera model
│   │   ├── detection.py     # Detection results model
│   │   ├── tracking.py      # Tracking data model
│   │   └── face_recognition.py # Face recognition model
│   │
│   ├── schemas/             # Pydantic schemas (API contracts)
│   │   ├── __init__.py
│   │   ├── camera.py
│   │   ├── detection.py
│   │   ├── tracking.py
│   │   └── face_recognition.py
│   │
│   ├── api/                 # API routes
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── cameras.py   # Camera management endpoints
│   │   │   ├── detections.py # Detection results endpoints
│   │   │   ├── tracking.py  # Tracking data endpoints
│   │   │   ├── analytics.py # Analytics & statistics
│   │   │   └── websocket.py # Real-time WebSocket
│   │   └── deps.py          # API dependencies
│   │
│   ├── services/            # Business logic services
│   │   ├── __init__.py
│   │   ├── camera_service.py
│   │   ├── detection_service.py
│   │   ├── tracking_service.py
│   │   ├── analytics_service.py
│   │   └── notification_service.py
│   │
│   └── workers/             # Background workers
│       ├── __init__.py
│       ├── rabbitmq_consumer.py  # Consume ROS2 data
│       ├── data_processor.py     # Process detection data
│       └── cleanup_worker.py     # Cleanup old data
│
├── alembic/                 # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── tests/                   # Test files
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api/
│   ├── test_services/
│   └── test_workers/
│
└── scripts/                 # Utility scripts
    ├── init_db.py
    ├── seed_data.py
    └── start_workers.py