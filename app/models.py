from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class FoodItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    shelf_life_days: Optional[int] = None
    photo_path: Optional[str] = None


class PrintLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    food_name: str
    initials: str
    prepped_date: date
    expiration_date: Optional[date] = None
    printed_at: datetime = Field(default_factory=datetime.utcnow)
