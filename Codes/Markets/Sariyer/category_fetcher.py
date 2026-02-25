"""
Product fetcher — Sarıyer Market
Kategori sayfalarını HTML olarak scrape eder.
NopCommerce tabanlı site — sayfalama: ?pagenumber=N
"""

import re
import time
import logging
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(config.DEFAULT_HEADERS)
    return session


def _price(text: str) -> float:
    if not text:
        return 0.0
    clean = re.sub(r"[^\d,\.]", "", text)
    if "," in clean and "." in clean:
        if clean.rfind(",") > clean.rfind("."):
            clean = clean.replace(".", "").replace(",", ".")
        else:
            clean = clean.replace(",", "")
    elif "," in clean:
        clean = clean.replace(",", ".")
    try:
        return round(float(clean), 2)
    except:
        return 0.0


def _parse_product(card, category: dict) -> Optional[dict]:
    # Ürün adı
    name_tag = card.select_one(".product-title a, .product-name a, h2 a, h3 a, .name a")
    if not name_tag:
        name_tag = card.select_one(".product-title, .product-name, h2, h3")
    name = name_tag.get_text(strip=True) if name_tag else ""
    if not name:
        return None

    # Fiyatlar — NopCommerce genelde .price-value veya .actual-price kullanır
    shown_tag   = card.select_one(".price-value, .actual-price, .price .current, .new-price, span.price")
    regular_tag = card.select_one(".old-price, .non-discounted-price, s.price, .price-old")

    shown_price   = _price(shown_tag.get_text(strip=True)   if shown_tag   else "")
    regular_price = _price(regular_tag.get_text(strip=True) if regular_tag else "")

    if regular_price == 0:
        regular_price = shown_price

    discount = 0
    if regular_price and shown_price and regular_price > shown_price:
        discount = int(round((regular_price - shown_price) / regular_price * 100))

    # Görsel
    img_tag = card.select_one("img.product-image, .product-img img, img")
    image_url = ""
    if img_tag:
        image_url = img_tag.get("data-src") or img_tag.get("src") or ""
        if image_url and not image_url.startswith("http"):
            image_url = urljoin(config.BASE_URL, image_url)

    # Ürün URL
    link_tag = card.select_one("a.product-title, h2 a, h3 a, .product-name a, a")
    product_url = ""
    if link_tag:
        href = link_tag.get("href", "")
        product_url = urljoin(config.BASE_URL, href) if href else ""

    # ID
    product_id = (
        card.get("data-productid") or card.get("data-id") or card.get("id") or ""
    )
    if not product_id and product_url:
        product_id = product_url.rstrip("/").split("/")[-1]

    return {
        "id":            str(product_id),
        "sku":           str(product_id),
        "name":          name,
        "brand":         card.get("data-brand", ""),
        "category":      category.get("name", ""),
        "category_id":   category.get("id", ""),
        "regular_price": regular_price,
        "shown_price":   shown_price,
        "discount_rate": discount,
        "unit":          "",
        "status":        "OUT_OF_STOCK" if card.select_one(".out-of-stock") else "IN_STOCK",
        "image_url":     image_url,
        "product_url":   product_url,
    }


def fetch_products_for_category(
    category: dict,
    session: Optional[requests.Session] = None,
    delay: float = config.REQUEST_DELAY,
    page_limit: int = 0,
) -> list[dict]:

    if session is None:
        session = _make_session()

    all_products: list[dict] = []
    page = 1
    base_url = category["url"]

    while True:
        if page_limit and page > page_limit:
            break

        url = base_url + ("&" if "?" in base_url else "?") + f"pagenumber={page}"

        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                resp = session.get(url, timeout=30)
                resp.raise_for_status()
                break
            except requests.RequestException as exc:
                if attempt == config.MAX_RETRIES:
                    logger.error("Sayfa alınamadı '%s' sayfa %d: %s", category["name"], page, exc)
                    return all_products
                time.sleep(config.RETRY_BACKOFF * attempt)

        soup = BeautifulSoup(resp.text, "lxml")

        # NopCommerce ürün kartları
        cards = soup.select(
            ".product-item, .item-box, article.product-item, "
            ".product-grid .item, .product-box"
        )

        if not cards:
            logger.debug("Kategori '%s' sayfa %d'de ürün yok — durdu.", category["name"], page)
            break

        page_products = []
        for card in cards:
            record = _parse_product(card, category)
            if record:
                page_products.append(record)

        all_products.extend(page_products)
        logger.debug(
            "Kategori '%s' — sayfa %d → %d ürün (toplam: %d)",
            category["name"], page, len(page_products), len(all_products),
        )

        # Sonraki sayfa var mı?
        next_page = soup.select_one("a.next-page, li.next-page a, .pager .next a, a[rel='next']")
        if not next_page:
            break

        page += 1
        time.sleep(delay)

    return all_products
