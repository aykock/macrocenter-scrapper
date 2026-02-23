"""
Unit tests - run with: python -m pytest tests/
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bs4 import BeautifulSoup
from src.utils import parse_price, get_total_product_count
from src.scraper import extract_products_from_page


MOCK_PATH = os.path.join(os.path.dirname(__file__), "mock_data", "meyve_page1.html")


def load_mock_soup():
    with open(MOCK_PATH, "r", encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "html.parser")


# ---- parse_price ----

def test_parse_price_normal():
    assert parse_price("134,90 TL") == 134.9

def test_parse_price_thousands():
    assert parse_price("1.250,00 TL") == 1250.0

def test_parse_price_with_kdv():
    assert parse_price("88,50 TL\n KDV Dahil") == 88.5

def test_parse_price_none():
    assert parse_price(None) is None
    assert parse_price("") is None


# ---- get_total_product_count ----

def test_total_count():
    soup = load_mock_soup()
    assert get_total_product_count(soup) == 3


# ---- extract_products ----

def test_extract_products_count():
    soup = load_mock_soup()
    assert len(extract_products_from_page(soup, "Meyve")) == 3

def test_first_product_fields():
    soup = load_mock_soup()
    p = extract_products_from_page(soup, "Meyve")[0]
    assert p["product_id"] == "6650"
    assert p["name"] == "Domates Pembe Kg"
    assert p["current_price"] == 114.9
    assert p["regular_price"] == 149.9
    assert p["is_discounted"] is True
    assert p["discount_pct"] == 23.3
    assert p["category"] == "Meyve"

def test_non_discounted_product():
    soup = load_mock_soup()
    muz = extract_products_from_page(soup, "Meyve")[1]
    assert muz["regular_price"] is None
    assert muz["is_discounted"] is False
    assert muz["discount_pct"] is None

def test_image_prefers_data_original():
    soup = load_mock_soup()
    products = extract_products_from_page(soup, "Meyve")
    assert products[0]["image_url"] == "https://example.com/domates_hq.jpg"
    assert products[1]["image_url"] == "https://example.com/muz.jpg"


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS  {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {test.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed.")
