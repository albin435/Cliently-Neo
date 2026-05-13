import os
import json
import logging
import asyncio
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from sqlmodel import select

from .orchestrator import handle_chat, get_active_task, approve_task, reject_task
from .memory import memory_manager
from ..database import get_session, ChatSession, Task, TaskPhase
from .openclaw import get_openclaw, RuntimeStatus

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.app = None
        self.allowed_users = [] # We can restrict to specific user IDs if provided
        
        allowed = os.environ.get("TELEGRAM_ALLOWED_USERS")
        if allowed:
            self.allowed_users = [int(u.strip()) for u in allowed.split(",")]

    async def _ensure_session(self, chat_id: str):
        """Map a Telegram chat ID to an internal session, creating one if needed."""
        with get_session() as db:
            # First, try to find a session already linked to this telegram_chat_id
            stmt = select(ChatSession).where(ChatSession.telegram_chat_id == chat_id)
            session = db.exec(stmt).first()
            
            if not session:
                # Create a new session specifically for this Telegram chat
                session = ChatSession(
                    title="Telegram Remote",
                    model="gemini-2.5-flash",
                    telegram_chat_id=chat_id
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                logger.info(f"Linked new internal session {session.id} to Telegram chat {chat_id}")
            
            return session.id

    def is_allowed(self, user_id: int) -> bool:
        if not self.allowed_users:
            return True # If not set, allow anyone (maybe dangerous, but good for testing)
        return user_id in self.allowed_users

    async def broadcast(self, session_id: str, data: dict):
        """Broadcast updates back to Telegram if the session is linked."""
        if not self.app:
            return
            
        target_chat_id = None
        
        with get_session() as db:
            session = db.get(ChatSession, session_id)
            if session and session.telegram_chat_id:
                target_chat_id = session.telegram_chat_id
            else:
                # Fallback: Check if session_id itself is a chat_id (direct)
                stmt = select(ChatSession).where(ChatSession.telegram_chat_id == session_id)
                session = db.exec(stmt).first()
                if session:
                    target_chat_id = session.telegram_chat_id

        if not target_chat_id:
            return

        try:
            # 1. Message Sync (Bidirectional)
            if data.get("type") == "message":
                role = data.get("role")
                content = data.get("content")
                
                # Check source metadata
                meta_json = data.get("metadata_json")
                source = None
                if meta_json:
                    try:
                        meta = json.loads(meta_json)
                        source = meta.get("source")
                    except: pass

                # Sync if it's Neo, OR if it's Albin typing from the Mac App (source != telegram)
                should_send = (role == "neo") or (role == "albin" and source != "telegram")
                
                if should_send and content:
                    prefix = "🤖 *Neo:* " if role == "neo" else "👤 *Albin:* "
                    await self.app.bot.send_message(
                        chat_id=target_chat_id, 
                        text=f"{prefix}{content}", 
                        parse_mode="Markdown"
                    )
            
            # 2. Phase Updates
            elif data.get("type") == "phase":
                phase = data.get("phase")
                emoji = {
                    "planning": "📝", "awaiting_approval": "⚖️", "delegating": "🤝",
                    "executing": "⚙️", "reviewing": "🧐", "complete": "✅", "failed": "❌"
                }.get(phase, "ℹ️")
                
                await self.app.bot.send_message(
                    chat_id=target_chat_id, 
                    text=f"{emoji} *System State:* {phase.replace('_', ' ').capitalize()}",
                    parse_mode="Markdown"
                )

            # 3. Approval Requests
            elif data.get("type") == "approval_request":
                task_id = data.get("task_id")
                plan = data.get("plan", "No plan details.")
                
                keyboard = [[
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_{task_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_{task_id}")
                ]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await self.app.bot.send_message(
                    chat_id=target_chat_id, 
                    text=f"⚠️ *CTO Approval Required*\n\n{plan}", 
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

        except Exception as e:
            logger.error(f"Telegram broadcast error: {e}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return
            
        user_id = update.effective_user.id
        if not self.is_allowed(user_id):
            await update.message.reply_text("🚫 Unauthorized access.")
            return

        chat_id = str(update.effective_chat.id)
        text = update.message.text
        internal_session_id = await self._ensure_session(chat_id)
        
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        try:
            await handle_chat(
                session_id=internal_session_id,
                prompt=text,
                model="gemini-2.5-flash",
                broadcast=self.broadcast,
                metadata={"source": "telegram"}
            )
        except Exception as e:
            logger.error(f"Telegram handle_message error: {e}")
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/status - Get system health and git status."""
        user_id = update.effective_user.id
        if not self.is_allowed(user_id): return

        from .context import get_git_branch, get_git_status
        branch = get_git_branch()
        git_status = get_git_status()
        
        openclaw = get_openclaw()
        oc_health = await openclaw.check_health()
        
        status_msg = (
            "🖥️ *Neo System Status*\n\n"
            f"📍 *Branch:* `{branch}`\n"
            f"🛠️ *Runtime (OpenClaw):* `{oc_health.status.value}`\n"
            f"📦 *Active Tasks:* `{oc_health.active_tasks}`\n\n"
            "*Git Status:*\n"
            f"```\n{git_status}\n```"
        )
        await update.message.reply_text(status_msg, parse_mode="Markdown")

    async def cmd_memory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/memory <query> - Search Neo's architectural memory."""
        user_id = update.effective_user.id
        if not self.is_allowed(user_id): return

        query = " ".join(context.args)
        if not query:
            await update.message.reply_text("Usage: `/memory <search query>`", parse_mode="Markdown")
            return

        results = memory_manager.query_memory(query, top_k=5)
        if not results:
            await update.message.reply_text("No matching architectural nodes found.")
            return

        response = f"🧠 *Memory Search Results for:* `{query}`\n\n"
        for i, res in enumerate(results):
            content = res['content']
            node_type = res['node_type'].replace('_', ' ').capitalize()
            response += f"{i+1}. *[{node_type}]*\n{content}\n\n"
        
        await update.message.reply_text(response, parse_mode="Markdown")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        if not self.is_allowed(user_id): return
            
        data = query.data
        if data.startswith("approve_"):
            task_id = data.replace("approve_", "")
            if approve_task(task_id):
                await query.edit_message_text(f"✅ *Task Approved:* `{task_id}`. Initiating execution...", parse_mode="Markdown")
            else:
                await query.edit_message_text("❌ Failed to approve task.")
                
        elif data.startswith("reject_"):
            task_id = data.replace("reject_", "")
            if reject_task(task_id):
                await query.edit_message_text(f"🛑 *Task Rejected:* `{task_id}`.", parse_mode="Markdown")
            else:
                await query.edit_message_text("❌ Failed to reject task.")

    async def start_bot(self):
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not set. Telegram integration disabled.")
            return

        self.app = ApplicationBuilder().token(self.token).build()
        
        # Handlers
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("memory", self.cmd_memory))
        self.app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_message))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        logger.info("Starting Telegram bot...")
        try:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            logger.info("Telegram bot active.")
        except Exception as e:
            logger.error(f"Telegram start error: {e}")
            self.app = None

    async def stop_bot(self):
        if self.app:
            try:
                if self.app.updater and self.app.updater.running:
                    await self.app.updater.stop()
                if self.app.running:
                    await self.app.stop()
                    await self.app.shutdown()
            except RuntimeError as e:
                logger.warning(f"Error during bot shutdown (likely already stopped): {e}")

telegram_bot = TelegramBot()
