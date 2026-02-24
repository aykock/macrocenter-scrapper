import requests
from bs4 import BeautifulSoup
import csv
import time
import re
import os
from datetime import datetime

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

KATEGORILER = [
    ("Meyve ve Sebze",          "https://www.gurmar.com.tr/meyve-ve-sebze-c"),
    ("Et ve Tavuk",             "https://www.gurmar.com.tr/et-ve-tavuk-urunleri-c"),
    ("Süt, Kahvaltılık, Sark.", "https://www.gurmar.com.tr/sut-kahvaltiliklar-sarkuteri-c"),
    ("Temel Gıda",              "https://www.gurmar.com.tr/temel-gida-c"),
    ("İçecekler",               "https://www.gurmar.com.tr/icecekler-c"),
    ("Atıştırmalıklar",         "https://www.gurmar.com.tr/atistirmaliklar-c"),
    ("Bebek Ürünleri",          "https://www.gurmar.com.tr/bebek-urunleri-c"),
    ("Deterjan ve Temizlik",    "https://www.gurmar.com.tr/deterjan-temizlik-c"),
    ("Kişisel Bakım",           "https://www.gurmar.com.tr/kisisel-bakim-ve-hijyen-c"),
    ("Ev ve Yaşam",             "https://www.gurmar.com.tr/ev-yasam-c"),
    ("Kitap, Kırtasiye",        "https://www.gurmar.com.tr/kitap-kirtasiye-oyuncak-c"),
    ("Petshop",                 "https://www.gurmar.com.tr/petshop-c"),
]


def fiyat_temizle(metin):
    return metin.replace("₺", "").strip()


def kategori_cek(base_url, kategori_adi):
    tum_urunler = []
    gorulmus_href = set()
    beklenen = 0
    sayfa = 1

    while True:
        url = f"{base_url}?page={sayfa}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"  ❌ Hata ({url}): {e}")
            break

        soup = BeautifulSoup(r.text, "html.parser")

        if sayfa == 1:
            sayi_tag = soup.find(string=re.compile(r"ürün listeleniyor", re.IGNORECASE))
            if sayi_tag:
                m = re.search(r"(\d+)", sayi_tag)
                if m:
                    beklenen = int(m.group(1))
                    print(f"  📦 Beklenen: {beklenen}")

        tum_linkler = soup.find_all("a", href=re.compile(r"^/[\w\-]+-\d+-p$"))
        urun_linkleri = [a for a in tum_linkler if a.find("h4")]

        yeni_linkler = []
        for a in urun_linkleri:
            href = a.get("href")
            if href not in gorulmus_href:
                gorulmus_href.add(href)
                yeni_linkler.append(a)

        if not yeni_linkler:
            break

        for a in yeni_linkler:
            h4 = a.find("h4")
            isim = h4.get_text(strip=True) if h4 else a.get_text(strip=True)
            if not isim:
                continue

            kart = a.parent
            fiyat_guncel, fiyat_eski = "", ""
            fiyatlar = [t.strip() for t in kart.stripped_strings if "₺" in t]

            if len(fiyatlar) == 1:
                fiyat_guncel = fiyat_temizle(fiyatlar[0])
            elif len(fiyatlar) >= 2:
                fiyat_guncel = fiyat_temizle(fiyatlar[0])
                fiyat_eski   = fiyat_temizle(fiyatlar[1])

            tum_urunler.append({
                "tarih":         datetime.now().strftime("%Y-%m-%d"),
                "kategori":      kategori_adi,
                "product_name":  isim,
                "product_price": fiyat_guncel,
                "eski_fiyat":    fiyat_eski,
                "url":           "https://www.gurmar.com.tr" + a["href"],
            })

        print(f"  📄 Sayfa {sayfa}: {len(yeni_linkler)} ürün (toplam: {len(tum_urunler)})")

        if len(urun_linkleri) < 25:
            break

        sayfa += 1
        time.sleep(0.5)

    cekilen = len(tum_urunler)
    if beklenen and cekilen == beklenen:
        print(f"  ✅ Başarılı! {cekilen} ürün")
    elif beklenen:
        print(f"  ⚠️  Uyuşmazlık! Beklenen: {beklenen} | Çekilen: {cekilen}")

    return tum_urunler


def main():
    tum_urunler = []

    for kategori_adi, url in KATEGORILER:
        print(f"\n🔍 İşleniyor: {kategori_adi}")
        urunler = kategori_cek(url, kategori_adi)
        tum_urunler.extend(urunler)
        time.sleep(1)

    # Datas/Markets/Gurmar klasörüne kaydet
    bugun = datetime.now().strftime("%Y-%m-%d")
    REPO_KOKU = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    klasor = os.path.join(REPO_KOKU, "Datas", "Markets", "Gurmar")
    os.makedirs(klasor, exist_ok=True)
    csv_dosyasi = os.path.join(klasor, f"gurmar_{bugun}.csv")

    with open(csv_dosyasi, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = ["tarih", "kategori", "product_name", "product_price", "eski_fiyat", "url"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(tum_urunler)

    print(f"\n🎉 Tamamlandı! Toplam {len(tum_urunler)} ürün → '{csv_dosyasi}'")


if __name__ == "__main__":
    main()