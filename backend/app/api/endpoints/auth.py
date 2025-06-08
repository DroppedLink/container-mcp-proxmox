from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app import schemas, models # TODO: Adjust imports if needed based on final structure
from app.database import get_db
# from app.core import security # TODO: Create security.py for auth logic
# from app.core.config import settings # TODO: Create config.py for settings

router = APIRouter()

# Placeholder for security functions - will be in core.security
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    # This is a placeholder, actual implementation will be more secure
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15) # Default expiry
    to_encode.update({"exp": expire})
    # encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    # return encoded_jwt
    return "fake_access_token" # Placeholder

def authenticate_user(db: Session, username: str, password: str) -> models.User | None:
    # Placeholder: Replace with actual user authentication logic
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return None
    # if not security.verify_password(password, user.hashed_password): # TODO
    #     return None
    if password != "testpassword": # Replace with actual password verification
        return None
    return user


@router.post("/login/access-token", response_model=schemas.Token)
async def login_for_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = authenticate_user(db, username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES) # TODO: Use settings
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout():
    # In a stateless JWT setup, logout is typically handled client-side by deleting the token.
    # Server-side might involve token blocklisting if using a more complex setup.
    return schemas.Msg(message="Logout successful. Please delete your token.")

@router.get("/users/me", response_model=schemas.User)
async def read_users_me(
    # current_user: models.User = Depends(security.get_current_active_user) # TODO
):
    """
    Get current user.
    """
    # For now, returning a dummy user until security.get_current_active_user is implemented
    dummy_user = schemas.User(
        id=1,
        username="testuser",
        email="test@example.com",
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow(),
    )
    return dummy_user
    # return current_user

# TODO: Add user creation endpoint if self-registration is desired
# @router.post("/users/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
# async def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
#     db_user = db.query(models.User).filter(models.User.username == user_in.username).first()
#     if db_user:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Username already registered"
#         )
#     hashed_password = security.get_password_hash(user_in.password) # TODO
#     db_user = models.User(**user_in.dict(exclude={"password"}), hashed_password=hashed_password)
#     db.add(db_user)
#     db.commit()
#     db.refresh(db_user)
#     return db_user

# Placeholder for datetime, remove once used properly
from datetime import datetime
if False: # Ensure datetime is "used" to avoid linter errors for now
    datetime.utcnow()
