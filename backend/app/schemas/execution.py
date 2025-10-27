from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import ConfigDict
from app.models.execution import ExecutionStatus


class ExecutionCreate(BaseModel):
    script_id: int = Field(..., description="The ID of the script to execute")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Parameters for the script execution")
    initiated_by: Optional[str] = Field(None, description="The user who initiated the execution")
    
class ExecutionResponse(BaseModel):
    id: int = Field(..., description="The unique identifier of the execution")
    script_id: int = Field(..., description="The ID of the executed script")
    status: ExecutionStatus = Field(..., description="The status of the execution")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Parameters used for the execution")
    output: Optional[str] = Field(None, description="The output of the execution")
    error : Optional[str] = Field(None, description="The error message if the execution failed")
    started_at: datetime = Field(..., description="The start timestamp of the execution")
    completed_at: Optional[datetime] = Field(None, description="The finish timestamp of the execution")
    executed_by: str = Field(None, description="The user who executed the script")
    created_at: datetime = Field(..., description="The creation timestamp of the execution record")
    result: Optional[Dict[str, Any]] = Field(None, description="The result of the execution")

    model_config = ConfigDict(from_attributes=True)