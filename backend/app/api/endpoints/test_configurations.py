from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import schemas, models # TODO: Adjust imports
from app.database import get_db
# from app.core.security import get_current_active_user # TODO

router = APIRouter()

@router.post("/", response_model=schemas.TestConfiguration, status_code=status.HTTP_201_CREATED)
async def create_test_configuration(
    config_in: schemas.TestConfigurationCreate,
    db: Session = Depends(get_db),
    # current_user: models.User = Depends(get_current_active_user) # TODO
):
    # Validate connection_profile_id belongs to the user
    # conn_profile = db.query(models.ConnectionProfile).filter(models.ConnectionProfile.id == config_in.connection_profile_id, models.ConnectionProfile.owner_id == current_user.id).first()
    conn_profile = db.query(models.ConnectionProfile).filter(models.ConnectionProfile.id == config_in.connection_profile_id, models.ConnectionProfile.owner_id == 1).first() # Placeholder
    if not conn_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection profile not found or access denied")

    db_config = models.TestConfiguration(**config_in.dict(), owner_id=1) # Placeholder current_user.id
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config

@router.get("/", response_model=List[schemas.TestConfiguration])
async def read_test_configurations(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    # current_user: models.User = Depends(get_current_active_user) # TODO
):
    # configs = db.query(models.TestConfiguration).filter(models.TestConfiguration.owner_id == current_user.id).offset(skip).limit(limit).all()
    configs = db.query(models.TestConfiguration).filter(models.TestConfiguration.owner_id == 1).offset(skip).limit(limit).all() # Placeholder
    return configs

@router.get("/{config_id}", response_model=schemas.TestConfiguration)
async def read_test_configuration(
    config_id: int,
    db: Session = Depends(get_db),
    # current_user: models.User = Depends(get_current_active_user) # TODO
):
    # config = db.query(models.TestConfiguration).filter(models.TestConfiguration.id == config_id, models.TestConfiguration.owner_id == current_user.id).first()
    config = db.query(models.TestConfiguration).filter(models.TestConfiguration.id == config_id, models.TestConfiguration.owner_id == 1).first() # Placeholder
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test configuration not found")
    return config

@router.put("/{config_id}", response_model=schemas.TestConfiguration)
async def update_test_configuration(
    config_id: int,
    config_in: schemas.TestConfigurationUpdate,
    db: Session = Depends(get_db),
    # current_user: models.User = Depends(get_current_active_user) # TODO
):
    # config = db.query(models.TestConfiguration).filter(models.TestConfiguration.id == config_id, models.TestConfiguration.owner_id == current_user.id).first()
    config = db.query(models.TestConfiguration).filter(models.TestConfiguration.id == config_id, models.TestConfiguration.owner_id == 1).first() # Placeholder
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test configuration not found")

    if config_in.connection_profile_id:
        # conn_profile = db.query(models.ConnectionProfile).filter(models.ConnectionProfile.id == config_in.connection_profile_id, models.ConnectionProfile.owner_id == current_user.id).first()
        conn_profile = db.query(models.ConnectionProfile).filter(models.ConnectionProfile.id == config_in.connection_profile_id, models.ConnectionProfile.owner_id == 1).first() # Placeholder
        if not conn_profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection profile not found or access denied for update")

    update_data = config_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    db.add(config)
    db.commit()
    db.refresh(config)
    return config

@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_configuration(
    config_id: int,
    db: Session = Depends(get_db),
    # current_user: models.User = Depends(get_current_active_user) # TODO
):
    # config = db.query(models.TestConfiguration).filter(models.TestConfiguration.id == config_id, models.TestConfiguration.owner_id == current_user.id).first()
    config = db.query(models.TestConfiguration).filter(models.TestConfiguration.id == config_id, models.TestConfiguration.owner_id == 1).first() # Placeholder
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test configuration not found")
    db.delete(config)
    db.commit()
    return None
