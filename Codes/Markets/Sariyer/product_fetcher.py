"""
Product fetcher — Sarıyer Market
===================================
POST /Catalog/OBAjaxFilterProducts
Form parametreleri: cid, PagingFilteringContext[PageNumber], isc, sid, adv
"""

import time
import logging
from typing import Optional

import requests
import config

logger = logging.getLogger(__name__)


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(config.DEFAULT_HEADERS)
    return session


def _parse_product(raw: dict, category: dict) -> dict:
    def price(val) -> float:
        if not val:
            return 0.0
        try:
            return round(float(str(val).replace(",", ".")), 2)
        except:
            return 0.0

    regular = price(raw.get("OldPrice") or raw.get("Price"))
    shown   = price(raw.get("Price"))
    if regular == 0:
        regular = shown

    discount = 0
    if regular and shown and regular > shown:
        discount = int(round((regular - shown) / regular * 100))

    # Görsel
    image = raw.get("PictureThumbnailUrl") or raw.get("PictureUrl") or ""
    if image and not image.startswith("http"):
        image = config.BASE_URL + image

    # Ürün URL
    slug = raw.get("SeName") or raw.get("seName") or ""
    product_url = f"{config.BASE_URL}/{slug}" if slug else ""

    return {
        "id":            str(raw.get("Id") or raw.get("id") or ""),
        "sku":           str(raw.get("Sku") or raw.get("sku") or ""),
        "name":          raw.get("Name") or raw.get("name") or "",
        "brand":         raw.get("BrandName") or raw.get("brandName") or "",
        "category":      category.get("name", ""),
        "category_id":   category.get("id", ""),
        "regular_price": regular,
        "shown_price":   shown,
        "discount_rate": discount,
        "unit":          raw.get("QuantityUnitName") or "",
        "status":        "IN_STOCK" if raw.get("InStock") else "OUT_OF_STOCK",
        "image_url":     image,
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
    page = 0  # site 0-indexed sayfalama kullanıyor

    while True:
        if page_limit and page >= page_limit:
            break

        form_data = {
            "q":            "",
            "cid":          category["id"],
            "isc":          "true",
            "mid":          "0",
            "vid":          "0",
            "sid":          "true",
            "adv":          "true",
            "asv":          "false",
            "PagingFilteringContext[PageNumber]": str(page),
            "PagingFilteringContext[PageSize]":   str(config.PAGE_SIZE),
        }

        data = _post_with_retry(session, form_data)
        if data is None:
            break

        # Yanıt: {"products": [...], "totalItems": N} veya düz liste
        if isinstance(data, dict):
            products_raw = (
                data.get("products")
                or data.get("Products")
                or data.get("items")
                or []
            )
            total_pages = data.get("totalPages") or data.get("TotalPages")
        elif isinstance(data, list):
            products_raw = data
            total_pages = None
        else:
            break

        if not products_raw:
            break

        for raw in products_raw:
            all_products.append(_parse_product(raw, category))

        logger.debug(
            "Kategori '%s' — sayfa %d → %d ürün (toplam: %d)",
            category["name"], page, len(products_raw), len(all_products),
        )

        # Sonraki sayfa var mı?
        if total_pages and page + 1 >= int(total_pages):
            break
        if len(products_raw) < config.PAGE_SIZE:
            break

        page += 1
        time.sleep(delay)

    return all_products


def _post_with_retry(session: requests.Session, form_data: dict) -> Optional[dict]:
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            resp = session.post(
                config.PRODUCT_LIST_URL,
                data=form_data,
                timeout=30,
            )
            if resp.status_code == 403:
                logger.warning("403 Forbidden — delay artırılabilir.")
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            if attempt == config.MAX_RETRIES:
                logger.error("Tüm denemeler başarısız: %s", exc)
                return None
            wait = config.RETRY_BACKOFF * attempt
            logger.warning("Deneme %d başarısız (%s). %ds sonra tekrar…", attempt, exc, wait)
            time.sleep(wait)
    return None
