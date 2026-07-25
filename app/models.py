from sqlalchemy import BigInteger, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class RecoveryEvent(Base):
    __tablename__ = "recovery_events"

    id = Column(Integer, primary_key=True, index=True)
    container_name = Column(String, index=True, nullable=False)
    status = Column(String, nullable=False)  # crash_loop | oom_killed
    reason = Column(String, nullable=True)
    restart_count = Column(Integer, nullable=False)
    action = Column(String, nullable=False)  # restart | rollback
    image_before = Column(String, nullable=True)
    image_after = Column(String, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(BigInteger, nullable=True)
