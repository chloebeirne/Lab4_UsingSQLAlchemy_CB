# app/schemas.py 
from typing import Annotated 
from pydantic import BaseModel, EmailStr, Field, StringConstraints, ConfigDict 
 
NameStr = Annotated[str, StringConstraints(min_length=2, max_length=50)] 
StudentId = Annotated[str, StringConstraints(pattern=r"^S\d{7}$")] 
 
class UserCreate(BaseModel): 
    name: NameStr 
    email: EmailStr 
    age: int = Field(gt=18) 
    student_id: StudentId 
 
class UserRead(BaseModel): 
    id: int 
    name: NameStr 
    email: EmailStr 
    age: int 
    student_id: StudentId 
 
    model_config = ConfigDict(from_attributes=True)




