"""
Category fetcher: discovers all Migros product categories using the
REST API's own aggregation data — the only reliable source of categories
that actually have products.

Strategy
--------
Migros exposes 8 top-level category IDs (2–9) that return products directly.
Each API response includes an ``aggregationGroups`` section listing all
available sub-category filters under the key ``kategoriler``.

By collecting those filters from every top-level category we get the full
tree of scrapable (sub)categories.
"""

import time
import logging
from typing import Optional

import requests

import config

logger = logging.getLogger(__name__)

# Verified top-level category IDs — confirmed by exhaustive probe of /rest/products/search.
# IDs 2-10 are the main grocery/home sections.
# IDs 158, 160, 165, 166 are standalone sections found by probing the 11-500 range.
TOP_LEVEL_CATEGORIES = [
    {"id": "2",   "name": "Meyve, Sebze"},
    {"id": "3",   "name": "Et, Tavuk, Balık"},
    {"id": "4",   "name": "Süt, Kahvaltılık"},
    {"id": "5",   "name": "Temel Gıda"},
    {"id": "6",   "name": "İçecek"},
    {"id": "7",   "name": "Deterjan, Temizlik"},
    {"id": "8",   "name": "Kişisel Bakım, Kozmetik, Sağlık"},
    {"id": "9",   "name": "Bebek"},
    {"id": "10",  "name": "Ev, Yaşam"},
    {"id": "158", "name": "Oyuncak"},
    {"id": "160", "name": "Evcil Hayvan"},
    {"id": "165", "name": "Kitap, Dergi, Gazete"},
    {"id": "166", "name": "Elektronik"},
]


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(config.DEFAULT_HEADERS)
    return session


def _fetch_subcategories(
    session: requests.Session,
    parent_id: str,
    parent_name: str,
) -> list[dict]:
    """
    Query the API for a top-level category and extract its sub-category
    filter options from the ``aggregationGroups`` field.

    Returns a list of sub-category dicts:
        [{"id": "101", "name": "Meyve", "parent_id": "2",
          "parent_name": "Meyve, Sebze"}, ...]
    """
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            resp = session.get(
                config.PRODUCT_SEARCH_URL,
                params={
                    "category-id": parent_id,
                    "sayfa": 1,
                    "sirala": config.DEFAULT_SORT,
                },
                timeout=30,
            )
            resp.raise_for_status()
            break
        except requests.RequestException as exc:
            if attempt == config.MAX_RETRIES:
                logger.error(
                    "Failed to fetch aggregations for top-level category %s: %s",
                    parent_id, exc,
                )
                return []
            wait = config.RETRY_BACKOFF * attempt
            logger.warning("Attempt %d failed (%s). Retrying in %ds…", attempt, exc, wait)
            time.sleep(wait)

    data = resp.json().get("data", {})
    subcats = []

    for agg_group in data.get("aggregationGroups", []):
        if agg_group.get("requestParamKey") != "kategoriler":
            continue
        for item in agg_group.get("aggregationInfos", []):
            sub_id = item.get("requestParameter") or item.get("id")
            sub_name = item.get("label", "")
            count = item.get("count", 0)
            if sub_id and count > 0:
                subcats.append({
                    "id": sub_id,
                    "name": sub_name,
                    "parent_id": parent_id,
                    "parent_name": parent_name,
                    "product_count": count,
                })

    logger.debug(
        "Top-level category '%s' (id=%s): %d subcategories found.",
        parent_name, parent_id, len(subcats),
    )
    return subcats


def fetch_categories(session: Optional[requests.Session] = None) -> list[dict]:
    """
    Return the full list of scrapable categories.

    Each entry is:
        {
          "id": "101",          # subcategory filter ID for ?kategoriler=
          "name": "Meyve",
          "parent_id": "2",     # top-level category ID for ?category-id=
          "parent_name": "Meyve, Sebze",
          "product_count": 50,
        }

    If a top-level category has no subcategories exposed in the API
    aggregations, it is included as a single entry with id == parent_id
    and parent_id == None (scraped without subcategory filter).
    """
    if session is None:
        session = _make_session()

    all_categories: list[dict] = []
    seen_ids: set[str] = set()

    for top in TOP_LEVEL_CATEGORIES:
        logger.info(
            "Fetching subcategories for '%s' (id=%s)…",
            top["name"], top["id"],
        )

        subcats = _fetch_subcategories(session, top["id"], top["name"])
        time.sleep(0.3)

        if subcats:
            for sc in subcats:
                if sc["id"] not in seen_ids:
                    all_categories.append(sc)
                    seen_ids.add(sc["id"])
        else:
            # Fall back: scrape the top-level directly (no sub-filter)
            entry = {
                "id": top["id"],
                "name": top["name"],
                "parent_id": None,
                "parent_name": None,
                "product_count": None,
            }
            if top["id"] not in seen_ids:
                all_categories.append(entry)
                seen_ids.add(top["id"])

    logger.info("Total scrapable categories: %d", len(all_categories))
    return all_categories
