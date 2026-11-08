from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    original_text = Column(Text)
    analysis = Column(Text)
    knowledge_point = Column(String(255))
    created_at = Column(TIMESTAMP, server_default=func.now())

class Flashcard(Base):
    __tablename__ = "flashcards"
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    similar_question = Column(Text)
    is_mastered = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

class Mistake(Base):
    __tablename__ = "mistakes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, default=1)
    question = Column(Text, nullable=False)
    analysis = Column(Text, nullable=False)
    knowledge_point = Column(String(255))
    created_at = Column(TIMESTAMP, server_default=func.now())