from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Single declarative base — all models inherit from this so their tables share one MetaData."""
    pass


# Extensions the schema depends on; our migration system runs CREATE EXTENSION for any that are missing
Base.metadata.info["required_extensions"] = ["vector"]
