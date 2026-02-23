# Hapeloğlu Price Tracker

**AI201 - Intro to Data Science** | Spring 2026 | Özyeğin University

Daily web scraper for [Hapeloğlu Online Market](https://www.hapeloglu.com/).

## Important: Why curl_cffi?

This site runs behind **Cloudflare**, which fingerprints TLS handshakes.
Python's standard `requests` library has a recognizable TLS signature
that Cloudflare blocks (returning empty pages with 0 products).

**`curl_cffi`** uses libcurl compiled to impersonate Chrome's exact TLS
fingerprint. Cloudflare sees it as a real browser and serves full content.

## Setup

```bash
cd hapeloglu-price-tracker
pip install -r requirements.txt
```

## Usage

```bash
python -m scripts.run_scraper       # scrape today's prices
python -m scripts.run_analysis      # merge + analyze multi-day data
python -m pytest tests/             # run unit tests
```

## Project Structure

```
src/
    config.py       Settings: URLs, categories, headers
    utils.py        fetch_page(), parse_price() (uses curl_cffi)
    scraper.py      Core scraping engine

scripts/
    run_scraper.py  Daily scraper entry point
    run_analysis.py Multi-day analysis entry point
    run_daily.sh    Cron automation wrapper

notebooks/          Jupyter EDA & visualization
data/raw/           Daily CSV snapshots
data/processed/     Merged datasets
tests/              Unit tests with mock HTML
```

## Data Schema

| Column | Type | Example |
|--------|------|---------|
| product_id | str | 6650 |
| name | str | Domates Pembe Kg |
| current_price | float | 114.9 |
| regular_price | float | 149.9 |
| is_discounted | bool | True |
| discount_pct | float | 23.3 |
| category | str | Meyve, Sebze |
| product_url | str | https://www.hapeloglu.com/domates-pembe-kg-6650 |
| image_url | str | https://static.ticimax.cloud/... |
| in_stock | bool | True |
| scrape_date | str | 2026-02-24 |
| scrape_timestamp | str | 2026-02-24T08:00:00 |
