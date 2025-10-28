from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.db.base_class import Base


class SecretAuditLog(Base):
    __tablename__ = "secret_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    secret_id = Column(Integer, ForeignKey('secrets.id', ondelete='CASCADE'), nullable=False, index=True)
    secret_name = Column(String(255), nullable=False)
    action = Column(String(50), nullable=False)  # 'accessed', 'created', 'updated', 'deleted', 'injected'
    accessed_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    accessed_by_username = Column(String(255), nullable=True)
    execution_id = Column(Integer, ForeignKey('executions.id'), nullable=True)
    script_id = Column(Integer, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<SecretAuditLog {self.secret_name} - {self.action} by {self.accessed_by_username}>"