"""
Configuration settings for the Sarıyer Market product scraper.
"""

# ── Base URLs ────────────────────────────────────────────────────────────────
BASE_URL = "https://www.sariyermarket.com"

# Ürün listeleme API endpoint (sayfalı, JSON döner)
PRODUCT_LIST_URL = f"{BASE_URL}/api/products"

# Kategori ağacı endpoint
CATEGORY_API_URL = f"{BASE_URL}/api/categories"

# Alternatif: HTML tabanlı kategori sayfası (API yoksa fallback)
CATEGORY_HTML_URL = f"{BASE_URL}/urunler"

# ── Request Headers ──────────────────────────────────────────────────────────
# Tarayıcı gibi görünmek için gerekli başlıklar — 403 almamak için kritik.
DEFAULT_HEADERS = {
    "Accept":           "application/json, text/html, */*",
    "Accept-Language":  "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding":  "gzip, deflate, br",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer":          BASE_URL + "/",
    "Origin":           BASE_URL,
    "Connection":       "keep-alive",
    "Cache-Control":    "no-cache",
}

# HTML scraping sırasında kullanılan ek başlık
HTML_HEADERS = {
    **DEFAULT_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── Scraping Parametreleri ───────────────────────────────────────────────────
# İstekler arası bekleme süresi (saniye) — rate limit'ten kaçınmak için
REQUEST_DELAY = 0.7

# Başarısız istekte maksimum deneme sayısı
MAX_RETRIES = 3

# Exponential backoff başlangıç süresi (saniye)
RETRY_BACKOFF = 2

# Sayfa başına ürün sayısı (API'nin desteklediği max değer)
PAGE_SIZE = 48

# Sıralama parametresi (varsayılan: önerilen/default)
DEFAULT_SORT = "default"

# ── Çıktı Ayarları ───────────────────────────────────────────────────────────
import datetime as _dt
from pathlib import Path as _Path

_SCRIPTS_DIR  = _Path(__file__).resolve().parent       # …/scripts/
_MARKET_DIR   = _SCRIPTS_DIR.parent                    # …/Sarıyer/
_PROJECT_ROOT = _MARKET_DIR.parent.parent        # …/InflationResearchStudy/

# CSV / JSON çıktı → Datas/Markets/SariyerMarket/
OUTPUT_DIR    = str(_PROJECT_ROOT / "Datas" / "Markets" / "Sarıyer")

# Checkpoint dosyaları → Codes/Markets/SariyerMarket/checkpoints/
CHECKPOINT_DIR = str(_MARKET_DIR / "checkpoints")

# Her günün verisi ayrı dosyaya kaydedilir
_TODAY = _dt.date.today().strftime("%Y-%m-%d")

CSV_OUTPUT_FILE  = str(_Path(OUTPUT_DIR)      / f"sariyermarket_{_TODAY}.csv")
JSON_OUTPUT_FILE = str(_Path(OUTPUT_DIR)      / f"sariyermarket_{_TODAY}.json")
CHECKPOINT_FILE  = str(_Path(CHECKPOINT_DIR)  / f"sariyermarket_checkpoint_{_TODAY}.json")

# ── CSS Seçicileri (HTML scraping için) ─────────────────────────────────────
# Sitenin HTML yapısı değişirse buradan güncellenebilir.
CSS = {
    # Kategori linkleri
    "category_links": "nav.categories a, .category-menu a, .sidebar-categories a",
    # Ürün kartları
    "product_card":   ".product-card, .product-item, article.product",
    # Ürün adı
    "product_name":   ".product-title, .product-name, h2.name, h3.name",
    # Fiyat
    "product_price":  ".price .current, .current-price, span.price",
    # İndirimli fiyat
    "product_old_price": ".old-price, .original-price, s.price",
    # Ürün görseli
    "product_image":  "img.product-image, .product-card img",
    # Ürün linki
    "product_link":   "a.product-card-link, .product-card > a",
    # Sayfalama: sonraki sayfa butonu
    "next_page":      "a[rel='next'], .pagination .next, button.load-more",
}
