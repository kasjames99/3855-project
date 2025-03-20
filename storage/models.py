from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy import Integer, String, DateTime, func, BigInteger

class Base(DeclarativeBase):
    pass

class temperatureEvent(Base):
    __tablename__ = "temperature"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id = mapped_column(String(50), nullable=False)
    temperature = mapped_column(Integer, nullable=False)
    timestamp = mapped_column(DateTime, nullable=False)
    event_type = mapped_column(String(50), nullable=False)
    trace_id = mapped_column(BigInteger, nullable=False)

    def __init__(self, device_id: str, temperature: int, trace_id: int, timestamp, event_type="temperature"):
        self.device_id = device_id
        self.temperature = temperature
        self.timestamp = timestamp
        self.event_type = event_type
        self.trace_id = trace_id

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "temperature": self.temperature,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "trace_id": self.trace_id
        }

class motionEvent(Base):
    __tablename__ = "motion"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id = mapped_column(String(50), nullable=False)
    room = mapped_column(String(50), nullable=False)
    timestamp = mapped_column(DateTime, nullable=False)
    motion_intensity = mapped_column(Integer, nullable=False)
    trace_id = mapped_column(BigInteger, nullable=False)

    def __init__(self, device_id: str, room: str, trace_id: int, timestamp, motion_intensity=0):
        self.device_id = device_id
        self.room = room
        self.timestamp = timestamp
        self.motion_intensity = motion_intensity
        self.trace_id = trace_id
    
    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "room": self.room,
            "timestamp": self.timestamp.isoformat(),
            "motion_intensity": self.motion_intensity,
            "trace_id": self.trace_id
        }