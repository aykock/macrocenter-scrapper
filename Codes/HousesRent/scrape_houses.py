import os
import csv
import time
import random  # <-- Add this new import
from datetime import datetime
from bs4 import BeautifulSoup
import undetected_chromedriver as uc

# Configuration
CITIES = {
    'bursa': 'Bursa',
    'yalova': 'Yalova',
    'bilecik': 'Bilecik',
    'kutahya': 'Kütahya'
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../../Datas/HousesRent/"))


def setup_driver():
    """Sets up an undetected Chrome driver with a persistent profile."""
    options = uc.ChromeOptions()

    # Create a persistent profile directory so you stay logged in
    profile_path = os.path.join(SCRIPT_DIR, "SeleniumProfile")
    options.add_argument(f"--user-data-dir={profile_path}")

    # Initialize undetected-chromedriver
    # It automatically handles hiding automation flags, so we need less config
    driver = uc.Chrome(options=options, version_main=145)

    return driver


def scrape_city(driver, city_url_name, folder_name):
    """Scrapes data for a specific city, handling CAPTCHAs and all pages."""

    # GÜNCELLEME 1: URL sonuna ?pagingSize=50 ekleyerek sayfa sayısını azaltıyoruz.
    url = f"https://www.sahibinden.com/kiralik/{city_url_name}?pagingSize=50"

    print(f"\nLoading {url}...")
    driver.get(url)

    all_scraped_data = []
    page_num = 1

    while True:
        # GÜNCELLEME 2: Bekleme süresini 5 saniyeden 2.5 saniyeye düşürdük.
        # Sayfa yüklendikten sonra öğelerin belirmesi için genellikle bu yeterlidir.
        time.sleep(2.5)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        listings = soup.select("#searchResultsTable tbody tr.searchResultsItem")

        # --- CAPTCHA & LOGIN KONTROLÜ ---
        if not listings:
            print("\n" + "=" * 50)
            print("⚠️ İŞLEM GEREKİYOR: İlan bulunamadı.")
            print("Muhtemelen bir CAPTCHA veya Login ekranı çıktı.")
            print("1. Chrome penceresine bak ve bulmacayı çöz veya giriş yap.")
            print("2. İlanları görene kadar bekle.")
            print("=" * 50)
            input("İlanları gördükten sonra buraya gelip ENTER'a bas...")

            # Enter'a bastıktan sonra sayfayı tekrar oku
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            listings = soup.select("#searchResultsTable tbody tr.searchResultsItem")

            if not listings:
                print(f"{folder_name} için hala ilan yok. Atlanıyor.")
                break
        # -----------------------------------

        print(f"{folder_name} için {page_num}. sayfa taranıyor (50'lik liste)...")

        for row in listings:
            try:
                # 1. Fiyat
                price_elem = row.select_one(".searchResultsPriceValue")
                price = price_elem.text.strip() if price_elem else "N/A"

                # 2. Semt / Konum
                location_elem = row.select_one(".searchResultsLocationValue")
                district = location_elem.text.strip().replace('\n', ' ') if location_elem else "N/A"

                # 3. Oda Sayısı
                attributes = row.select(".searchResultsAttributeValue")
                rooms = attributes[0].text.strip() if len(attributes) > 0 else "N/A"

                if price != "N/A" and district != "N/A":
                    all_scraped_data.append({
                        "District": district,
                        "Rooms": rooms,
                        "Price": price
                    })
            except Exception as e:
                print(f"Satır okuma hatası: {e}")
                continue

        # --- SONRAKİ SAYFAYA GEÇİŞ ---
        next_button = soup.find('a', title='Sonraki')

        if next_button and 'href' in next_button.attrs:
            # href bazen tam url, bazen relative url olabilir, sahibinden'de genelde relative'dir.
            next_url = "https://www.sahibinden.com" + next_button['href']

            driver.get(next_url)
            page_num += 1

            # GÜNCELLEME 3: Sayfalar arası bekleme süresini (4-8) saniyeden (2-4) saniyeye çektik.
            # Daha hızlısı riskli olabilir.
            time.sleep(random.uniform(2, 4))
        else:
            print(f"{folder_name} için tüm sayfalar bitti.")
            break
        # ------------------------

    # Verileri kaydet
    if all_scraped_data:
        save_to_csv(folder_name, all_scraped_data)


def save_to_csv(folder_name, data):
    """Saves the scraped data to a daily CSV file in the correct directory."""
    today_str = datetime.now().strftime("%Y-%m-%d")

    target_dir = os.path.join(DATA_BASE_DIR, folder_name)
    os.makedirs(target_dir, exist_ok=True)

    file_path = os.path.join(target_dir, f"{today_str}.csv")

    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=["District", "Rooms", "Price"])
        writer.writeheader()
        writer.writerows(data)

    print(f"Saved {len(data)} records to {file_path}")


def main():
    driver = setup_driver()
    try:
        for city_url_name, folder_name in CITIES.items():
            print(f"\n--- Scraping {folder_name} ---")
            scrape_city(driver, city_url_name, folder_name)
            time.sleep(5)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()