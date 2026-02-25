import csv
import os
from datetime import datetime


def scrape_file_market():
    all_data = []

    # Codes/Markets/File/file_scraper.py -> repo root
    repo_root = os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
        )
    )

    output_dir = os.path.join(repo_root, "Datas", "Markets", "File")
    os.makedirs(output_dir, exist_ok=True)

    today_str = datetime.now().strftime("%Y-%m-%d")
    output_file = os.path.join(output_dir, f"file_{today_str}.csv")

    with open(output_file, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Product Name", "Price"])
        writer.writerows(all_data)

    print(f"Created: {output_file}")


if __name__ == "__main__":
    scrape_file_market()