"""create cameras table

Revision ID: 123456789abc
Revises: 
Create Date: 2025-08-21 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '123456789abc'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Xóa bảng cũ nếu tồn tại
    op.execute("DROP TABLE IF EXISTS cameras CASCADE;")
    
    # Tạo bảng cameras mới
    op.create_table(
        'cameras',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('camera_id', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('camera_type', sa.String(50), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('location', sa.String(200), nullable=True),
        sa.Column('zone', sa.String(50), nullable=True),
        sa.Column('floor', sa.String(20), nullable=True),
        sa.Column('building', sa.String(100), nullable=True),
        sa.Column('settings', postgresql.JSONB, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('is_enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('config', postgresql.JSONB, nullable=True),
        sa.Column('stream_url', sa.String(500), nullable=True),
        sa.Column('resolution', sa.String(20), nullable=True),
        sa.Column('fps', sa.Integer, nullable=True),
        sa.Column('enable_detection', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('enable_tracking', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('enable_face_recognition', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('detection_threshold', postgresql.JSONB, nullable=True),
        sa.Column('tracking_config', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table('cameras')
