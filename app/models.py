from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    level = Column(String, nullable=True) # midschool, highschool, undergrad, others
    objectives = Column(Text, nullable=True)
    onboarding_completed = Column(Boolean, default=False)

    goals = relationship("Goal", back_populates="owner")

class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    pdf_path = Column(String, nullable=True)
    vector_store_path = Column(String, nullable=True)
    status = Column(String, default="pending") # pending, processing, completed, failed
    status_message = Column(String, nullable=True)
    completed = Column(Boolean, default=False)
    chapters_data = Column(Text, nullable=True)
    processing_logs = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="goals")
    messages = relationship("ChatMessage", back_populates="goal", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="goal", cascade="all, delete-orphan")
    flashcard_sets = relationship("FlashcardSet", back_populates="goal", cascade="all, delete-orphan")
    topic_descriptions = relationship("TopicDescription", back_populates="goal", cascade="all, delete-orphan")
    video_suggestions = relationship("VideoSuggestion", back_populates="goal", cascade="all, delete-orphan")
    visuals = relationship("Visual", back_populates="goal", cascade="all, delete-orphan")
    sections = relationship("Section", back_populates="goal", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"))
    chapter_title = Column(String, nullable=True) # Which chapter this message belongs to
    role = Column(String) # "user" or "ai"
    msg_type = Column(String, default="text") # "text", "quiz", "flashcard"
    related_id = Column(Integer, nullable=True) # ID of the quiz or flashcard set
    content = Column(Text)
    suggestions = Column(Text, nullable=True) # JSON string of suggestions
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    goal = relationship("Goal", back_populates="messages")

class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"))
    title = Column(String)
    questions = Column(Text) # JSON string of questions
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    goal = relationship("Goal", back_populates="quizzes")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    score = Column(Integer, default=0)
    total = Column(Integer, default=0)
    answers = Column(Text) # JSON string of user answers, dict mapping question index to answer
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    quiz = relationship("Quiz", back_populates="attempts")
    user = relationship("User")

class FlashcardSet(Base):
    __tablename__ = "flashcard_sets"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"))
    title = Column(String)
    cards = Column(Text) # JSON string of cards
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    goal = relationship("Goal", back_populates="flashcard_sets")

class TopicDescription(Base):
    __tablename__ = "topic_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"))
    topic_name = Column(String, index=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    goal = relationship("Goal", back_populates="topic_descriptions")

class VideoSuggestion(Base):
    __tablename__ = "video_suggestions"
    
    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"))
    term = Column(String)
    video_data = Column(Text) # JSON list of videos
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    goal = relationship("Goal", back_populates="video_suggestions")

class Visual(Base):
    __tablename__ = "visuals"
    
    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"))
    term = Column(String)
    html_content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    goal = relationship("Goal", back_populates="visuals")

class Section(Base):
    __tablename__ = "sections"
    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"))
    title = Column(String)
    # content = Column(Text, nullable=True)
    
    goal = relationship("Goal", back_populates="sections")
    subsections = relationship("Subsection", back_populates="section", cascade="all, delete-orphan")

class Subsection(Base):
    __tablename__ = "subsections"
    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("sections.id"))
    title = Column(String)
    # content = Column(Text)
    
    section = relationship("Section", back_populates="subsections")
