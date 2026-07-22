import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://pipeline:pipeline@localhost:5432/pipeline")
STORAGE_DIR = os.getenv("STORAGE_DIR", "./storage_data")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DUPLICATE_HASH_THRESHOLD = int(os.getenv("DUPLICATE_HASH_THRESHOLD", "5"))

# "rq"     -> real queue + separate worker process, talking over Redis.
#             Requires Redis and a worker service running (docker-compose default).
# "inline" -> no Redis, no separate worker. The same web process runs the job
#             in a background thread via FastAPI's BackgroundTasks. Lets the
#             whole app run as a single free-tier web service with no worker
#             or Redis add-on. See README trade-offs for what this gives up.
QUEUE_BACKEND = os.getenv("QUEUE_BACKEND", "rq")

# pool_pre_ping avoids using dead connections after DB restarts / idle timeouts
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()