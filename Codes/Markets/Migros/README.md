# Migros Türkiye Product Scraper

A Python tool to scrape all product data from [migros.com.tr](https://www.migros.com.tr) using their internal REST API.

## Features

- �️ Discovers **all sub-categories** automatically via the API's aggregation data (13 top-level × N subcategories)
- 📄 **Pagination** handled automatically — fetches every page per category
- 💾 Output as **CSV** and/or **JSON**, named with today's date
- ♻️ **Resume support** — restart an interrupted run without re-scraping completed categories
- ⏱️ Configurable **rate limiting** to avoid server overload
- 🔄 Automatic **retry** with exponential backoff on failed requests
- 🧹 Final **deduplication** pass removes any cross-category duplicate products

## Project Structure

```
Codes/Markets/Migros/
├── scripts/
│   ├── main.py              # CLI entry point & orchestrator
│   ├── category_fetcher.py  # Discovers all scrapable (sub)categories
│   ├── product_fetcher.py   # Paginates through products for a category
│   └── config.py            # All settings, paths, and API constants
├── checkpoints/
│   └── migros_checkpoint_<DATE>.json   # Resume state (auto-generated)
├── requirements.txt
└── README.md

Datas/Markets/Migros/           ← output lives here (outside Codes/)
└── migros_<DATE>.csv
```

## Output Fields

| Field           | Description                                             |
| --------------- | ------------------------------------------------------- |
| `id`            | Product ID                                              |
| `sku`           | SKU / barcode                                           |
| `name`          | Product name (Turkish)                                  |
| `brand`         | Brand name                                              |
| `category`      | Subcategory label                                       |
| `regular_price` | Regular price in TL                                     |
| `shown_price`   | Currently displayed price (may differ during campaigns) |
| `unit`          | Unit of measurement (e.g. `GRAM`, `PIECE`)              |
| `status`        | Availability status (e.g. `IN_SALE`)                    |
| `image_url`     | Product listing image URL                               |
| `product_url`   | Link to the product page                                |

## Setup

```bash
# 1. Go to the project root
cd InflationResearchStudy

# 2. Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate   # macOS / Linux
# venv\Scripts\activate    # Windows

# 3. Install dependencies
pip install -r Codes/Markets/Migros/requirements.txt
```

## Usage

Run all commands from inside the `scripts/` directory (so that relative imports resolve correctly):

```bash
cd Codes/Markets/Migros/scripts

# List all discovered categories and their IDs
python main.py --list-categories

# Scrape a single category (ID "2" = Meyve, Sebze) — CSV only
python main.py --category 2 --output csv

# Scrape all categories, save both CSV and JSON
python main.py --output both

# Quick test — only 2 pages per category
python main.py --category 2 --limit 2 --output json

# Continue an interrupted full scrape
python main.py --output csv --resume

# Slow down requests (useful if getting 429 / 403 errors)
python main.py --delay 1.5 --output csv

# Verbose debug logging
python main.py --category 2 -v
```

## Output Files

| File                                                             | Description                                           |
| ---------------------------------------------------------------- | ----------------------------------------------------- |
| `Datas/Markets/Migros/migros_<DATE>.csv`                         | All products (UTF-8 with BOM for Excel compatibility) |
| `Codes/Markets/Migros/checkpoints/migros_checkpoint_<DATE>.json` | Tracks completed categories for resume support        |

> Output paths are resolved automatically by `config.py` relative to the script's location, regardless of working directory.

## Configuration

Edit `scripts/config.py` to change:

| Setting          | Default                             | Description                             |
| ---------------- | ----------------------------------- | --------------------------------------- |
| `REQUEST_DELAY`  | `0.5` s                             | Delay between paginated requests        |
| `MAX_RETRIES`    | `3`                                 | Retries before skipping a failed page   |
| `RETRY_BACKOFF`  | `2` s                               | Backoff multiplier (doubles each retry) |
| `DEFAULT_SORT`   | `onerilenler`                       | API sort order                          |
| `OUTPUT_DIR`     | `Datas/Markets/Migros/`             | Where CSV/JSON files are saved          |
| `CHECKPOINT_DIR` | `Codes/Markets/Migros/checkpoints/` | Where checkpoint files are saved        |

## Category Discovery

`category_fetcher.py` probes **13 top-level category IDs** (2–10, 158, 160, 165, 166) against the `/rest/products/search` endpoint and extracts sub-category filter options from the `aggregationGroups` field. Categories with zero products are automatically skipped.

| ID  | Name                            |
| --- | ------------------------------- |
| 2   | Meyve, Sebze                    |
| 3   | Et, Tavuk, Balık                |
| 4   | Süt, Kahvaltılık                |
| 5   | Temel Gıda                      |
| 6   | İçecek                          |
| 7   | Deterjan, Temizlik              |
| 8   | Kişisel Bakım, Kozmetik, Sağlık |
| 9   | Bebek                           |
| 10  | Ev, Yaşam                       |
| 158 | Oyuncak                         |
| 160 | Evcil Hayvan                    |
| 165 | Kitap, Dergi, Gazete            |
| 166 | Elektronik                      |

## Notes

> **Disclaimer**: This tool is for educational / research purposes. Always respect `robots.txt` and the site's Terms of Service. Do not overload the server.
