# handlers/scalp.py — /scalp command handler
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from bot_utils import split_chunks, is_authorized
from core.morning_scalp import run_scalp


async def scalp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, allowed_id: int) -> None:
    """Handle /scalp SYMBOL [SYMBOL2 ...]"""
    user_id = update.effective_user.id
    if not is_authorized(user_id, allowed_id):
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /scalp SYMBOL [SYMBOL2 ...]\nExample: /scalp ONGC")
        return

    symbols = [s.upper() for s in args]
    await update.message.reply_text(f"⏳ Running scalp scan for: {', '.join(symbols)}...")

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_scalp, symbols, "morning")
    except Exception as e:
        await update.message.reply_text(f"❌ Scalp scan failed: {e}\nSend /retry to try again.")
        context.bot_data["last_error"] = ("scalp", list(args))
        return

    for chunk in split_chunks(result):
        await update.message.reply_text(f"```\n{chunk}\n```", parse_mode="Markdown")

    context.bot_data["last_command"] = ("scalp", list(args))
