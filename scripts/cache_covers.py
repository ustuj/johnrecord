from __future__ import annotations

import csv
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "processed" / "products.csv"
MEDIA_DIR = ROOT / "media" / "products"


def cache_covers() -> None:
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file, delimiter=";"))
        fieldnames = rows[0].keys() if rows else []

    success = 0
    for row in rows:
        source = row["image_path"]
        target_name = f"{row['article']}.jpg"
        target = MEDIA_DIR / target_name
        if source.startswith(("http://", "https://")):
            try:
                request = Request(source, headers={"User-Agent": "Mozilla/5.0"})
                with urlopen(request, timeout=20) as response:
                    data = response.read()
                target.write_bytes(data)
                row["image_path"] = f"/media/products/{target_name}"
                success += 1
            except Exception as exc:
                print(f"Не удалось скачать {row['article']}: {exc}")

    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Обложек сохранено локально: {success} из {len(rows)}")
    print("После этого выполните: python scripts/init_database.py")


if __name__ == "__main__":
    cache_covers()
