"""
Enhanced Scripts API with validation, sanitization, and proper error handling
File: backend/app/api/routes/scripts.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.db.session import get_db
from app.models.script import Script, ScriptType, ScriptStatus
from app.models.secret import Secret
from app.models.user import User
from app.api.dependencies import get_current_user, require_operator
from app.schemas.script import ScriptCreate, ScriptResponse, ScriptUpdate
from app.core.security import InputValidator
from app.services.secret_service import SecretService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[ScriptResponse])
async def list_scripts(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    script_type: Optional[ScriptType] = None,
    status: Optional[ScriptStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List scripts with optional filtering and pagination
    
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records (default: 100, max: 1000)
    - **search**: Search in name and description
    - **script_type**: Filter by script type (bash, python, ansible, terraform)
    - **status**: Filter by status (draft, active, deprecated, etc.)
    """
    # Validate pagination
    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skip parameter must be non-negative"
        )
    
    if limit < 1 or limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 1000"
        )
    
    try:
        query = db.query(Script)
        
        # Apply filters
        if search:
            search_term = InputValidator.sanitize_string(search, max_length=100)
            if search_term:
                query = query.filter(
                    (Script.name.ilike(f"%{search_term}%")) |
                    (Script.description.ilike(f"%{search_term}%"))
                )
        
        if script_type:
            query = query.filter(Script.script_type == script_type)
        
        if status:
            query = query.filter(Script.status == status)
        
        # Order by most recently updated
        query = query.order_by(Script.updated_at.desc())
        
        # Get total count (for pagination metadata)
        total = query.count()
        
        # Apply pagination
        scripts = query.offset(skip).limit(limit).all()
        
        logger.info(
            f"Listed {len(scripts)} scripts (total: {total})",
            extra={"user": current_user.username, "filters": {
                "search": search, "type": script_type, "status": status
            }}
        )
        
        return scripts
        
    except Exception as e:
        logger.error(f"Error listing scripts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scripts"
        )


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(
    script_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific script by ID"""
    if script_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid script ID"
        )
    
    script = db.query(Script).filter(Script.id == script_id).first()
    
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Script with id {script_id} not found"
        )
    
    logger.info(
        f"Retrieved script {script_id}",
        extra={"script_id": script_id, "user": current_user.username}
    )
    
    return script


@router.post("/", response_model=ScriptResponse, status_code=status.HTTP_201_CREATED)
async def create_script(
    script_data: ScriptCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """
    Create a new script with validation
    
    Requires: operator role or higher
    """
    try:
        # Validate script content
        is_valid, errors = InputValidator.validate_script_content(
            script_data.content,
            script_data.script_type.value,
            max_size=1_000_000  # 1MB limit
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Script validation failed", "errors": errors}
            )
        
        # Sanitize string inputs
        script_data.name = InputValidator.sanitize_string(
            script_data.name, 
            max_length=255
        )
        
        if not script_data.name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Script name cannot be empty"
            )
        
        if script_data.description:
            script_data.description = InputValidator.sanitize_string(
                script_data.description,
                max_length=1000,
                allow_newlines=True
            )
        
        # Check for duplicate names
        existing = db.query(Script).filter(Script.name == script_data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Script with name '{script_data.name}' already exists"
            )
        
        # Validate JSON parameters structure
        if script_data.parameters:
            is_valid, error_msg = InputValidator.validate_json_structure(
                script_data.parameters,
                max_depth=10,
                max_keys=100
            )
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
        
        # Create script
        new_script = Script(
            **script_data.model_dump(),
            created_by=current_user.username,
            updated_by=current_user.username
        )
        
        db.add(new_script)
        db.commit()
        db.refresh(new_script)
        
        logger.info(
            f"Script created: {new_script.id} - {new_script.name}",
            extra={
                "script_id": new_script.id,
                "script_name": new_script.name,
                "user": current_user.username
            }
        )
        
        return new_script
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create script: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create script"
        )


@router.put("/{script_id}", response_model=ScriptResponse)
async def update_script(
    script_id: int,
    script_data: ScriptUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Update an existing script"""
    if script_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid script ID"
        )
    
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Script with id {script_id} not found"
        )
    
    try:
        update_data = script_data.model_dump(exclude_unset=True)
        
        # Validate content if provided
        if "content" in update_data:
            script_type = update_data.get("script_type", script.script_type)
            is_valid, errors = InputValidator.validate_script_content(
                update_data["content"],
                script_type.value if hasattr(script_type, 'value') else script_type
            )
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": "Script validation failed", "errors": errors}
                )
        
        # Sanitize name if provided
        if "name" in update_data:
            update_data["name"] = InputValidator.sanitize_string(
                update_data["name"],
                max_length=255
            )
            
            # Check for duplicate names (excluding current script)
            existing = db.query(Script).filter(
                Script.name == update_data["name"],
                Script.id != script_id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Script with name '{update_data['name']}' already exists"
                )
        
        # Sanitize description if provided
        if "description" in update_data and update_data["description"]:
            update_data["description"] = InputValidator.sanitize_string(
                update_data["description"],
                max_length=1000,
                allow_newlines=True
            )
        
        # Validate parameters if provided
        if "parameters" in update_data and update_data["parameters"]:
            is_valid, error_msg = InputValidator.validate_json_structure(
                update_data["parameters"]
            )
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
        
        # Update fields
        for field, value in update_data.items():
            setattr(script, field, value)
        
        script.updated_by = current_user.username
        
        db.commit()
        db.refresh(script)
        
        logger.info(
            f"Script updated: {script_id}",
            extra={"script_id": script_id, "user": current_user.username}
        )
        
        return script
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update script {script_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update script"
        )


@router.delete("/{script_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_script(
    script_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Delete a script by its ID"""
    if script_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid script ID"
        )
    
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Script with id {script_id} not found"
        )
    
    try:
        # Check if script has active executions
        from app.models.execution import Execution, ExecutionStatus
        active_executions = db.query(Execution).filter(
            Execution.script_id == script_id,
            Execution.status.in_([ExecutionStatus.PENDING, ExecutionStatus.RUNNING])
        ).count()
        
        if active_executions > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete script with {active_executions} active execution(s)"
            )
        
        script_name = script.name
        db.delete(script)
        db.commit()
        
        logger.info(
            f"Script deleted: {script_id} - {script_name}",
            extra={"script_id": script_id, "user": current_user.username}
        )
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete script {script_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete script"
        )


# ============================================================================
# SECRET MANAGEMENT FOR SCRIPTS
# ============================================================================

@router.post("/{script_id}/secrets/{secret_id}")
async def attach_secret_to_script(
    script_id: int,
    secret_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Attach a secret to a script"""
    if script_id < 1 or secret_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid script or secret ID"
        )
    
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    secret = db.query(Secret).filter(Secret.id == secret_id).first()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    try:
        # Check if already attached
        if secret in script.secrets.all():
            raise HTTPException(
                status_code=400,
                detail="Secret already attached to script"
            )
        
        script.secrets.append(secret)
        db.commit()
        
        # Log the attachment
        SecretService.log_access(
            db=db,
            secret=secret,
            action="attached_to_script",
            user_id=current_user.id,
            username=current_user.username,
            script_id=script_id
        )
        
        logger.info(
            f"Secret {secret_id} attached to script {script_id}",
            extra={"script_id": script_id, "secret_id": secret_id, "user": current_user.username}
        )
        
        return {"message": "Secret attached successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to attach secret: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to attach secret"
        )


@router.delete("/{script_id}/secrets/{secret_id}")
async def detach_secret_from_script(
    script_id: int,
    secret_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Detach a secret from a script"""
    if script_id < 1 or secret_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid script or secret ID"
        )
    
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    secret = db.query(Secret).filter(Secret.id == secret_id).first()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    try:
        if secret not in script.secrets.all():
            raise HTTPException(status_code=400, detail="Secret not attached to script")
        
        script.secrets.remove(secret)
        db.commit()
        
        logger.info(
            f"Secret {secret_id} detached from script {script_id}",
            extra={"script_id": script_id, "secret_id": secret_id, "user": current_user.username}
        )
        
        return {"message": "Secret detached successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to detach secret: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to detach secret"
        )


@router.get("/{script_id}/secrets")
async def get_script_secrets(
    script_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all secrets attached to a script (without values)"""
    if script_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid script ID"
        )
    
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    secrets = [
        {
            "id": secret.id,
            "name": secret.name,
            "description": secret.description,
            "created_at": secret.created_at
        }
        for secret in script.secrets.all()
    ]
    
    return secrets