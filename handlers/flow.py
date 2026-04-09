# handlers/flow.py — /flow command handler
from telegram import Update
from telegram.ext import ContextTypes

from bot_utils import split_chunks, retry_call, is_authorized
from config import SENSIBULL_MAX_RETRIES, SENSIBULL_RETRY_BASE_DELAY
from core.options_flow import fetch_symbol_data, format_symbol_block, format_summary_table


async def flow_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, allowed_id: int) -> None:
    """Handle /flow SYMBOL [SYMBOL2 ...]"""
    user_id = update.effective_user.id
    if not is_authorized(user_id, allowed_id):
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /flow SYMBOL [SYMBOL2 ...]\nExample: /flow ONGC RELIANCE")
        return

    symbols = [s.upper() for s in args]
    await update.message.reply_text(f"⏳ Fetching flow data for: {', '.join(symbols)}...")

    summary_results = []
    error_symbols = []
    output_parts = []

    for symbol in symbols:
        try:
            data = retry_call(
                lambda s=symbol: fetch_symbol_data(s),
                max_retries=SENSIBULL_MAX_RETRIES,
                base_delay=SENSIBULL_RETRY_BASE_DELAY,
            )
            block, dirn, conf = format_symbol_block(data)
            output_parts.append(block)
            summary_results.append((symbol, dirn, conf))
        except Exception as e:
            error_symbols.append(symbol)
            output_parts.append(f"❌ {symbol}: failed after {SENSIBULL_MAX_RETRIES} retries — {e}")

    summary = format_summary_table(summary_results)
    if summary:
        output_parts.append(summary)

    full_output = "\n\n".join(output_parts)

    for chunk in split_chunks(full_output):
        await update.message.reply_text(f"```\n{chunk}\n```", parse_mode="Markdown")

    # Store last command for /retry
    context.bot_data["last_command"] = ("flow", args)
    if error_symbols:
        context.bot_data["last_error"] = ("flow", args)
        await update.message.reply_text(
            f"⚠️ Failed: {', '.join(error_symbols)}. Send /retry to try again."
        )
