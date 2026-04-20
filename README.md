# Deal Hunter MVP

Scans Slickdeals RSS + retailer JSON endpoints for penny deals / clearance items
and posts matches to a Discord channel via webhook.

## Quick start (Windows / PowerShell)

```powershell
cd C:\Projects\deal-hunter

# 1. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
copy .env.example .env
notepad .env      # paste your Discord webhook URL

# 4. Run a single test scan
python main.py --once

# 5. Run continuously (every 5 min)
python main.py
```

## Getting a Discord webhook URL

1. Make a test Discord server (or use an existing one).
2. Server settings → Integrations → Webhooks → New Webhook.
3. Pick the channel, copy the webhook URL into `.env`.

## Adding retailer JSON endpoints

Slickdeals alone will catch a lot. But for first-to-know on specific retailers,
you'll want to find their product JSON endpoints:

1. Open the retailer's clearance page in Chrome.
2. F12 → Network tab → filter to `Fetch/XHR`.
3. Refresh. Look for requests returning JSON with product data
   (Target uses `redsky.target.com`, Best Buy uses `www.bestbuy.com/site/...`, etc.).
4. Right-click the request → Copy → Copy as cURL. Test it in Postman / `curl`.
5. Once you find one that works, add it to `config.yaml` under `retailer_endpoints`.
6. You'll almost certainly need to customize `sources/retailer_json.py` per-retailer
   because response shapes vary — the generic extractor is a starting point, not a
   finished product.

## Tuning filters

Edit `config.yaml`:
- `max_price` — raise to $10-$20 while testing so you see volume.
- `penny_keywords` — add your own triggers (e.g. brand names, category keywords).

## Files

- `main.py` — entry point + scheduler
- `config.yaml` — all tunable settings
- `sources/` — one file per source type (extend here)
- `filters/` — decides what's worth alerting on
- `notifiers/` — Discord webhook poster
- `storage/seen.db` — SQLite dedup store (auto-created)
- `deal_hunter.log` — runtime log

## Known MVP limits (intentional — address in v2)

- **No profit validation.** It alerts on cheap things, not *profitably resellable* things.
  Next iteration: add eBay sold-comp lookup to compute estimated margin.
- **No stock verification.** A $0.01 listing might be out of stock; we still alert.
- **No image previews on Discord embeds** — could parse OG tags from the deal URL
  to add thumbnails.
- **Generic retailer JSON extractor is weak.** Every retailer needs its own parser;
  the included one only handles simple flat lists.
- **Single-threaded polling.** Fine for 2-5 sources; parallelize if you scale to 20+.
