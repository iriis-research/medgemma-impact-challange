"""
AI Chat API Routes
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import User, Conversation, Message, MessageCategory
from app.security.auth import get_current_user
from app.llm.medgemma_client import medgemma

router = APIRouter()

# Request/Response Models
class MessageCreate(BaseModel):
    content: str
    conversation_id: Optional[int] = None

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    category: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: int
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []
    
    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    message: MessageResponse
    ai_response: MessageResponse
    conversation_id: int
    is_emergency: bool

@router.post("/send", response_model=ChatResponse)
@router.post("/send/", response_model=ChatResponse, include_in_schema=False)
async def send_message(
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message and get AI response."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info(f"📨 CHAT REQUEST RECEIVED")
    logger.info(f"   Message: {message_data.content[:100]}...")
    logger.info(f"   Conversation ID: {message_data.conversation_id}")
    logger.info("=" * 60)
    
    user_id = current_user.id
    logger.info(f"   Using User ID: {user_id}")
    
    # Get or create conversation
    if message_data.conversation_id:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.id == message_data.conversation_id)
            .where(Conversation.user_id == user_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        # Create new conversation
        conversation = Conversation(
            user_id=user_id,
            title=message_data.content[:50] + "..." if len(message_data.content) > 50 else message_data.content
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
    
    # Get conversation history
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in result.scalars().all()
    ]
    
    # Get AI response
    logger.info("🤖 Calling MedGemma model for AI response...")
    try:
        ai_result = await medgemma.chat(message_data.content, history)
        logger.info(f"✅ AI response generated (length: {len(ai_result.get('response', ''))})")
        logger.info(f"   Category: {ai_result.get('category')}")
        logger.info(f"   Is Emergency: {ai_result.get('is_emergency')}")
    except Exception as e:
        logger.error(f"❌ Error generating AI response: {e}", exc_info=True)
        raise
    
    # Determine category
    category_map = {
        "symptom": MessageCategory.SYMPTOM,
        "medication": MessageCategory.MEDICATION,
        "report": MessageCategory.REPORT,
        "emergency": MessageCategory.EMERGENCY,
        "general": MessageCategory.GENERAL
    }
    category = category_map.get(ai_result.get("category"), MessageCategory.GENERAL)
    
    # Save user message
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=message_data.content,
        category=category
    )
    db.add(user_message)
    
    # Save AI response
    ai_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=ai_result["response"],
        category=category
    )
    db.add(ai_message)
    
    # Update conversation timestamp
    conversation.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(user_message)
    await db.refresh(ai_message)
    
    logger.info(f"✅ Chat response ready - returning to frontend")
    logger.info("=" * 60)
    
    return ChatResponse(
        message=MessageResponse(
            id=user_message.id,
            role=user_message.role,
            content=user_message.content,
            category=category.value if category else None,
            created_at=user_message.created_at
        ),
        ai_response=MessageResponse(
            id=ai_message.id,
            role=ai_message.role,
            content=ai_message.content,
            category=category.value if category else None,
            created_at=ai_message.created_at
        ),
        conversation_id=conversation.id,
        is_emergency=ai_result.get("is_emergency", False)
    )

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all conversations for current user."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().all()
    
    response = []
    for conv in conversations:
        # Get messages for each conversation
        msg_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at)
        )
        messages = msg_result.scalars().all()
        
        response.append(ConversationResponse(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            messages=[
                MessageResponse(
                    id=msg.id,
                    role=msg.role,
                    content=msg.content,
                    category=msg.category.value if msg.category else None,
                    created_at=msg.created_at
                )
                for msg in messages
            ]
        ))
    
    return response

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific conversation with all messages."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.user_id == current_user.id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get messages
    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()
    
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                category=msg.category.value if msg.category else None,
                created_at=msg.created_at
            )
            for msg in messages
        ]
    )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a conversation."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.user_id == current_user.id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    await db.delete(conversation)
    await db.commit()
    
    return {"message": "Conversation deleted successfully"}

