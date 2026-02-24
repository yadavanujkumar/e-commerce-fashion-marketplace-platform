# src/core/services/user_service.py

import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr, constr
from .models import User  # Assuming User is a SQLAlchemy model
from .schemas import UserCreate, UserUpdate, UserResponse  # Pydantic schemas
from .repositories import UserRepository  # Repository pattern for data access

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repository = UserRepository(db)

    def hash_password(self, password: str) -> str:
        """Hash a password for storing."""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a stored password against one provided by user."""
        return pwd_context.verify(plain_password, hashed_password)

    def create_user(self, user_create: UserCreate) -> UserResponse:
        """Create a new user."""
        if self.user_repository.get_user_by_email(user_create.email):
            logger.warning(f"User with email {user_create.email} already exists.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")

        hashed_password = self.hash_password(user_create.password)
        user = User(email=user_create.email, password=hashed_password, full_name=user_create.full_name)
        self.user_repository.create_user(user)
        logger.info(f"User created with email: {user_create.email}")
        return UserResponse.from_orm(user)

    def get_user(self, user_id: int) -> UserResponse:
        """Retrieve a user by ID."""
        user = self.user_repository.get_user_by_id(user_id)
        if not user:
            logger.error(f"User with ID {user_id} not found.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return UserResponse.from_orm(user)

    def update_user(self, user_id: int, user_update: UserUpdate) -> UserResponse:
        """Update user information."""
        user = self.user_repository.get_user_by_id(user_id)
        if not user:
            logger.error(f"User with ID {user_id} not found for update.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        if user_update.password:
            user_update.password = self.hash_password(user_update.password)

        updated_user = self.user_repository.update_user(user_id, user_update)
        logger.info(f"User with ID {user_id} updated.")
        return UserResponse.from_orm(updated_user)

    def delete_user(self, user_id: int) -> Dict[str, str]:
        """Delete a user by ID."""
        user = self.user_repository.get_user_by_id(user_id)
        if not user:
            logger.error(f"User with ID {user_id} not found for deletion.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        self.user_repository.delete_user(user_id)
        logger.info(f"User with ID {user_id} deleted.")
        return {"detail": "User deleted successfully."}

# Pydantic models for user creation and update
class UserCreate(BaseModel):
    email: EmailStr
    password: constr(min_length=8)
    full_name: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[constr(min_length=8)] = None
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str

    class Config:
        orm_mode = True