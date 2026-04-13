# handlers/sl.py — /sl command handler (Stop Loss & R:R Calculator)
from telegram import Update
from telegram.ext import ContextTypes

from bot_utils import is_authorized

DEFAULT_LOT_SIZE = 6750


def _calculate(entry: float, lot: int) -> dict:
    stop   = round(entry * 0.70, 2)
    t11    = round(entry * 1.30, 2)
    t115   = round(entry * 1.45, 2)
    t12    = round(entry * 1.60, 2)
    cost   = round(entry * lot, 2)
    sl_rs  = round((entry - stop) * lot, 2)
    p11    = round((t11  - entry) * lot, 2)
    p115   = round((t115 - entry) * lot, 2)
    p12    = round((t12  - entry) * lot, 2)
    return dict(
        stop=stop, t11=t11, t115=t115, t12=t12,
        cost=cost, sl_rs=sl_rs, p11=p11, p115=p115, p12=p12,
    )


def _fmt(entry: float, lot: int, r: dict) -> str:
    return (
        f"📊 Stop Loss Calculator\n"
        f"{'─'*30}\n"
        f"Entry : ₹{entry:.2f}  |  Lot: {lot:,}  |  Cost: ₹{r['cost']:,.0f}\n"
        f"{'─'*30}\n"
        f"🛑 Stop Loss      ₹{r['stop']:.2f}  →  Loss  ₹{r['sl_rs']:,.0f}\n"
        f"{'─'*30}\n"
        f"✅ 1:1   Target   ₹{r['t11']:.2f}  →  Profit ₹{r['p11']:,.0f}\n"
        f"🎯 1:1.5 Target   ₹{r['t115']:.2f}  →  Profit ₹{r['p115']:,.0f}\n"
        f"🚀 1:2   Target   ₹{r['t12']:.2f}  →  Profit ₹{r['p12']:,.0f}\n"
        f"{'─'*30}\n"
        f"Win rate needed → 1:1 >50%  |  1:1.5 >40%  |  1:2 >33%"
    )


async def sl_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, allowed_id: int) -> None:
    """Handle /sl <entry_price> [lot_size]"""
    user_id = update.effective_user.id
    if not is_authorized(user_id, allowed_id):
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: /sl <entry_price> [lot_size]\n"
            "Example: /sl 2.00 6750\n"
            "Example: /sl 0.70"
        )
        return

    try:
        entry = float(args[0])
        lot   = int(args[1]) if len(args) > 1 else DEFAULT_LOT_SIZE
    except ValueError:
        await update.message.reply_text("❌ Invalid input. Use: /sl 2.00 6750")
        return

    if entry <= 0 or lot <= 0:
        await update.message.reply_text("❌ Entry price and lot size must be positive.")
        return

    r = _calculate(entry, lot)
    await update.message.reply_text(f"```\n{_fmt(entry, lot, r)}\n```", parse_mode="Markdown")
