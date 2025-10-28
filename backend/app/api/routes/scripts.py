from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.script import Script
from app.models.secret import Secret
from app.models.user import User
from app.api.dependencies import get_db, require_operator, get_current_user
from app.services.SecretService import SecretService
from app.schemas.script import ScriptCreate, ScriptResponse, ScriptUpdate

router = APIRouter()

@router.get("/", response_model=List[ScriptResponse])
def list_scripts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all scripts.

    Args:
        db (Session): Database session dependency.

    Returns:
        List[Script]: List of scripts.
    """
    scripts = db.query(Script).offset(skip).limit(limit).all()
    return scripts

@router.get("/{script_id}", response_model=ScriptResponse)
def get_script(script_id: int, db: Session = Depends(get_db)) -> Script:
    """Retrieve a specific script by its ID.

    Args:
        script_id (int): The ID of the script to retrieve.
        db (Session): Database session dependency.

    Returns:
        Script: The requested script.

    Raises:
        HTTPException: If the script is not found.
    """
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Script with id {script_id} not found"
        )
    return script

@router.post("/", response_model=ScriptResponse, status_code=status.HTTP_201_CREATED)
def create_script(script_in: ScriptCreate, db: Session = Depends(get_db)) -> Script:
    """Create a new script.

    Args:
        script_in (ScriptCreate): The script data to create.
        db (Session): Database session dependency.

    Returns:
        Script: The created script.
    """
    existing_script = db.query(Script).filter(Script.name == script_in.name).first()
    
    if existing_script:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Script with name '{script_in.name}' already exists"
        )
    
    new_script = Script(**script_in.model_dump())
    db.add(new_script)
    db.commit()
    db.refresh(new_script)
    return new_script

@router.put("/{script_id}", response_model=ScriptResponse)
def update_script(
    script_id: int,
    script_in: ScriptUpdate,
    db: Session = Depends(get_db)
) -> Script:
    """Update an existing script.

    Args:
        script_id (int): The ID of the script to update.
        script_in (ScriptUpdate): The updated script data.
        db (Session): Database session dependency.

    Returns:
        Script: The updated script.

    Raises:
        HTTPException: If the script is not found.
    """
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Script with id {script_id} not found"
        )

    update_data = script_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(script, field, value)
    
    db.commit()
    db.refresh(script)
    return script

@router.delete("/{script_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_script(
    script_id: int,
    db: Session = Depends(get_db)
) -> None:
    """Delete a script by its ID.

    Args:
        script_id (int): The ID of the script to delete.
        db (Session): Database session dependency.

    Raises:
        HTTPException: If the script is not found.
    """
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Script with id {script_id} not found"
        )

    db.delete(script)
    db.commit()
    return None

@router.post("/{script_id}/secrets/{secret_id}")
async def attach_secret_to_script(
    script_id: int,
    secret_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Attach a secret to a script"""
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    secret = db.query(Secret).filter(Secret.id == secret_id).first()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    # Check if already attached
    if secret in script.secrets.all():
        raise HTTPException(status_code=400, detail="Secret already attached to script")
    
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
    
    return {"message": "Secret attached successfully"}


@router.delete("/{script_id}/secrets/{secret_id}")
async def detach_secret_from_script(
    script_id: int,
    secret_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Detach a secret from a script"""
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    secret = db.query(Secret).filter(Secret.id == secret_id).first()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    if secret not in script.secrets.all():
        raise HTTPException(status_code=400, detail="Secret not attached to script")
    
    script.secrets.remove(secret)
    db.commit()
    
    return {"message": "Secret detached successfully"}


@router.get("/{script_id}/secrets")
async def get_script_secrets(
    script_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all secrets attached to a script"""
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