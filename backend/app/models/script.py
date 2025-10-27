from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from app.db.base import Base
import enum

class ScriptType(str, enum.Enum):
    BASH = "bash"
    PYTHON = "python"
    POWERSHELL = "powershell"
    ANSIBLE = "ansible"
    TERRAFORM = "terraform"

class ScriptStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"
    
class Script(Base):
    __tablename__ = "scripts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    script_type = Column(SQLEnum(ScriptType), nullable=False)
    content = Column(Text, nullable=False)
    parameters = Column(JSON, nullable=True)
    status = Column(SQLEnum(ScriptStatus), default=ScriptStatus.ACTIVE)
    version = Column(String(50), nullable=False, default="1.0.0")
    tags = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(255), nullable=False, default="system")
    updated_by = Column(String(255), nullable=False, default="system")
