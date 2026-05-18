from pydantic import BaseModel
from datetime import datetime

class UserCreate(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    level: str | None = None
    objectives: str | None = None
    onboarding_completed: bool

    class Config:
        from_attributes = True

class TopicDescriptionResponse(BaseModel):
    id: int
    goal_id: int
    topic_name: str
    description: str
    created_at: datetime

    class Config:
        from_attributes = True

class GoalCreate(BaseModel):
    title: str
    description: str | None = None

class GoalUpdate(BaseModel):
    title: str | None = None
    description: str | None = None

class GoalResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    pdf_path: str | None = None
    vector_store_path: str | None = None
    status: str
    status_message: str | None = None
    completed: bool
    chapters_data: str | None = None
    processing_logs: str | None = None
    owner_id: int

    class Config:
        from_attributes = True

class ChatMessageResponse(BaseModel):
    id: int
    role: str
    msg_type: str
    related_id: int | None = None
    content: str
    suggestions: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str

class OnboardingUpdate(BaseModel):
    level: str
    objectives: str

class QuizAttemptBase(BaseModel):
    score: int
    total: int
    answers: str
    completed: bool

class QuizAttemptResponse(QuizAttemptBase):
    id: int
    quiz_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class QuizBase(BaseModel):
    title: str
    questions: str

class QuizResponse(QuizBase):
    id: int
    goal_id: int
    created_at: datetime
    attempts: list[QuizAttemptResponse] = []

    class Config:
        from_attributes = True

class FlashcardSetBase(BaseModel):
    title: str
    cards: str

class FlashcardSetResponse(FlashcardSetBase):
    id: int
    goal_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class VideoSuggestionBase(BaseModel):
    term: str
    video_data: str

class VideoSuggestionResponse(VideoSuggestionBase):
    id: int
    goal_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class VisualResponse(BaseModel):
    id: int
    goal_id: int
    term: str
    html_content: str
    created_at: datetime

    class Config:
        from_attributes = True
