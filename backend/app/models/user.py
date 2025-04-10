import uuid
from datetime import datetime

from pydantic import EmailStr
from sqlmodel import Field, SQLModel
from sqlalchemy import BigInteger, Column


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    user_name: str | None = Field(default=None, max_length=255)
    level: int = Field(default=1) # 0 for admin , 1 for junior, # 2... senior
    

    # We have this field because we crawl from other platform and does want to duplicate user.
    origin_user_id: int | None = Field(default=None, sa_type=BigInteger, unique=True)

    is_banned: bool = False
    last_login: datetime | None = Field(default=datetime.now())
    created_at: datetime = Field(default=datetime.now())
    updated_at: datetime = Field(default=datetime.now())


# Properties to receive via API on creation
class UserCreate(SQLModel):
    email: EmailStr
    password: str
    user_name: str

class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    user_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
    user_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: int = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    hashed_password: str


class IdentityValidator(SQLModel, table=True):
    __tablename__ = 'identity_validator'
    id: int = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    user_id: int = Field(nullable=False, foreign_key="user.id", sa_type=BigInteger)
    phone_number: int = Field(nullable=False, unique=True)
    is_validated: bool = Field(default=False, nullable=False)
    otp: str = Field(nullable=False)
    created_at: datetime = Field(default=datetime.now)
    updated_at: datetime = Field(default=datetime.now)

# Properties to return via API, id is always required
class UserPublic(SQLModel):
    user_name: str
    level: int
    is_banned: bool
    last_login: datetime | None = Field(default=datetime.now())
    id: int


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int

# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)
