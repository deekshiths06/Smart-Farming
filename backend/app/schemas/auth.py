from pydantic import BaseModel, EmailStr, Field as PydanticField
from typing import Optional


class UserBase(BaseModel):
    name: str = PydanticField(min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = PydanticField(default=None, max_length=20)


class UserCreate(UserBase):
    password: str = PydanticField(min_length=6, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserInDB(UserBase):
    id: int
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
