from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import schemas, models # TODO: Adjust imports
from app.database import get_db
# from app.core.security import get_current_active_user # TODO

router = APIRouter()

@router.post("/", response_model=schemas.ConnectionProfile, status_code=status.HTTP_201_CREATED)
async def create_connection_profile(
    profile_in: schemas.ConnectionProfileCreate,
    db: Session = Depends(get_db),
    # current_user: models.User = Depends(get_current_active_user) # TODO
):
    # TODO: Encrypt password before saving
    # hashed_password = encrypt_password(profile_in.password)
    # db_profile = models.ConnectionProfile(**profile_in.dict(exclude={"password"}), owner_id=current_user.id, password_encrypted=hashed_password)
    # For now, storing password as is (highly insecure, placeholder)
    db_profile = models.ConnectionProfile(
        **profile_in.dict(exclude={"password"}),
        owner_id=1, # Placeholder for current_user.id
        password_encrypted=f"encrypted_{profile_in.password}" # Placeholder
    )
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile

@router.get("/", response_model=List[schemas.ConnectionProfile])
async def read_connection_profiles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    # current_user: models.User = Depends(get_current_active_user) # TODO
):
    # profiles = db.query(models.ConnectionProfile).filter(models.ConnectionProfile.owner_id == current_user.id).offset(skip).limit(limit).all()
    profiles = db.query(models.ConnectionProfile).filter(models.ConnectionProfile.owner_id == 1).offset(skip).limit(limit).all() # Placeholder
    return profiles

@router.get("/{profile_id}", response_model=schemas.ConnectionProfile)
async def read_connection_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    # current_user: models.User = Depends(get_current_active_user) # TODO
):
    profile = db.query(models.ConnectionProfile).filter(models.ConnectionProfile.id == profile_id, models.ConnectionProfile.owner_id == 1).first() # Placeholder current_user.id
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection profile not found")
    return profile

@router.put("/{profile_id}", response_model=schemas.ConnectionProfile)
async def update_connection_profile(
    profile_id: int,
    profile_in: schemas.ConnectionProfileUpdate,
    db: Session = Depends(get_db),
    # current_user: models.User = Depends(get_current_active_user) # TODO
):
    profile = db.query(models.ConnectionProfile).filter(models.ConnectionProfile.id == profile_id, models.ConnectionProfile.owner_id == 1).first() # Placeholder
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection profile not found")

    update_data = profile_in.dict(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        # TODO: Encrypt password
        # update_data["password_encrypted"] = encrypt_password(update_data["password"])
        update_data["password_encrypted"] = f"encrypted_{update_data['password']}" # Placeholder
        del update_data["password"]

    for field, value in update_data.items():
        setattr(profile, field, value)

    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile

@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    # current_user: models.User = Depends(get_current_active_user) # TODO
):
    profile = db.query(models.ConnectionProfile).filter(models.ConnectionProfile.id == profile_id, models.ConnectionProfile.owner_id == 1).first() # Placeholder
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection profile not found")
    db.delete(profile)
    db.commit()
    return None
