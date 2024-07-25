from .base import Base
from .session import engine


def init_db():
    from . import models  # Import models here to ensure they are registered correctly

    Base.metadata.create_all(bind=engine)
