from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


# Association table for many-to-many relationship between scripts and secrets
script_secrets = Table(
    'script_secrets',
    Base.metadata,
    Column('script_id', Integer, ForeignKey('scripts.id'), primary_key=True),
    Column('secret_id', Integer, ForeignKey('secrets.id'), primary_key=True)
)


class Secret(Base):
    __tablename__ = "secrets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    encrypted_value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)