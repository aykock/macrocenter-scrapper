import csv
import os
import re
from typing import Optional


DATA_DIR = r"C:\Users\EXCALIBUR\OneDrive\Masaüstü\AI201\InflationResearchStudy\Datas\Markets\Onur"
#change price to float from string

def parse_price_to_float(value: str) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"[\d\.,]+", text)
    if not match:
        return None
    number = match.group(0)
    number = number.replace(".", "").replace(",", ".")
    try:
        return float(number)
    except ValueError:
        return None


def fix_file(path: str) -> int:
    rows = []
    fixed = 0
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return 0
        rows.append(header)
        for row in reader:
            if not row:
                continue
            if len(row) < 3:
                rows.append(row)
                continue
            price_value = parse_price_to_float(row[2])
            if price_value is not None:
                if str(row[2]) != str(price_value):
                    row[2] = price_value
                    fixed += 1
            rows.append(row)

    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    os.replace(temp_path, path)
    return fixed


def main() -> None:
    if not os.path.isdir(DATA_DIR):
        raise SystemExit(f"Missing data directory: {DATA_DIR}")
    total_fixed = 0
    files = [
        os.path.join(DATA_DIR, name)
        for name in os.listdir(DATA_DIR)
        if name.lower().endswith(".csv")
    ]
    if not files:
        print("No CSV files found.")
        return
    for path in sorted(files):
        fixed = fix_file(path)
        total_fixed += fixed
        print(f"Updated {os.path.basename(path)}: {fixed} rows fixed.")
    print(f"Done. Total rows fixed: {total_fixed}")


if __name__ == "__main__":
    main()
