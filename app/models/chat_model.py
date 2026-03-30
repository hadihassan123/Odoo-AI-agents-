from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.database import Base


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, default="anonymous")
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    model = Column(String, nullable=False)
    mode = Column(String, nullable=False, default="general")
    session_id = Column(String, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
