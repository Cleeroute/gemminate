from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from . import models, schemas, auth
from .database import get_db

router = APIRouter()

from fastapi import Request

@router.post("/api/goals/{goal_id}/chat/stop")
async def stop_chat_generation(
    goal_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    active_generators = getattr(request.app.state, 'active_generators', {})
    if goal_id in active_generators:
        active_generators[goal_id].set()
        
    active_tasks = getattr(request.app.state, 'active_tasks', {})
    if goal_id in active_tasks:
        task = active_tasks[goal_id]
        if not task.done():
            task.cancel()
            
    # Find the last AI message for this goal that is empty, and update it
    last_msg = db.query(models.ChatMessage).filter(
        models.ChatMessage.goal_id == goal_id,
        models.ChatMessage.role == "ai"
    ).order_by(models.ChatMessage.id.desc()).first()

    if last_msg and last_msg.content == "":
        last_msg.content = '<span class="text-red-500 italic text-sm">Generation stopped by user.</span>'
        db.commit()

    return {"message": "Generation stopped"}
