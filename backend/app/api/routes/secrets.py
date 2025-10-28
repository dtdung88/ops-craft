from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.api.dependencies import get_db, require_operator, require_admin
from app.models.user import User
from app.models.secret import Secret
from app.core.encryption import encryption_service
from app.services.SecretService import SecretService
from app.schemas.secret import SecretCreate, SecretUpdate, SecretResponse, SecretWithValue

router = APIRouter()


@router.get("", response_model=List[SecretResponse])
async def list_secrets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """List all secrets (without values)"""
    secrets = db.query(Secret).offset(skip).limit(limit).all()
    return secrets


@router.get("/{secret_id}", response_model=SecretWithValue)
async def get_secret(
    secret_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Get secret with decrypted value"""
    secret = db.query(Secret).filter(Secret.id == secret_id).first()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    # Update last accessed time
    secret.last_accessed_at = datetime.utcnow()
    db.commit()
    
    # Decrypt value using encryption service
    try:
        decrypted_value = encryption_service.decrypt(secret.encrypted_value)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to decrypt secret: {str(e)}")
    
    return {
        **secret.__dict__,
        "value": decrypted_value
    }


@router.post("", response_model=SecretResponse, status_code=status.HTTP_201_CREATED)
async def create_secret(
    secret_data: SecretCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Create new secret"""
    # Check if secret name already exists
    existing = db.query(Secret).filter(Secret.name == secret_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Secret with this name already exists")
    
    # Encrypt the value using encryption service
    try:
        encrypted_value = encryption_service.encrypt(secret_data.value)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to encrypt secret: {str(e)}")
    
    new_secret = Secret(
        name=secret_data.name,
        encrypted_value=encrypted_value,
        description=secret_data.description,
        created_by=current_user.id
    )
    
    db.add(new_secret)
    db.commit()
    db.refresh(new_secret)
    return new_secret


@router.put("/{secret_id}", response_model=SecretResponse)
async def update_secret(
    secret_id: int,
    secret_data: SecretUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Update secret"""
    secret = db.query(Secret).filter(Secret.id == secret_id).first()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    # Update value if provided
    if secret_data.value is not None:
        try:
            secret.encrypted_value = encryption_service.encrypt(secret_data.value)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to encrypt secret: {str(e)}")
    
    # Update description if provided
    if secret_data.description is not None:
        secret.description = secret_data.description
    
    db.commit()
    db.refresh(secret)
    return secret


@router.delete("/{secret_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_secret(
    secret_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Delete secret"""
    secret = db.query(Secret).filter(Secret.id == secret_id).first()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    # Check if secret is being used by any scripts
    from app.models.secret import script_secrets
    usage_count = db.query(script_secrets).filter(
        script_secrets.c.secret_id == secret_id
    ).count()
    
    if usage_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete secret: it is being used by {usage_count} script(s)"
        )
    
    db.delete(secret)
    db.commit()
    return None


@router.get("/name/{secret_name}", response_model=SecretWithValue)
async def get_secret_by_name(
    secret_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Get secret by name with decrypted value"""
    secret = db.query(Secret).filter(Secret.name == secret_name).first()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    # Update last accessed time
    secret.last_accessed_at = datetime.utcnow()
    db.commit()
    
    # Decrypt value using encryption service
    try:
        decrypted_value = encryption_service.decrypt(secret.encrypted_value)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to decrypt secret: {str(e)}")
    
    return {
        **secret.__dict__,
        "value": decrypted_value
    }

@router.get("/audit-logs")
async def get_all_audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get all secret audit logs (Admin only)"""
    logs = SecretService.get_audit_logs(db=db, limit=limit)
    
    return [
        {
            "id": log.id,
            "secret_name": log.secret_name,
            "action": log.action,
            "accessed_by": log.accessed_by_username,
            "execution_id": log.execution_id,
            "script_id": log.script_id,
            "timestamp": log.timestamp
        }
        for log in logs
    ]

@router.get("/{secret_id}/audit-logs")
async def get_secret_audit_logs(
    secret_id: int,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Get audit logs for a specific secret"""
    secret = db.query(Secret).filter(Secret.id == secret_id).first()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")

    logs = SecretService.get_audit_logs(db=db, secret_id=secret_id, limit=limit)

    return [
        {
            "id": log.id,
            "action": log.action,
            "accessed_by": log.accessed_by_username,
            "execution_id": log.execution_id,
            "script_id": log.script_id,
            "timestamp": log.timestamp
        }
        for log in logs
    ]
