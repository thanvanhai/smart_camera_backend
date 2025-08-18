# app/models.py
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

# Bảng Camera
class Camera(Base):
    __tablename__ = "cam_cameras"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    topic = Column(String, unique=True, nullable=False)
    location = Column(String, nullable=True)

# Bảng Person
class Person(Base):
    __tablename__ = "cam_persons"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

# Bảng Embedding của Person
class PersonEmbedding(Base):
    __tablename__ = "cam_embeddings"
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("cam_persons.id"))
    vector = Column(String, nullable=False)  # có thể lưu JSON string
    person = relationship("Person", backref="embeddings")

# Bảng Event Nhận diện
class PersonEvent(Base):
    __tablename__ = "cam_person_events"
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("cam_persons.id"))
    camera_id = Column(Integer, ForeignKey("cam_cameras.id"))
    score = Column(Float)
    passed = Column(Boolean, default=False)
    bbox = Column(String)  # lưu dạng JSON [x1, y1, x2, y2]
    timestamp = Column(DateTime, default=datetime.utcnow)

    person = relationship("Person", backref="events")
    camera = relationship("Camera", backref="events")
