# stock-portfolio-tracker (stock-bot)

A daily stock portfolio tracker that sends reports via **Telegram**.

## Features

- **Multi-provider data**: Finnhub → Alpha Vantage → yfinance (automatic fallback)
- **Currency conversion**: All prices converted to your base currency (default EUR) using live FX rates
- **Rich metrics**: Day %, Week-to-Date %, Month-to-Date %, P/L, 52-week range
- **Telegram delivery**: Reports sent via Telegram Bot API
- **Flexible scheduling**: Run once (`RUN_ONCE=true`) or on a daily schedule
- **Docker-ready**: Single container, deploy via Portainer from Git

## Project Structure

```
├── app.py                        # Top-level entry point (python /app/app.py)
├── config.yml                    # Portfolio & app configuration
├── requirements.txt              # Python dependencies
├── Dockerfile
├── docker-compose.yml            # For local Docker / Portainer deployment
├── stock_bot/                    # Main package
│   ├── app.py                    # Core application logic
│   ├── config.py                 # YAML config loader
│   ├── calculations.py           # P/L, day %, WTD, MTD computations
│   ├── currency.py               # FX rate fetching & conversion
│   ├── report.py                 # Plain-text report formatter
│   ├── telegram_sender.py        # Telegram Bot API client
│   ├── scheduler.py              # Schedule loop / RUN_ONCE support
│   └── providers/
│       ├── base.py               # Abstract StockProvider interface
│       ├── provider_manager.py   # Priority-based provider cascade
│       ├── finnhub_provider.py   # Finnhub API
│       ├── alphavantage_provider.py  # Alpha Vantage API
│       └── yfinance_provider.py  # yfinance (no API key needed)
└── tests/
    └── test_calculations.py      # Unit tests for calculations
```

## Quick Start — Get a Telegram test message in 5 minutes

### 1. Create a Telegram bot

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`, follow the prompts, pick a name
3. Copy the **bot token** (looks like `123456:ABC-DEF...`)

### 2. Get your chat ID

1. Send any message to your new bot in Telegram
2. Open this URL in your browser (replace `<TOKEN>`):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. Find `"chat":{"id": 123456789}` — that number is your chat ID

### 3. Configure and run

```bash
cp .env.example .env
# Edit .env — paste your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
```

Then send a test report:

```bash
docker compose run --rm -e RUN_ONCE=true stock-bot
```

Check Telegram — you should receive the stock report! 🎉

### 4. Start the scheduled bot

```bash
docker compose up -d
```

The bot will send reports at the times configured in `config.yml`.

## Configuration

Edit `config.yml`:

```yaml
portfolio:
  base_currency: EUR
  positions:
    - symbol: AAPL
      units: 12
      cost_basis: 148.20    # optional – omit for change-only report
    - symbol: MSFT
      units: 8
      cost_basis: 310.50
    - symbol: ASML.AS
      units: 5

report:
  fields: [last_price, day_change_pct, pnl_abs, pnl_pct, week_to_date_pct, month_to_date_pct, fiftytwo_wk_range]
  sort_by: day_change_pct
  top_n: 10
  include_index: ["^GSPC", "^NDX"]

telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  chat_ids: ["${TELEGRAM_CHAT_ID}"]
  header: "📈 Daily Stock Report"
  footer: "— sent by stock-bot"

schedule:
  times: ["08:10", "17:10"]
  timezone: "Europe/Amsterdam"
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | **Yes** | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | **Yes** | Your chat or group ID |
| `FINNHUB_API_KEY` | No | Finnhub API key (highest priority provider) |
| `ALPHAVANTAGE_API_KEY` | No | Alpha Vantage API key (second priority) |
| `RUN_ONCE` | No | Set to `true` to run once and exit |
| `CONFIG_PATH` | No | Custom config file path (default: `/app/config.yml`) |
| `LOG_LEVEL` | No | DEBUG, INFO, WARNING, ERROR (default: INFO) |

## Deploy on Portainer (via Git)

1. Go to **Stacks → Add stack**
2. Select **Repository**
3. Fill in:
   - **Repository URL**: `https://github.com/PimVanLeeuwen/stock-portfolio-tracker`
   - **Reference**: `main`
   - **Compose path**: `docker-compose.yml`
4. Under **Environment variables**, add:
   - `TELEGRAM_BOT_TOKEN` = your bot token
   - `TELEGRAM_CHAT_ID` = your chat ID
   - `RUN_ONCE` = `false` (or `true` for a one-shot test)
5. Click **Deploy the stack**

To update after a `git push`: go to the stack and click **Pull and redeploy**.

## Running Locally (without Docker)

```bash
pip install -r requirements.txt

# Set env vars
export TELEGRAM_BOT_TOKEN=your_token
export TELEGRAM_CHAT_ID=your_chat_id

# Run once
RUN_ONCE=true python app.py
```

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## Data Provider Priority

1. **Finnhub** – if `FINNHUB_API_KEY` is set
2. **Alpha Vantage** – if `ALPHAVANTAGE_API_KEY` is set
3. **yfinance** – always available (no API key required, fallback)

The same priority is used for FX rate fetching.

## Notes

- If `cost_basis` is omitted for a position, the P/L columns show "—" and only change metrics are reported.
- Reports are auto-chunked if they exceed Telegram's 4096-character limit.
- The app exits with a non-zero code on fatal errors when `RUN_ONCE=true`.
- To update after a git push: in Portainer, go to the stack and click **Pull and redeploy**.

