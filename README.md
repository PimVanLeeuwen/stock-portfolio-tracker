# stock-portfolio-tracker (stock-bot)

Small tracker for a stock portfolio to send a daily report via Signal.

## Features

- **Multi-provider data**: Finnhub → Alpha Vantage → yfinance (automatic fallback)
- **Currency conversion**: All prices converted to your base currency (default EUR) using live FX rates
- **Rich metrics**: Day %, Week-to-Date %, Month-to-Date %, P/L, 52-week range
- **Signal delivery**: Sends a formatted plain-text report via Signal REST API
- **Flexible scheduling**: Run once (`RUN_ONCE=true`) or on a daily schedule
- **Docker-ready**: Runs as `python /app/app.py`

## Project Structure

```
├── app.py                        # Top-level entry point (python /app/app.py)
├── config.yml                    # Portfolio & app configuration
├── requirements.txt              # Python dependencies
├── Dockerfile
├── stock_bot/                    # Main package
│   ├── app.py                    # Core application logic
│   ├── config.py                 # YAML config loader
│   ├── calculations.py           # P/L, day %, WTD, MTD computations
│   ├── currency.py               # FX rate fetching & conversion
│   ├── report.py                 # Plain-text report formatter
│   ├── signal_sender.py          # Signal REST API client
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

## Configuration

Edit `config.yml` (mounted at `/app/config.yml` inside Docker):

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

signal:
  sender: "+31YOURNUMBER"
  recipients: ["+31RECIPIENT1"]
  header: "📈 Daily Stock Report"
  footer: "— sent by stock-bot"

schedule:
  times: ["08:10", "17:10"]
  timezone: "Europe/Amsterdam"
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `FINNHUB_API_KEY` | No | Finnhub API key (highest priority provider) |
| `ALPHAVANTAGE_API_KEY` | No | Alpha Vantage API key (second priority) |
| `SIGNAL_API_BASE` | No | Signal REST API base URL (default: `http://signal:8080`) |
| `RUN_ONCE` | No | Set to `true` to run once and exit |
| `CONFIG_PATH` | No | Custom config file path (default: `/app/config.yml`) |
| `LOG_LEVEL` | No | Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO) |

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run once
RUN_ONCE=true python app.py

# Or with API keys
FINNHUB_API_KEY=your_key RUN_ONCE=true python app.py
```

## Running with Docker

```bash
# Build
docker build -t stock-bot .

# Run once
docker run --rm \
  -e RUN_ONCE=true \
  -e SIGNAL_API_BASE=http://host.docker.internal:8080 \
  -v $(pwd)/config.yml:/app/config.yml:ro \
  stock-bot

# Run on schedule (daemon)
docker run -d --name stock-bot \
  -e SIGNAL_API_BASE=http://signal:8080 \
  -e FINNHUB_API_KEY=your_key \
  -v $(pwd)/config.yml:/app/config.yml:ro \
  stock-bot
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
- Reports are capped at ~5.5 KB to stay within Signal's message limit.
- The app exits with a non-zero code on fatal errors when `RUN_ONCE=true`.

