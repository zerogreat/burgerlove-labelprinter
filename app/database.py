import json
import os

from sqlmodel import Session, SQLModel, create_engine, select

from .models import FoodItem

DATA_DIR = os.getenv("DATA_DIR", "./data")
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR}/labelprinter.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SEED_FILE = os.path.join(os.path.dirname(__file__), "seed_items.json")


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _seed_food_items()


def _seed_food_items() -> None:
    """Pre-populates food_items from seed_items.json on a brand new
    install (an empty table) — e.g. a fresh clone on the Raspberry Pi.
    Never touches an install that already has items."""
    with Session(engine) as session:
        if session.exec(select(FoodItem)).first() is not None:
            return
        if not os.path.exists(SEED_FILE):
            return
        with open(SEED_FILE) as f:
            items = json.load(f)
        for entry in items:
            session.add(FoodItem(name=entry["name"], shelf_life_days=entry.get("shelf_life_days")))
        session.commit()


def get_session():
    with Session(engine) as session:
        yield session
