# Analysis-GPT — Design Spec
**Date:** 2026-04-08
**Status:** Approved

---

## Overview

Analysis-GPT is a personal Telegram bot deployed on an AWS EC2 t3.micro instance that provides on-demand Indian stock/index options analysis. It unifies three existing analysis engines — options flow, reversal scanner, and morning scalp — into a single always-on service accessible from Telegram. No AI API key is required; all analysis is purely algorithmic.

---

## Project Structure

```
Analysis-GPT/
├── bot.py                  # Main entry point — Telegram bot + command handlers
├── handlers/
│   ├── flow.py             # /flow command handler
│   ├── reversal.py         # /reversal command handler
│   └── scalp.py            # /scalp command handler
├── core/                   # Shared analysis engines (refactored from existing skills)
│   ├── options_flow.py     # Options flow smart money scanner
│   ├── flow_signals.py     # Flow signal logic (volume spike, OI buildup, PCR, IV)
│   ├── equity_flow.py      # Equity flow analysis
│   ├── reversal_scan.py    # Reversal trade finder
│   └── morning_scalp.py    # Morning/EOD scalp scanner
├── config.py               # All shared config: budgets, thresholds, default watchlist
├── requirements.txt        # All Python dependencies
├── .env                    # BOT_TOKEN, ALLOWED_USER_ID (git-ignored, EC2 only)
├── .gitignore
└── deploy/
    └── setup.sh            # One-shot EC2 first-time setup script
```

---

## Commands

| Command | Example | Description |
|---|---|---|
| `/flow SYMBOL(S)` | `/flow ONGC` or `/flow ONGC RELIANCE` | Options flow analysis on one or more stocks |
| `/reversal` | `/reversal` | Reversal scan across full 63-stock default watchlist |
| `/reversal SYMBOL(S)` | `/reversal ONGC TATASTEEL` | Reversal scan on specified stocks only |
| `/scalp SYMBOL` | `/scalp ONGC` | Morning scalp analysis on a single stock |
| `/retry` | `/retry` | Re-runs the last failed command |
| `/status` | `/status` | Pings Sensibull API + yfinance, reports health |
| `/update` | `/update` | Pulls latest code from GitHub and restarts the bot |
| `/help` | `/help` | Lists all available commands |

---

## Bot Behaviour

### Security
- Every incoming message is checked against `ALLOWED_USER_ID` from `.env`
- Messages from any other user are silently ignored — no response, no error

### Long-running scans
- Full reversal scan (63 stocks) takes 2–4 minutes
- Bot sends an immediate acknowledgement: `⏳ Scanning 63 stocks, please wait...`
- Analysis runs in the background (asyncio), result sent when complete

### Message splitting
- Telegram caps messages at 4096 characters
- Long reports are automatically split into multiple sequential messages

### Error handling
- Every Sensibull API call retries up to 3 times with exponential backoff (1s → 2s → 4s)
- On total failure: `❌ ONGC failed after 3 retries. Reply /retry to try again.`
- `/retry` re-runs the last failed command without retyping
- `/status` performs a live health check of Sensibull + yfinance APIs

### Output format
- Same as current terminal/email output — full plain text, all data included
- No AI summarisation (can be added in a future phase)

---

## Technical Stack

| Component | Choice | Reason |
|---|---|---|
| Bot framework | `python-telegram-bot` v20 (async) | Mature, async-native, polling support |
| Analysis | `scipy`, `yfinance`, `requests` | Existing dependencies, no change |
| Data source | Sensibull public API + yfinance | Free, no API key required |
| Python version | 3.11 | Stable, available on Ubuntu 22.04 |

**No AI/LLM API key required.** All analysis is algorithmic (Black-Scholes IV, OI ratios, volume spikes, rule-based scoring).

---

## AWS Deployment

### Instance
- **Type:** EC2 `t3.micro` (1 vCPU, 1GB RAM)
- **OS:** Ubuntu 22.04 LTS
- **Cost:** ~$8/month on-demand, ~$5/month reserved
- **Free tier:** Eligible for first 12 months on a new AWS account

### Service management
The bot runs as a `systemd` service named `analysis-gpt`:
- Auto-starts on EC2 boot
- Auto-restarts on crash
- Logs via `journalctl -u analysis-gpt`

### Networking
- Bot uses Telegram **polling** (outbound calls only)
- No inbound ports needed
- No HTTPS certificate or domain name required

### First-time setup
`deploy/setup.sh` handles the full EC2 setup in one run:
1. Install Python 3.11, pip, git
2. Clone GitHub repo
3. Install requirements
4. Create `.env` with tokens
5. Register and start `analysis-gpt` systemd service

---

## Update Workflow

### Standard update (from terminal)
```
Local: edit code in Claude Code → test locally → git push origin main
EC2:   git pull origin main → sudo systemctl restart analysis-gpt
```

### Remote update (from Telegram)
Send `/update` to the bot from Telegram:
- Bot runs `git pull origin main` on the EC2 instance
- Restarts itself via systemd
- Confirms: `✅ Updated to latest. Bot restarting...`

This means the full cycle is:
```
Edit in Claude Code → git push → /update in Telegram → done
```
No SSH required after initial setup.

---

## Environment Variables

Stored in `.env` on EC2 only — never committed to git:

```env
BOT_TOKEN=<from BotFather>
ALLOWED_USER_ID=<your numeric Telegram user ID>
```

### One-time Telegram setup
1. Open Telegram → search `@BotFather`
2. Send `/newbot` → name it (e.g. `Analysis GPT`) → get bot token
3. Find your user ID: send any message to `@userinfobot`
4. Add both values to `.env` on EC2

---

## Future Enhancements (Phase 2 — separate spec)

- Improve scoring factors: Greeks (Delta, Gamma, Vega), multi-day PCR trend, unusual activity detection
- Sector correlation weighting
- Historical backtesting of signals
- AI interpretation layer using Claude API (plain-English signal summaries)
- Scheduled auto-scans with Telegram push notifications

---

## Out of Scope (this phase)

- Multiple authorized users
- Webhook mode (polling is sufficient for single-user personal bot)
- Web dashboard or admin UI
- Database / persistence of past analyses
- Automated scheduled scans
