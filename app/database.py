import os

from sqlmodel import Session, SQLModel, create_engine

DATA_DIR = os.getenv("DATA_DIR", "./data")
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR}/labelprinter.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
