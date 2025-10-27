from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class SecretCreate(BaseModel):
    name: str
    value: str
    description: Optional[str] = None


class SecretUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None


class SecretResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_by: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    last_accessed_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


class SecretWithValue(SecretResponse):
    value: str