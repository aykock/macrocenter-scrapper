from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import subprocess
import random

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
CITIES = {
    "bursa": "Bursa",
    "kutahya": "Kütahya",
    "bilecik": "Bilecik",
    "yalova": "Yalova",
}

PAGE_SIZE = 50
MAX_PAGE = 50

data_dir = "Datas/HousesRent"
os.makedirs(data_dir, exist_ok=True)
OUTPUT_FILE = f"{data_dir}/sahibinden_kiralik_{time.strftime('%Y-%m-%d')}.csv"
LOGIN_URL = "https://www.sahibinden.com/giris"


# ─────────────────────────────────────────
# DRIVER
# ─────────────────────────────────────────
def create_driver(headless: bool = True) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
    )
    return driver


# ─────────────────────────────────────────
# GİRİŞ YAP
# ─────────────────────────────────────────
def login(driver: webdriver.Chrome) -> bool:
    """
    Sahibinden hesabına giriş yapar.
    Başarılıysa True, başarısızsa False döner.
    """
    print("Sahibinden'e giriş yapılıyor…")
    driver.get(LOGIN_URL)

    try:
        wait = WebDriverWait(driver, 20)

        # E-posta alanını bul ve doldur
        email_input = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[name='username'], input[type='email'], #username, #email"))
        )
        email_input.clear()
        email_input.send_keys(SAHIBINDEN_EMAIL)
        time.sleep(random.uniform(0.5, 1.5))

        # Şifre alanını doldur
        password_input = driver.find_element(By.CSS_SELECTOR,
                                             "input[name='password'], input[type='password'], #password")
        password_input.clear()
        password_input.send_keys(SAHIBINDEN_PASSWORD)
        time.sleep(random.uniform(0.5, 1.5))

        # Giriş butonuna tıkla
        submit_btn = driver.find_element(By.CSS_SELECTOR,
                                         "button[type='submit'], input[type='submit'], .login-btn, #login-button")
        submit_btn.click()

        # Giriş başarılı mı? Ana sayfaya yönlendirme bekleniyor
        wait.until(lambda d: "giris" not in d.current_url or "hata" not in d.current_url)
        time.sleep(random.uniform(2, 4))

        # Hâlâ giriş sayfasındaysak başarısız
        if "giris" in driver.current_url:
            print("  ! Giriş başarısız. E-posta/şifre bilgilerini kontrol edin.")
            return False

        print(f"  ✓ Giriş başarılı. URL: {driver.current_url}")
        return True

    except Exception as e:
        print(f"  ! Giriş hatası: {e}")
        # Debug için ekran görüntüsü al
        driver.save_screenshot(f"{data_dir}/debug_login.png")
        print(f"  → Ekran görüntüsü: {data_dir}/debug_login.png")
        return False


# ─────────────────────────────────────────
# SAYFA ÇEK
# ─────────────────────────────────────────
def get_page(driver: webdriver.Chrome, city_slug: str, offset: int) -> BeautifulSoup | None:
    url = (
        f"https://www.sahibinden.com/kiralik-daire/{city_slug}"
        f"?pagingOffset={offset}&pagingSize={PAGE_SIZE}&sorting=date_desc"
    )
    try:
        driver.get(url)
        WebDriverWait(driver, 25).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(random.uniform(2, 4))

        # Giriş sayfasına düşüldü mü?
        if "individual-login-body" in driver.page_source or "giris" in driver.current_url:
            print(f"  ! Oturum sona erdi, tekrar giriş yapılıyor…")
            if not login(driver):
                return None
            driver.get(url)
            time.sleep(random.uniform(2, 4))

        return BeautifulSoup(driver.page_source, "lxml")

    except Exception as e:
        print(f"  ! Sayfa hatası (city={city_slug}, offset={offset}): {e}")
        return None


# ─────────────────────────────────────────
# PARSE
# ─────────────────────────────────────────
def parse_listings(soup: BeautifulSoup, city_name: str) -> list[dict]:
    rows = soup.select("tr.searchResultsItem")
    results = []
    for row in rows:
        try:
            price_tag = row.select_one("td.searchResultsPriceValue")
            price = _parse_price(price_tag.get_text(strip=True) if price_tag else "")

            title_tag = row.select_one("td.searchResultsTitleValue a")
            title = title_tag.get_text(strip=True) if title_tag else ""

            link = ""
            if title_tag and title_tag.get("href"):
                href = title_tag["href"]
                link = ("https://www.sahibinden.com" + href) if href.startswith("/") else href
                link = link.split("?")[0]

            location_tag = row.select_one("td.searchResultsLocationValue")
            location_text = location_tag.get_text(" / ", strip=True) if location_tag else ""
            parts = [p.strip() for p in location_text.split("/")]
            district = parts[1] if len(parts) >= 2 else (parts[0] if parts else "")
            neighbourhood = parts[2] if len(parts) >= 3 else ""

            specs = row.select("td.searchResultsAttributeValue")
            size_m2 = specs[0].get_text(strip=True) if len(specs) >= 1 else ""
            room_count = specs[1].get_text(strip=True) if len(specs) >= 2 else ""

            date_tag = row.select_one("td.searchResultsDateValue")
            listing_date = date_tag.get_text(strip=True) if date_tag else ""

            results.append({
                "City": city_name,
                "District": district,
                "Neighbourhood": neighbourhood,
                "Title": title,
                "RoomCount": room_count,
                "SizeM2": size_m2,
                "Price": price,
                "ListingDate": listing_date,
                "URL": link,
                "ScrapeDate": time.strftime("%Y-%m-%d"),
            })
        except Exception as e:
            print(f"  ! Satır parse hatası: {e}")
    return results


def _parse_price(raw: str) -> float:
    try:
        return float(raw.replace("TL", "").replace(".", "").replace(",", ".").strip())
    except ValueError:
        return 0.0


# ─────────────────────────────────────────
# ŞEHİR SCRAPE
# ─────────────────────────────────────────
def scrape_city(driver: webdriver.Chrome, city_slug: str, city_name: str) -> list[dict]:
    print(f"\n→ Başladı: {city_name}")
    all_listings = []
    offset = 0
    consecutive_empty = 0

    for page_num in range(MAX_PAGE):
        soup = get_page(driver, city_slug, offset)
        if soup is None:
            break

        if page_num == 0:
            for sel in ["strong.resultCount", "span.resultCount strong", ".resultCount"]:
                tag = soup.select_one(sel)
                if tag:
                    try:
                        print(f"  Toplam ilan: ~{int(tag.get_text(strip=True).replace('.', '').replace(',', ''))}")
                    except Exception:
                        pass
                    break

        listings = parse_listings(soup, city_name)

        if not listings:
            consecutive_empty += 1
            if consecutive_empty >= 2:
                break
            print(f"  Sayfa {page_num + 1}: boş")
        else:
            consecutive_empty = 0
            all_listings.extend(listings)
            print(f"  Sayfa {page_num + 1}: {len(listings)} ilan ({len(all_listings)} toplam)")

        offset += PAGE_SIZE
        time.sleep(random.uniform(2, 5))

    print(f"  ✓ {city_name}: {len(all_listings)} ilan")
    return all_listings


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    print(f"Sahibinden Kiralık Daire Scraper – {time.strftime('%Y-%m-%d')}")
    print(f"Şehirler: {', '.join(CITIES.values())}\n")

    # Sorun olursa headless=False yapın → Chrome görünür açılır
    driver = create_driver(headless=True)

    try:
        driver.get("https://www.sahibinden.com/")
        time.sleep(random.uniform(2, 4))

        if not login(driver):
            print("Giriş yapılamadı, script durduruluyor.")
            return

        all_listings = []
        for city_slug, city_name in CITIES.items():
            listings = scrape_city(driver, city_slug, city_name)
            all_listings.extend(listings)
            time.sleep(random.uniform(8, 15))

    finally:
        driver.quit()

    if all_listings:
        df = pd.DataFrame(all_listings)
        df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
        print(f"\n✓ Tamamlandı! {len(all_listings)} ilan → {OUTPUT_FILE}")
        print(df.groupby("City")["Price"].describe().round(0))
    else:
        print("\nHiç ilan bulunamadı.")


def git_push():
    subprocess.run(["git", "pull", "research", "master", "--no-rebase"])
    subprocess.run(["git", "add", "Datas/HousesRent/"])
    subprocess.run(["git", "commit", "-m", f"Sahibinden kiralik data {time.strftime('%Y-%m-%d')}"])
    subprocess.run(["git", "push", "research", "master"])


if __name__ == "__main__":
    main()
    git_push()