
import asyncio
import json
from datetime import datetime, timezone
from sqlmodel import Session, create_engine
from src.database import ChatMessage, ChatSession, engine
from src.engines.broadcaster import global_broadcaster

async def send_test_message():
    session_id = "ebc1d936-2020-4af5-9638-ca762416dc34"
    content = "Hello Albin! I am Neo. Can you see this message?"
    
    # 1. Save to DB
    with Session(engine) as db:
        msg = ChatMessage(
            session_id=session_id,
            role="neo",
            content=content,
        )
        db.add(msg)
        db.commit()
    
    # 2. Broadcast
    await global_broadcaster.broadcast(session_id, {
        "type": "message",
        "role": "neo",
        "content": content,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    print("Broadcast sent.")

if __name__ == "__main__":
    asyncio.run(send_test_message())
