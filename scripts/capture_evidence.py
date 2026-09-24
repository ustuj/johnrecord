from __future__ import annotations

import re
import sys
from base64 import b64encode
from mimetypes import guess_type
from pathlib import Path

from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "ui_check"
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT))
from main import app  # noqa: E402
from models import Order, OrderItem, Product  # noqa: E402
from database import SessionLocal  # noqa: E402

USERS = {
    "client": ("client", "client123"),
    "manager": ("manager", "manager123"),
    "admin": ("admin", "admin123"),
}


def csrf(client: TestClient, path: str) -> str:
    html = client.get(path).text
    match = re.search(r'name="csrf" value="([^"]+)"', html)
    if not match:
        raise RuntimeError(f"CSRF token not found at {path}")
    return match.group(1)


def sign_in(client: TestClient, kind: str) -> None:
    login, password = USERS[kind]
    token = csrf(client, "/login")
    response = client.post(
        "/login",
        data={"login": login, "password": password, "csrf": token},
        follow_redirects=False,
    )
    if response.status_code != 303:
        raise RuntimeError(f"Login failed for {kind}")


def embed_assets(html: str) -> str:
    css = (ROOT / "static/css/style.css").read_text(encoding="utf-8")
    html = html.replace(
        '<link rel="stylesheet" href="/static/css/style.css">',
        f"<style>{css}</style>",
    )

    def replace_src(match: re.Match[str]) -> str:
        src = match.group(1)
        if src.startswith("/static/"):
            path = ROOT / src.lstrip("/")
        elif src.startswith("/media/"):
            path = ROOT / src.lstrip("/")
        else:
            return match.group(0)
        if not path.exists():
            return match.group(0)
        mime = guess_type(str(path))[0] or "application/octet-stream"
        data = b64encode(path.read_bytes()).decode("ascii")
        return f'src="data:{mime};base64,{data}"'

    return re.sub(r'src="([^"]+)"', replace_src, html)


def capture_page(page, filename: str, html: str, full_page: bool = False) -> None:
    page.set_content(embed_assets(html), wait_until="domcontentloaded")
    page.screenshot(path=str(OUT / filename), full_page=full_page)


with TestClient(app) as client:
    # 01 - login
    capture_page(page=None, filename="", html="") if False else None
    login_html = client.get("/login").text

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path="/usr/bin/chromium",
            args=["--no-sandbox"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)

        capture_page(page, "01_login.png", login_html)

        # 02 - wrong credentials / informative message
        token = csrf(client, "/login")
        client.post(
            "/login",
            data={
                "login": "wrong@example.local",
                "password": "wrong",
                "csrf": token,
            },
            follow_redirects=False,
        )
        capture_page(page, "02_login_error.png", client.get("/login").text)

        # 03 - guest catalog
        capture_page(page, "03_guest.png", client.get("/guest").text)

        # 04 - client catalog
        sign_in(client, "client")
        capture_page(page, "04_client.png", client.get("/catalog").text)

        # 05 - manager controls, filtered to Boris so several controls and results are visible
        client = TestClient(app)
        sign_in(client, "manager")
        with SessionLocal() as db:
            boris = db.scalar(select(Product).where(Product.artist == "Boris"))
            supplier_id = boris.supplier_id
        manager_html = client.get(
            "/catalog",
            params={"q": "Boris", "supplier": supplier_id, "stock_sort": "desc"},
        ).text
        capture_page(page, "05_manager_controls.png", manager_html)

        # 06 - manager orders
        capture_page(page, "06_manager_orders.png", client.get("/orders").text)

        # 07 - admin catalog filtered to show a >15% discount and out-of-stock entry
        client = TestClient(app)
        sign_in(client, "admin")
        admin_html = client.get("/catalog", params={"q": "Boris"}).text
        capture_page(page, "07_admin_cards.png", admin_html)

        # 08 - new product form
        capture_page(page, "08_product_new.png", client.get("/admin/product/new").text)

        # 09 - edit an existing product
        with SessionLocal() as db:
            edit_product = db.scalar(select(Product).order_by(Product.product_id.asc()))
        capture_page(page, "09_product_edit.png", client.get(f"/admin/product/{edit_product.product_id}/edit").text)
        client.get(f"/admin/product/{edit_product.product_id}/cancel")

        # 10 - new order form
        capture_page(page, "10_order_new.png", client.get("/admin/order/new").text)

        # 11 - deletion forbidden because product is in an existing order
        with SessionLocal() as db:
            order_item = db.scalar(select(OrderItem).order_by(OrderItem.order_item_id.asc()))
            ordered_product_id = order_item.product_id
        token = csrf(client, "/catalog")
        client.post(
            f"/admin/product/{ordered_product_id}/delete",
            data={"csrf": token},
            follow_redirects=False,
        )
        capture_page(page, "11_forbidden_delete.png", client.get("/catalog").text)

        # 12 - cart with one real album
        with SessionLocal() as db:
            cart_product = db.scalar(
                select(Product).where(Product.stock_quantity > 0).order_by(Product.product_id.asc())
            )
        token = csrf(client, "/catalog")
        client.post(
            "/cart/add",
            data={"csrf": token, "product_id": cart_product.product_id},
            follow_redirects=False,
        )
        capture_page(page, "12_cart.png", client.get("/cart").text)

        browser.close()

print(f"Evidence screenshots written to {OUT}")
