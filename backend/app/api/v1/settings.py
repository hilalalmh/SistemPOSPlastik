from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.database import get_db
from app.models.store import Location, StoreSetting
from app.models.user import User
from app.permissions import SETTINGS_UPDATE
from app.schemas.settings import (
    LocationCreate,
    LocationOut,
    StoreSettingOut,
    StoreSettingUpdate,
)
from app.services import audit

router = APIRouter(tags=["settings"])


def get_or_create_settings(db: Session) -> StoreSetting:
    setting = db.execute(select(StoreSetting).limit(1)).scalar_one_or_none()
    if setting is None:
        setting = StoreSetting(store_name="Toko Plastik")
        db.add(setting)
        db.flush()
    return setting


@router.get("/settings", response_model=StoreSettingOut)
def get_settings(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    setting = get_or_create_settings(db)
    db.commit()
    return setting


@router.patch("/settings", response_model=StoreSettingOut)
def update_settings(
    payload: StoreSettingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(SETTINGS_UPDATE)),
):
    setting = get_or_create_settings(db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(setting, key, value)
    audit.log_action(
        db,
        action="settings.update",
        entity_type="store_settings",
        entity_id=setting.id,
        actor_id=user.id,
        meta=payload.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(setting)
    return setting


@router.get("/locations", response_model=list[LocationOut])
def list_locations(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.execute(select(Location).order_by(Location.name)).scalars().all()


@router.post("/locations", response_model=LocationOut, status_code=201)
def create_location(
    payload: LocationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(SETTINGS_UPDATE)),
):
    location = Location(**payload.model_dump())
    db.add(location)
    audit.log_action(db, action="location.create", entity_type="location", actor_id=user.id)
    db.commit()
    db.refresh(location)
    return location
