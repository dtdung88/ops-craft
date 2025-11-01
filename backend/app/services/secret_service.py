from sqlalchemy.orm import Session
from typing import Optional, Dict
from datetime import datetime

from app.models.secret import Secret
from app.models.secret_audit import SecretAuditLog
from app.services.encryption_service import encryption_service


class SecretService:
    """Service for managing secrets with audit logging"""
    
    @staticmethod
    def log_access(
        db: Session,
        secret: Secret,
        action: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        execution_id: Optional[int] = None,
        script_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log secret access for audit trail"""
        audit_log = SecretAuditLog(
            secret_id=secret.id,
            secret_name=secret.name,
            action=action,
            accessed_by=user_id,
            accessed_by_username=username or "system",
            execution_id=execution_id,
            script_id=script_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(audit_log)
        
        # Update last accessed timestamp
        if action in ['accessed', 'injected']:
            secret.last_accessed_at = datetime.utcnow()
        
        db.commit()
    
    @staticmethod
    def get_secret_value(
        db: Session,
        secret_name: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        execution_id: Optional[int] = None,
        script_id: Optional[int] = None
    ) -> Optional[str]:
        """
        Get decrypted secret value and log access
        
        Args:
            db: Database session
            secret_name: Name of the secret
            user_id: ID of user accessing secret
            username: Username accessing secret
            execution_id: Execution ID if called during script execution
            script_id: Script ID if called during script execution
            
        Returns:
            Decrypted secret value or None if not found
        """
        secret = db.query(Secret).filter(Secret.name == secret_name).first()
        
        if not secret:
            return None
        
        # Decrypt value
        decrypted_value = encryption_service.decrypt(secret.encrypted_value)
        
        # Log access
        SecretService.log_access(
            db=db,
            secret=secret,
            action='injected' if execution_id else 'accessed',
            user_id=user_id,
            username=username,
            execution_id=execution_id,
            script_id=script_id
        )
        
        return decrypted_value
    
    @staticmethod
    def get_secrets_for_script(
        db: Session,
        script_id: int,
        execution_id: Optional[int] = None,
        user_id: Optional[int] = None,
        username: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Get all secrets associated with a script
        
        Returns:
            Dictionary of secret_name: decrypted_value
        """
        from app.models.script import Script
        
        script = db.query(Script).filter(Script.id == script_id).first()
        if not script:
            return {}
        
        secrets_dict = {}
        
        for secret in script.secrets:
            decrypted_value = SecretService.get_secret_value(
                db=db,
                secret_name=secret.name,
                user_id=user_id,
                username=username,
                execution_id=execution_id,
                script_id=script_id
            )
            
            if decrypted_value:
                secrets_dict[secret.name] = decrypted_value
        
        return secrets_dict
    
    @staticmethod
    def get_audit_logs(
        db: Session,
        secret_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 100
    ):
        """Get audit logs for secrets"""
        query = db.query(SecretAuditLog)
        
        if secret_id:
            query = query.filter(SecretAuditLog.secret_id == secret_id)
        
        if user_id:
            query = query.filter(SecretAuditLog.accessed_by == user_id)
        
        return query.order_by(SecretAuditLog.timestamp.desc()).limit(limit).all()


# Global instance
secret_service = SecretService()