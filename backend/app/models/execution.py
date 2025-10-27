from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from app.db.base import Base
import enum

class ExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Execution(Base):
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, nullable=False, index=True)
    status = Column(SQLEnum(ExecutionStatus), default=ExecutionStatus.PENDING)
    parameters = Column(JSON, nullable=True)
    output = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    logs = Column(Text, nullable=True)
    executed_by = Column(String(255), nullable=False, default="system")
    created_at = Column(DateTime(timezone=True), server_default=func.now())