# handlers/reversal.py — /reversal command handler
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from bot_utils import split_chunks, is_authorized
from config import DEFAULT_SYMBOLS
from core.reversal_scan import run_scan


async def reversal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, allowed_id: int) -> None:
    """Handle /reversal [SYMBOL1 SYMBOL2 ...]"""
    user_id = update.effective_user.id
    if not is_authorized(user_id, allowed_id):
        return

    args = context.args
    symbols = [s.upper() for s in args] if args else DEFAULT_SYMBOLS
    label = f"{len(symbols)} stocks" if not args else ", ".join(symbols)
    await update.message.reply_text(f"⏳ Scanning {label} for reversal opportunities...")

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_scan, symbols)
    except Exception as e:
        await update.message.reply_text(f"❌ Reversal scan failed: {e}\nSend /retry to try again.")
        context.bot_data["last_error"] = ("reversal", list(args))
        return

    for chunk in split_chunks(result):
        await update.message.reply_text(f"```\n{chunk}\n```", parse_mode="Markdown")

    context.bot_data["last_command"] = ("reversal", list(args))
