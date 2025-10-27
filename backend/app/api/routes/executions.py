from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.models.script import Script
from app.models.user import User
from app.models.execution import Execution, ExecutionStatus
from app.schemas.execution import ExecutionCreate, ExecutionResponse
from app.tasks.executor import execute_script_task

router = APIRouter()

@router.get("", response_model=List[ExecutionResponse])
async def list_executions(
    skip: int = 0,
    limit: int = 100,
    script_id: int = None,
    db: Session = Depends(get_db)
) -> List[Execution]:
    """List script executions with optional filtering by script ID.

    Args:
        skip (int): Number of records to skip for pagination.
        limit (int): Maximum number of records to return.
        script_id (int, optional): Filter executions by this script ID.
        db (Session): Database session dependency.

    Returns:
        List[Execution]: List of script executions.
    """
    query = db.query(Execution)
    if script_id is not None:
        query = query.filter(Execution.script_id == script_id)

    executions = query.order_by(Execution.created_at.desc()).offset(skip).limit(limit).all()
    return executions

@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: int,
    db: Session = Depends(get_db)
) -> Execution:
    """Retrieve a specific script execution by its ID.

    Args:
        execution_id (int): The ID of the execution to retrieve.
        db (Session): Database session dependency.

    Returns:
        Execution: The requested script execution.

    Raises:
        HTTPException: If the execution is not found.
    """
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution with id {execution_id} not found"
        )
    return execution

@router.post("", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED)
async def create_execution(
    execution_in: ExecutionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Execution:
    """Create a new script execution and trigger its asynchronous execution.

    Args:
        execution_in (ExecutionCreate): Data for the new execution.
        db (Session): Database session dependency.

    Returns:
        Execution: The created script execution.

    Raises:
        HTTPException: If the associated script is not found.
    """
    script = db.query(Script).filter(Script.id == execution_in.script_id).first()
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Script with id {execution_in.script_id} not found"
        )

    new_execution = Execution(
        script_id=execution_in.script_id,
        parameters=execution_in.parameters,
        status=ExecutionStatus.PENDING,
        executed_by=current_user.username
    )
    db.add(new_execution)
    db.commit()
    db.refresh(new_execution)

    # Trigger asynchronous execution
    execute_script_task.delay(new_execution.id)

    return new_execution

@router.post("/{execution_id}/cancel", response_model=ExecutionResponse)
async def cancel_execution(
    execution_id: int,
    db: Session = Depends(get_db)
) -> Execution:
    """Cancel a running script execution.

    Args:
        execution_id (int): The ID of the execution to cancel.
        db (Session): Database session dependency.

    Returns:
        Execution: The updated script execution.

    Raises:
        HTTPException: If the execution is not found or cannot be canceled.
    """
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution with id {execution_id} not found"
        )

    if execution.status not in [ExecutionStatus.RUNNING, ExecutionStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel execution with status {execution.status}"
        )

    execution.status = ExecutionStatus.CANCELLED
    db.commit()
    db.refresh(execution)

    return execution
