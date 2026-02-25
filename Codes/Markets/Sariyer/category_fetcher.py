"""
Category fetcher — Sarıyer Market
===================================
GET /OBComponents/GetHomePageCategories → JSON kategori listesi döner.
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


def fetch_categories(session: Optional[requests.Session] = None) -> list[dict]:
    if session is None:
        session = _make_session()

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            resp = session.get(config.CATEGORY_API_URL, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            break
        except requests.RequestException as exc:
            if attempt == config.MAX_RETRIES:
                raise RuntimeError(f"Kategori listesi alınamadı: {exc}")
            time.sleep(config.RETRY_BACKOFF * attempt)

    if isinstance(data, list):
        raw_list = data
    elif isinstance(data, dict):
        raw_list = (
            data.get("categories")
            or data.get("data")
            or data.get("items")
            or []
        )
    else:
        raise RuntimeError(f"Beklenmeyen kategori yanıtı: {type(data)}")

    categories = []
    seen: set[str] = set()

    def _parse(nodes, parent_id=None, parent_name=None):
        for node in nodes:
            if not isinstance(node, dict):
                continue
            cid  = str(node.get("Id") or node.get("id") or "")
            name = node.get("Name") or node.get("name") or cid
            if cid and cid not in seen:
                seen.add(cid)
                categories.append({
                    "id":            cid,
                    "name":          name,
                    "url":           f"{config.BASE_URL}/search?cid={cid}&adv=True&isc=True&sid=True",
                    "parent_id":     parent_id,
                    "parent_name":   parent_name,
                    "product_count": node.get("ProductCount") or node.get("productCount"),
                })
            children = node.get("SubCategories") or node.get("children") or []
            if children:
                _parse(children, cid, name)

    _parse(raw_list)

    if not categories:
        raise RuntimeError("Hiçbir kategori bulunamadı.")

    logger.info("Toplam kategori: %d", len(categories))
    return categories
