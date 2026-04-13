#!/usr/bin/env python3
# bot.py — Analysis-GPT Telegram Bot entry point
import asyncio
import os
import subprocess
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot_utils import is_authorized, split_chunks
from handlers.flow import flow_handler
from handlers.reversal import reversal_handler
from handlers.scalp import scalp_handler
from handlers.sl import sl_handler

load_dotenv()

BOT_TOKEN   = os.environ["BOT_TOKEN"]
ALLOWED_ID  = int(os.environ["ALLOWED_USER_ID"])

HELP_TEXT = """
Analysis-GPT Commands:

/flow SYMBOL [SYMBOL2 ...]
  Options flow smart money analysis
  Example: /flow ONGC RELIANCE

/reversal [SYMBOL ...]
  Reversal trade scanner
  No symbols = scans full 63-stock watchlist
  Example: /reversal ONGC TATASTEEL

/scalp SYMBOL [SYMBOL2 ...]
  Morning scalp analysis
  Example: /scalp ONGC

/status
  Check if Sensibull and yfinance APIs are reachable

/retry
  Re-run the last failed command

/sl <entry_price> [lot_size]
  Stop loss & profit target calculator (R:R 1:1, 1:1.5, 1:2)
  Lot size defaults to 6750 if not provided
  Example: /sl 2.00 6750  or  /sl 0.70

/update
  Pull latest code from GitHub and restart bot

/help
  Show this message
""".strip()


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id, ALLOWED_ID):
        return
    await update.message.reply_text(HELP_TEXT)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id, ALLOWED_ID):
        return
    import requests
    results = []
    try:
        r = requests.get(
            "https://api.sensibull.com/v1/instruments/ONGC",
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://web.sensibull.com/"},
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json().get("data", [])
            results.append(f"Sensibull API: ✅ OK ({len(data)} instruments for ONGC)")
        else:
            results.append(f"Sensibull API: ❌ {r.status_code}")
    except Exception as e:
        results.append(f"Sensibull API: ❌ {e}")
    await update.message.reply_text("\n".join(results))


async def cmd_retry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id, ALLOWED_ID):
        return
    last_error = context.bot_data.get("last_error")
    if not last_error:
        await update.message.reply_text("No failed command to retry.")
        return
    cmd, args = last_error
    context.args = args
    if cmd == "flow":
        await flow_handler(update, context, ALLOWED_ID)
    elif cmd == "reversal":
        await reversal_handler(update, context, ALLOWED_ID)
    elif cmd == "scalp":
        await scalp_handler(update, context, ALLOWED_ID)


async def cmd_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id, ALLOWED_ID):
        return
    await update.message.reply_text("⏳ Pulling latest code from GitHub...")
    try:
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            capture_output=True, text=True, timeout=60,
        )
        output = result.stdout.strip() or result.stderr.strip() or "No output"
        await update.message.reply_text(f"git pull output:\n{output}")
        await update.message.reply_text("✅ Updated. Restarting bot...")
        subprocess.Popen(["sudo", "systemctl", "restart", "analysis-gpt"])
    except Exception as e:
        await update.message.reply_text(f"❌ Update failed: {e}")


async def cmd_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await flow_handler(update, context, ALLOWED_ID)


async def cmd_reversal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reversal_handler(update, context, ALLOWED_ID)


async def cmd_scalp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await scalp_handler(update, context, ALLOWED_ID)


async def cmd_sl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await sl_handler(update, context, ALLOWED_ID)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("help",     cmd_help))
    app.add_handler(CommandHandler("start",    cmd_help))
    app.add_handler(CommandHandler("status",   cmd_status))
    app.add_handler(CommandHandler("retry",    cmd_retry))
    app.add_handler(CommandHandler("update",   cmd_update))
    app.add_handler(CommandHandler("flow",     cmd_flow))
    app.add_handler(CommandHandler("reversal", cmd_reversal))
    app.add_handler(CommandHandler("scalp",    cmd_scalp))
    app.add_handler(CommandHandler("sl",       cmd_sl))
    print("Bot started. Polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
