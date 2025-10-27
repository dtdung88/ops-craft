from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import ConfigDict
from app.models.script import ScriptType, ScriptStatus

class ScriptBase(BaseModel):
    name: str = Field(..., description="The name of the script", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="A brief description of the script")
    script_type: ScriptType = Field(..., description="The type of the script")
    content: str = Field(..., description="The content of the script")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Parameters for the script execution")
    tags: Optional[List[str]] = Field(None, description="Tags associated with the script")
    version: Optional[str] = Field("1.0.0", description="Version of the script")
    
class ScriptCreate(ScriptBase):
    pass

class ScriptUpdate(BaseModel):
    name: Optional[str] = Field(None, description="The name of the script", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="A brief description of the script")
    content: Optional[str] = Field(None, description="The content of the script")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Parameters for the script execution")
    status: Optional[ScriptStatus] = Field(None, description="The status of the script")
    tags: Optional[List[str]] = Field(None, description="Tags associated with the script")
    version: Optional[str] = Field(None, description="Version of the script")
    
class ScriptResponse(ScriptBase):
    id: int = Field(..., description="The unique identifier of the script")
    status: ScriptStatus = Field(..., description="The status of the script")
    created_at: datetime = Field(..., description="The creation timestamp of the script")
    updated_at: datetime = Field(..., description="The last update timestamp of the script")
    created_by: Optional[str] = Field(None, description="The user who created the script")
    updated_by: Optional[str] = Field(None, description="The user who last updated the script")

    model_config = ConfigDict(from_attributes=True)
