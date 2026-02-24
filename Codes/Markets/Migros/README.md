# Migros Türkiye Product Scraper

A Python tool to scrape all product data from [migros.com.tr](https://www.migros.com.tr) using their internal REST API.

## Features

- 📦 Scrapes **all categories** automatically via the Migros sitemap
- 📄 **Pagination** handled automatically — fetches every page per category
- 💾 Output as **CSV** and/or **JSON**
- ♻️ **Resume support** — restart an interrupted run without re-scraping completed categories
- ⏱️ Configurable **rate limiting** to avoid server overload
- 🔄 Automatic **retry** with exponential backoff on failed requests

## Output Fields

| Field           | Description                                             |
| --------------- | ------------------------------------------------------- |
| `id`            | Product ID                                              |
| `sku`           | SKU / barcode                                           |
| `name`          | Product name (Turkish)                                  |
| `brand`         | Brand name                                              |
| `category`      | Category label                                          |
| `regular_price` | Regular price in TL                                     |
| `shown_price`   | Currently displayed price (may differ during campaigns) |
| `unit`          | Unit of measurement (e.g. GRAM, PIECE)                  |
| `status`        | Availability status (e.g. IN_SALE)                      |
| `image_url`     | Product listing image URL                               |
| `product_url`   | Link to the product page                                |

## Setup

```bash
# 1. Clone / copy the project files
cd "AI201 Data Scraping"

# 2. Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate   # macOS / Linux
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# List all categories and their IDs
python main.py --list-categories

# Scrape a single category (ID "2" = Meyve & Sebze)
python main.py --category 2 --output both

# Scrape all categories, CSV only
python main.py --output csv

# Quick test — only 2 pages per category
python main.py --category 2 --limit 2 --output json

# Continue an interrupted full scrape
python main.py --output both --resume

# Slow down requests (useful if getting 429/403 errors)
python main.py --delay 1.5 --output csv

# Verbose debug logging
python main.py --category 2 -v
```

## Output Files

All files are saved to the `output/` directory:

| File                     | Description                                           |
| ------------------------ | ----------------------------------------------------- |
| `output/products.csv`    | All products (UTF-8 with BOM for Excel compatibility) |
| `output/products.json`   | Same data in JSON format                              |
| `output/checkpoint.json` | Tracks completed categories for resume support        |

## Configuration

Edit `config.py` to change:

- `REQUEST_DELAY` — seconds between page requests (default: `0.5`)
- `MAX_RETRIES` — retries before skipping a page (default: `3`)
- `OUTPUT_DIR` — where output files are saved (default: `output/`)

## Notes

> **Disclaimer**: This tool is for educational/research purposes. Always respect `robots.txt` and the site's Terms of Service. Do not overload the server.
