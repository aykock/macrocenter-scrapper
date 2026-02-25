"""
Product fetcher — Sarıyer Market
==================================

İki katmanlı yaklaşım:

1. **API tabanlı (tercih edilen):**
   ``GET /api/products?category=<slug>&page=N&limit=48``
   JSON liste döner, sayfalama offset/page tabanlıdır.

2. **HTML tabanlı (fallback):**
   API yoksa BeautifulSoup ile kategori URL'sini scrape eder,
   ``?page=N`` veya ``?sayfa=N`` ile sonraki sayfalara geçer.
   CSS seçiciler config.py'daki ``CSS`` sözlüğünden okunur.

Her iki yöntemde de dönen kayıt şeması aynıdır:
    {
        "id":            str,
        "sku":           str,
        "name":          str,
        "brand":         str,
        "category":      str,
        "category_id":   str,
        "regular_price": float,   # TL cinsinden
        "shown_price":   float,   # indirimli fiyat; yoksa regular_price
        "discount_rate": int,     # 0–100 arası yüzde
        "unit":          str,     # "kg", "adet" vb.
        "status":        str,     # "IN_STOCK" | "OUT_OF_STOCK" | ""
        "image_url":     str,
        "product_url":   str,
    }
"""

import re
import time
import logging
from typing import Optional
from urllib.parse import urljoin, urlencode, urlparse, parse_qs, urlencode

import requests
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(config.DEFAULT_HEADERS)
    return session


# ── Kayıt normalleştirme ─────────────────────────────────────────────────────

def _price_str_to_float(raw: str) -> float:
    """'1.234,56 TL' veya '1234.56' gibi çeşitli formatları float'a çevirir."""
    if not raw:
        return 0.0
    clean = re.sub(r"[^\d,\.]", "", str(raw))
    # Türkçe format: nokta binlik ayracı, virgül ondalık
    if "," in clean and "." in clean:
        if clean.rfind(",") > clean.rfind("."):
            clean = clean.replace(".", "").replace(",", ".")
        else:
            clean = clean.replace(",", "")
    elif "," in clean:
        clean = clean.replace(",", ".")
    try:
        return round(float(clean), 2)
    except ValueError:
        return 0.0


def _parse_product_api(raw: dict, category: dict) -> dict:
    """JSON API'den gelen ham dict'i normalize eder."""
    # Fiyat: API genellikle kuruş veya float döner
    def to_float(val) -> float:
        if val is None:
            return 0.0
        v = float(val)
        # 100'den büyük tam sayı → büyük ihtimalle kuruş
        return round(v / 100, 2) if (v == int(v) and v > 200) else round(v, 2)

    regular = to_float(
        raw.get("regularPrice") or raw.get("original_price")
        or raw.get("price") or 0
    )
    shown = to_float(
        raw.get("shownPrice") or raw.get("discounted_price")
        or raw.get("sale_price") or raw.get("price") or regular
    )

    discount = raw.get("discountRate") or raw.get("discount_rate") or 0
    if not discount and regular and shown and regular > shown:
        discount = int(round((regular - shown) / regular * 100))

    brand_raw = raw.get("brand") or {}
    brand = (
        brand_raw.get("name", "") if isinstance(brand_raw, dict)
        else str(brand_raw or "")
    )

    images = raw.get("images") or []
    image_url = ""
    if isinstance(images, list) and images:
        first = images[0]
        image_url = (
            first.get("url") or first.get("src") or ""
        ) if isinstance(first, dict) else str(first)
    elif isinstance(images, str):
        image_url = images

    slug = raw.get("prettyName") or raw.get("slug") or raw.get("url") or ""
    if slug and not slug.startswith("http"):
        product_url = f"{config.BASE_URL}/{slug.lstrip('/')}"
    else:
        product_url = slug

    return {
        "id":            str(raw.get("id") or raw.get("sku") or ""),
        "sku":           str(raw.get("sku") or raw.get("id") or ""),
        "name":          raw.get("name") or raw.get("title") or "",
        "brand":         brand,
        "category":      category.get("name", ""),
        "category_id":   category.get("id", ""),
        "regular_price": regular,
        "shown_price":   shown,
        "discount_rate": int(discount),
        "unit":          raw.get("unit") or raw.get("birim") or "",
        "status":        (
            raw.get("status") or raw.get("stockStatus")
            or raw.get("availability") or ""
        ),
        "image_url":     image_url,
        "product_url":   product_url,
    }


def _parse_product_html(card, category: dict, base_url: str = config.BASE_URL) -> Optional[dict]:
    """BS4 ürün kartı tag'inden normalize kayıt çıkarır."""
    # ── Ürün adı ──────────────────────────────────────────────────────────────
    name_tag = card.select_one(config.CSS["product_name"])
    name = name_tag.get_text(strip=True) if name_tag else ""
    if not name:
        # data-* veya title attr fallback
        name = card.get("data-name") or card.get("title") or ""
    if not name:
        return None  # ürün adı yoksa kayıt anlamlı değil

    # ── Fiyatlar ──────────────────────────────────────────────────────────────
    price_tag = card.select_one(config.CSS["product_price"])
    shown_price = _price_str_to_float(
        price_tag.get_text(strip=True) if price_tag else ""
    )

    old_tag = card.select_one(config.CSS["product_old_price"])
    regular_price = _price_str_to_float(
        old_tag.get_text(strip=True) if old_tag else ""
    ) or shown_price

    discount = 0
    if regular_price and shown_price and regular_price > shown_price:
        discount = int(round((regular_price - shown_price) / regular_price * 100))

    # ── Görsel ────────────────────────────────────────────────────────────────
    img_tag = card.select_one(config.CSS["product_image"])
    image_url = ""
    if img_tag:
        image_url = (
            img_tag.get("data-src") or img_tag.get("src") or ""
        )
        if image_url and not image_url.startswith("http"):
            image_url = urljoin(base_url, image_url)

    # ── Ürün URL ──────────────────────────────────────────────────────────────
    link_tag = card.select_one(config.CSS["product_link"])
    product_url = ""
    if link_tag:
        href = link_tag.get("href", "")
        product_url = urljoin(base_url, href) if href else ""
    elif card.name == "a":
        product_url = urljoin(base_url, card.get("href", ""))

    # ── ID ────────────────────────────────────────────────────────────────────
    product_id = (
        card.get("data-id") or card.get("data-product-id")
        or card.get("id") or ""
    )
    if not product_id and product_url:
        # URL'nin son segmentini ID olarak kullan
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
        "unit":          card.get("data-unit", ""),
        "status":        card.get("data-status", ""),
        "image_url":     image_url,
        "product_url":   product_url,
    }


# ── Strateji 1: API tabanlı ──────────────────────────────────────────────────

def _fetch_products_api(
    session: requests.Session,
    category: dict,
    delay: float,
    page_limit: int,
) -> Optional[list[dict]]:
    """
    GET /api/products endpoint'inden tüm sayfaları çeker.
    API bulunamazsa None döner (HTML fallback devreye girer).
    """
    all_products: list[dict] = []
    page = 1

    while True:
        if page_limit and page > page_limit:
            break

        params = {
            "category": category["id"],
            "page":     page,
            "limit":    config.PAGE_SIZE,
            "sort":     config.DEFAULT_SORT,
        }
        data = _get_json(session, config.PRODUCT_LIST_URL, params)

        if data is None:
            # İlk sayfada bile veri yoksa → API yok, fallback kullan
            return None if page == 1 else all_products

        # Ürün listesini saptamak için birden fazla anahtar dene
        products_raw: list = (
            data.get("products")
            or data.get("items")
            or data.get("data", {}).get("products")
            or data.get("data")
            or []
        )

        if not isinstance(products_raw, list) or not products_raw:
            break

        for raw in products_raw:
            all_products.append(_parse_product_api(raw, category))

        logger.debug(
            "Kategori '%s' — sayfa %d → %d ürün (toplam: %d)",
            category["name"], page, len(products_raw), len(all_products),
        )

        # Sayfalama: "totalPages" veya "hasMore" kontrolü
        total_pages = (
            data.get("totalPages") or data.get("total_pages")
            or data.get("pageCount")
        )
        has_more = data.get("hasMore") or data.get("has_more")

        if total_pages and page >= int(total_pages):
            break
        if has_more is False:
            break
        if len(products_raw) < config.PAGE_SIZE:
            # Son sayfa: tam dolu gelmediyse bitti
            break

        page += 1
        time.sleep(delay)

    return all_products


def _get_json(
    session: requests.Session,
    url: str,
    params: dict,
) -> Optional[dict]:
    """Retry destekli GET isteği; başarısızsa None döner."""
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=30)
            if resp.status_code in (403, 404):
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            if attempt == config.MAX_RETRIES:
                logger.error("İstek başarısız (%s): %s", url, exc)
                return None
            wait = config.RETRY_BACKOFF * attempt
            logger.warning("Deneme %d başarısız (%s). %ds sonra tekrar…", attempt, exc, wait)
            time.sleep(wait)
    return None


# ── Strateji 2: HTML tabanlı ─────────────────────────────────────────────────

def _fetch_products_html(
    session: requests.Session,
    category: dict,
    delay: float,
    page_limit: int,
) -> list[dict]:
    """
    Kategori URL'sini sayfa sayfa scrape eder.
    ``?page=N`` veya ``?sayfa=N`` ile sayfalama yapar.
    """
    all_products: list[dict] = []
    base_url = category["url"]
    page = 1

    while True:
        if page_limit and page > page_limit:
            break

        # Sayfalama parametresini URL'ye ekle
        page_url = base_url + ("" if "?" not in base_url else "&") + f"?page={page}"

        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                resp = session.get(
                    page_url,
                    headers=config.HTML_HEADERS,
                    timeout=30,
                )
                resp.raise_for_status()
                break
            except requests.RequestException as exc:
                if attempt == config.MAX_RETRIES:
                    logger.error(
                        "Sayfa alınamadı (kategori: '%s', sayfa: %d): %s",
                        category["name"], page, exc,
                    )
                    return all_products
                time.sleep(config.RETRY_BACKOFF * attempt)
        else:
            return all_products

        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.select(config.CSS["product_card"])

        if not cards:
            logger.debug("Kategori '%s' sayfa %d'de ürün bulunamadı — durduruluyor.", category["name"], page)
            break

        page_products: list[dict] = []
        for card in cards:
            record = _parse_product_html(card, category)
            if record:
                page_products.append(record)

        all_products.extend(page_products)

        logger.debug(
            "Kategori '%s' — sayfa %d → %d ürün (toplam: %d)",
            category["name"], page, len(page_products), len(all_products),
        )

        # Sonraki sayfa linki var mı?
        next_btn = soup.select_one(config.CSS["next_page"])
        if not next_btn:
            break

        page += 1
        time.sleep(delay)

    return all_products


# ── Genel arayüz ─────────────────────────────────────────────────────────────

def fetch_products_for_category(
    category: dict,
    session: Optional[requests.Session] = None,
    delay: float = config.REQUEST_DELAY,
    page_limit: int = 0,
) -> list[dict]:
    """
    Bir kategorinin tüm ürünlerini çeker; önce API, başarısız olursa HTML.

    Args:
        category:   fetch_categories() tarafından döndürülen dict.
        session:    Paylaşılan requests.Session (None ise yeni oluşturulur).
        delay:      Sayfalar arası bekleme süresi (saniye).
        page_limit: Maksimum sayfa sayısı (0 = sınırsız).

    Returns:
        Normalize ürün dict listesi.
    """
    if session is None:
        session = _make_session()

    # Önce API'yi dene
    result = _fetch_products_api(session, category, delay, page_limit)

    if result is None:
        logger.info(
            "Kategori '%s' için API yanıt vermedi — HTML moduna geçiliyor.",
            category["name"],
        )
        result = _fetch_products_html(session, category, delay, page_limit)

    # Eksik fiyat veya ID'li kayıtları filtrele
    clean = [
        r for r in result
        if r.get("name") and (r.get("shown_price") or r.get("regular_price"))
    ]

    if len(clean) < len(result):
        logger.warning(
            "Kategori '%s': %d kayıt eksik alan nedeniyle düşürüldü.",
            category["name"], len(result) - len(clean),
        )

    return clean
