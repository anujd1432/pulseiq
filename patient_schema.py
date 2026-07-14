from pydantic import BaseModel
from typing import Optional

class PatientCreate(BaseModel):
    full_name: str
    age: int
    gender: str
    contact: str
    address: Optional[str] = None
    blood_group: Optional[str] = None

class PatientUpdate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    blood_group: Optional[str] = None

class PatientOut(BaseModel):
    id: int
    full_name: str
    age: int
    gender: str
    contact: str
    address: Optional[str] = None
    blood_group: Optional[str] = None

    class Config:
        from_attributes = True
