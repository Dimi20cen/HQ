from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, create_engine
)
from sqlalchemy import Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

from pathlib import Path
import os
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("CONTROLLER_DB_PATH", str(BASE_DIR / "tools.db"))

# SQLite engine
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

# Session factory
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Base class for models
Base = declarative_base()


# -------------------------------------------------------------
# Models
# -------------------------------------------------------------
class Tool(Base):
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    process_path = Column(String)     # where to launch the tool
    port = Column(Integer)            # where the tool serves its API
    pid = Column(Integer, nullable=True)
    has_widget = Column(Boolean, default=False)
    status = Column(String, default="stopped")
    last_heartbeat = Column(DateTime, nullable=True)
    registered_at = Column(DateTime, default=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "process_path": self.process_path,
            "port": self.port,
            "pid": self.pid,
            "status": self.status,
            "has_widget": self.has_widget,
            "last_heartbeat": (
                self.last_heartbeat.isoformat() if self.last_heartbeat else None
            ),
            "registered_at": self.registered_at.isoformat(),
        }


# -------------------------------------------------------------
# Database initialization
# -------------------------------------------------------------
def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


# -------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------
def get_session():
    """Get a new SQLAlchemy session."""
    return SessionLocal()


def add_tool(name, process_path, port, has_widget=False):
    """Register a new tool in the database."""
    session = get_session()
    tool = Tool(
        name=name,
        process_path=process_path,
        port=port,
        has_widget=has_widget,
    )
    session.add(tool)
    session.commit()
    session.refresh(tool)
    session.close()
    return tool


def get_tool_by_name(name):
    session = get_session()
    tool = session.query(Tool).filter(Tool.name == name).first()
    session.close()
    return tool


def update_tool_pid(name, pid):
    session = get_session()
    tool = session.query(Tool).filter(Tool.name == name).first()
    if tool:
        tool.pid = pid
        tool.status = "running" if pid else "stopped"
        session.commit()
    session.close()


def update_tool_status(name, status):
    session = get_session()
    tool = session.query(Tool).filter(Tool.name == name).first()
    if tool:
        tool.status = status
        session.commit()
    session.close()


def update_tool_metadata(name, process_path=None, port=None, has_widget=None):
    session = get_session()
    tool = session.query(Tool).filter(Tool.name == name).first()
    if tool:
        if process_path is not None:
            tool.process_path = process_path
        if port is not None:
            tool.port = port
        if has_widget is not None:
            tool.has_widget = has_widget
        session.commit()
    session.close()


def list_tools():
    session = get_session()
    tools = session.query(Tool).all()
    session.close()
    return [t.as_dict() for t in tools]
