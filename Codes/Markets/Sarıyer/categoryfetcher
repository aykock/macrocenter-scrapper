"""
Category fetcher — Sarıyer Market
==================================

İki aşamalı strateji:

1. **API tabanlı (tercih edilen):**
   ``GET /api/categories`` endpoint'i JSON dönüyorsa oradan alır.

2. **HTML tabanlı (fallback):**
   API yoksa veya 403/404 dönüyorsa, ana kategori sayfasının HTML'ini
   parse ederek kategori linklerini çıkarır.

Her iki yöntemde de dönen format aynıdır:
    {
        "id":           "meyve-sebze",   # slug veya sayısal ID
        "name":         "Meyve & Sebze",
        "url":          "https://www.sariyermarket.com/meyve-sebze",
        "parent_id":    None,            # alt kategori ise dolu
        "parent_name":  None,
        "product_count": 120,            # API bilinmiyorsa None
    }
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


# ── Strateji 1: API tabanlı ──────────────────────────────────────────────────

def _fetch_categories_from_api(session: requests.Session) -> list[dict]:
    """
    JSON API'den kategori ağacını çeker.
    API aşağıdaki formatlardan birini dönebilir:
      - Düz liste:  [{id, name, slug, parentId, productCount}, ...]
      - İç içe ağaç: [{id, name, children: [...]}]
    Her iki formatta da düz listeye dönüştürür.
    """
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            resp = session.get(config.CATEGORY_API_URL, timeout=20)
            if resp.status_code in (403, 404):
                logger.info(
                    "Kategori API'si %d döndü — HTML stratejisine geçiliyor.",
                    resp.status_code,
                )
                return []
            resp.raise_for_status()
            data = resp.json()
            break
        except requests.RequestException as exc:
            if attempt == config.MAX_RETRIES:
                logger.warning("Kategori API'si erişilemez: %s", exc)
                return []
            time.sleep(config.RETRY_BACKOFF * attempt)
    else:
        return []

    # API yanıtı doğrudan liste mi yoksa bir anahtar altında mı?
    if isinstance(data, list):
        raw_list = data
    elif isinstance(data, dict):
        # {"categories": [...]} veya {"data": [...]} gibi sarmalama
        raw_list = (
            data.get("categories")
            or data.get("data")
            or data.get("items")
            or []
        )
    else:
        return []

    return _flatten_category_tree(raw_list, parent_id=None, parent_name=None)


def _flatten_category_tree(
    nodes: list,
    parent_id: Optional[str],
    parent_name: Optional[str],
) -> list[dict]:
    """Recursive: iç içe kategori ağacını düz listeye çevirir."""
    result = []
    for node in nodes:
        if not isinstance(node, dict):
            continue

        cat_id   = str(node.get("id") or node.get("slug") or "")
        cat_name = node.get("name") or node.get("label") or cat_id
        cat_slug = node.get("slug") or node.get("url") or cat_id
        count    = node.get("productCount") or node.get("count") or node.get("product_count")

        # URL oluştur
        if cat_slug.startswith("http"):
            cat_url = cat_slug
        else:
            cat_url = f"{config.BASE_URL}/{cat_slug.lstrip('/')}"

        if cat_id:
            result.append({
                "id":            cat_id,
                "name":          cat_name,
                "url":           cat_url,
                "parent_id":     parent_id,
                "parent_name":   parent_name,
                "product_count": count,
            })

        # Alt kategorileri recursive işle
        children = node.get("children") or node.get("subCategories") or []
        if children:
            result.extend(
                _flatten_category_tree(children, cat_id, cat_name)
            )

    return result


# ── Strateji 2: HTML tabanlı ─────────────────────────────────────────────────

def _fetch_categories_from_html(session: requests.Session) -> list[dict]:
    """
    Siteyi tarayıcı gibi ziyaret edip HTML'den kategori linklerini çıkarır.
    """
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            resp = session.get(
                config.CATEGORY_HTML_URL,
                headers=config.HTML_HEADERS,
                timeout=30,
            )
            resp.raise_for_status()
            break
        except requests.RequestException as exc:
            if attempt == config.MAX_RETRIES:
                logger.error("HTML kategori sayfası alınamadı: %s", exc)
                return []
            time.sleep(config.RETRY_BACKOFF * attempt)
    else:
        return []

    soup = BeautifulSoup(resp.text, "lxml")

    # Önce CSS seçiciyle dene
    links = soup.select(config.CSS["category_links"])

    # Bulamazsa daha genel arama yap
    if not links:
        links = [
            a for a in soup.find_all("a", href=True)
            if _looks_like_category_url(a["href"])
        ]

    seen: set[str] = set()
    categories = []

    for a in links:
        href = a.get("href", "")
        url  = urljoin(config.BASE_URL, href)
        name = a.get_text(strip=True)

        if not name or url in seen:
            continue
        seen.add(url)

        # URL'den slug çıkar (son path segmenti)
        slug = url.rstrip("/").split("/")[-1]
        if not slug or slug in ("urunler", "products", "kategori", "category"):
            continue

        categories.append({
            "id":            slug,
            "name":          name or slug,
            "url":           url,
            "parent_id":     None,
            "parent_name":   None,
            "product_count": None,
        })

    logger.info("HTML'den %d kategori bulundu.", len(categories))
    return categories


def _looks_like_category_url(href: str) -> bool:
    """URL bir ürün kategorisi linkine benziyorsa True döner."""
    skip = {"#", "javascript", "mailto", "tel:", "http://", "https://"}
    if any(href.startswith(s) for s in skip):
        return False
    # Dış link değil ve sadece rakam/ID değil
    if href.startswith("http") and config.BASE_URL not in href:
        return False
    skip_segments = {
        "giris", "kayit", "sepet", "hesabim", "siparis",
        "iletisim", "hakkimizda", "login", "register", "cart",
        "account", "checkout", "search", "arama",
    }
    parts = href.strip("/").split("/")
    return bool(parts) and parts[-1].lower() not in skip_segments


# ── Genel arayüz ─────────────────────────────────────────────────────────────

def fetch_categories(session: Optional[requests.Session] = None) -> list[dict]:
    """
    Sarıyer Market'in tüm (alt-)kategorilerini döndürür.

    Önce JSON API'yi dener; başarısız olursa HTML'den parse eder.

    Her eleman:
        {
            "id":            str,   # slug veya sayısal ID
            "name":          str,
            "url":           str,   # tam URL (ürün listesi)
            "parent_id":     str | None,
            "parent_name":   str | None,
            "product_count": int | None,
        }
    """
    if session is None:
        session = _make_session()

    logger.info("Kategori listesi alınıyor (API deneniyor)…")
    categories = _fetch_categories_from_api(session)

    if not categories:
        logger.info("API çalışmıyor — HTML'den kategori çekiliyor…")
        categories = _fetch_categories_from_html(session)

    if not categories:
        raise RuntimeError(
            "Hiçbir kategori bulunamadı. "
            "CSS seçicilerini veya config.CATEGORY_API_URL'yi kontrol edin."
        )

    # Yinelenen ID'leri temizle
    seen: set[str] = set()
    unique = []
    for cat in categories:
        if cat["id"] not in seen:
            unique.append(cat)
            seen.add(cat["id"])

    logger.info("Toplam çekilebilir kategori: %d", len(unique))
    return unique
