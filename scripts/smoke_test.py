from __future__ import annotations

import io
import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import func, select, text

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from database import SessionLocal, engine
from main import app
from models import Order, OrderItem, PickupPoint, Product, User
from scripts.init_database import seed_database

ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "admin123"
MANAGER_LOGIN = "manager"
MANAGER_PASSWORD = "manager123"
CLIENT_LOGIN = "client"
CLIENT_PASSWORD = "client123"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def get_csrf(client: TestClient, path: str) -> str:
    response = client.get(path)
    assert_true(response.status_code == 200, f"GET {path}: {response.status_code}")
    match = re.search(r'name="csrf" value="([^"]+)"', response.text)
    assert_true(match is not None, f"CSRF token missing on {path}")
    return match.group(1)


def sign_in(client: TestClient, login: str, password: str) -> None:
    token = get_csrf(client, "/login")
    response = client.post(
        "/login",
        data={"login": login, "password": password, "csrf": token},
        follow_redirects=False,
    )
    assert_true(response.status_code == 303, f"Login failed for {login}")
    assert_true(response.headers["location"] == "/catalog", "Unexpected login redirect")


def product_form_data(client: TestClient, product_id: int, csrf: str) -> dict[str, str]:
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        assert_true(product is not None, "Product not found for form test")
    return {
        "csrf": csrf,
        "article": product.article,
        "name": product.name,
        "artist": product.artist,
        "category_id": str(product.category_id),
        "label_id": str(product.label_id),
        "manufacturer_id": str(product.manufacturer_id),
        "supplier_id": str(product.supplier_id),
        "format_id": str(product.format_id),
        "price": str(product.price),
        "unit": product.unit,
        "stock_quantity": str(product.stock_quantity),
        "discount": str(product.discount),
        "description": product.description,
    }


def make_png(seed: int) -> io.BytesIO:
    image = Image.new("RGB", (640, 480), (seed, 40, 80))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    buffer.seek(0)
    return buffer


def main() -> None:
    seed_database()

    with SessionLocal() as db:
        counts = {
            "users": db.scalar(select(func.count(User.user_id))),
            "products": db.scalar(select(func.count(Product.product_id))),
            "orders": db.scalar(select(func.count(Order.order_id))),
            "order_items": db.scalar(select(func.count(OrderItem.order_item_id))),
            "pickup_points": db.scalar(
                select(func.count(PickupPoint.pickup_point_id))
            ),
        }
        assert_true(counts == {"users": 3, "products": 30, "orders": 10, "order_items": 20, "pickup_points": 36}, f"Unexpected import counts: {counts}")
        assert_true(db.execute(text("PRAGMA foreign_keys")).scalar() == 1, "Foreign keys are disabled")

        product_without_image = Product(image_path="")
        product_with_image = db.get(Product, 1)
        assert_true(product_without_image.image_url == "/static/resources/picture.png", "Placeholder is not returned")
        assert_true(
            product_with_image.image_url.startswith(("/media/products/", "http://", "https://")),
            "Product image path is invalid",
        )

    with TestClient(app) as client:
        assert_true(client.get("/").status_code == 200, "Home page failed")
        login_html = client.get("/login").text
        assert_true("Вход" in login_html, "Login page missing heading")
        assert_true(client.get("/guest").status_code == 200, "Guest catalog failed")
        guest_html = client.get("/guest").text
        assert_true("catalog-search" not in guest_html, "Guest sees search controls")
        assert_true("Все поставщики" not in guest_html, "Guest sees supplier filter")
        assert_true("picture.png" in guest_html, "Guest placeholder is not present")
        assert_true("DEMO ACCESS" not in login_html, "Demo access block should be hidden")
        assert_true("Введите логин и пароль из базы данных" not in login_html, "Login helper text should be hidden")
        assert_true("FREE SHIPPING ON VINYL ORDERS" not in login_html, "Announcement bar should be hidden")
        assert_true("CURATED SELECTION" not in guest_html, "English section label should be removed")

        csrf = get_csrf(client, "/login")
        wrong = client.post(
            "/login",
            data={"login": "wrong@example.local", "password": "wrong", "csrf": csrf},
            follow_redirects=False,
        )
        assert_true(wrong.status_code == 303, "Invalid login did not redirect")
        assert_true("Неверный логин или пароль" in client.get("/login").text, "Invalid login warning is missing")

    with TestClient(app) as client:
        sign_in(client, CLIENT_LOGIN, CLIENT_PASSWORD)
        html = client.get("/catalog").text
        assert_true("catalog-search" not in html, "Client sees search controls")
        assert_true("supplier-filter" not in html, "Client sees supplier filter")
        assert_true(client.get("/orders", follow_redirects=False).status_code == 303, "Client can open orders")
        assert_true(client.get("/admin/product/new", follow_redirects=False).status_code == 303, "Client can open admin product form")

    with TestClient(app) as client:
        sign_in(client, MANAGER_LOGIN, MANAGER_PASSWORD)
        with SessionLocal() as db:
            matching_product = db.scalar(select(Product).where(Product.artist == "Boris"))
            assert_true(matching_product is not None, "Real album test product is missing")
            matching_supplier_id = matching_product.supplier_id
        html = client.get(
            "/catalog",
            params={"q": "Boris", "supplier": str(matching_supplier_id), "stock_sort": "desc"},
        ).text
        assert_true("catalog-search" in html, "Manager does not see search")
        assert_true("Boris" in html, "Manager query is not preserved")
        assert_true("supplier-filter" in html, "Manager does not see supplier filter")
        assert_true("stock-sort" in html, "Manager does not see sort")
        assert_true(client.get("/orders").status_code == 200, "Manager cannot view orders")
        orders_html = client.get("/orders").text
        assert_true("Изменить" not in orders_html, "Manager can edit orders")
        fragment = client.get(
            "/api/catalog",
            params={"q": "Boris", "supplier": str(matching_supplier_id), "stock_sort": "desc"},
        )
        assert_true(fragment.status_code == 200, "Manager catalog API failed")
        assert_true("product-card" in fragment.text, "Catalog fragment is empty")
        assert_true("Удалить" not in fragment.text, "Manager should not get admin delete controls")

    with TestClient(app) as client:
        sign_in(client, ADMIN_LOGIN, ADMIN_PASSWORD)
        catalog_html = client.get("/catalog").text
        assert_true("/admin/product/new" in catalog_html, "Admin add-product action missing")
        assert_true("ЗАКАЗЫ" in catalog_html, "Admin Orders button missing")
        assert_true("high-discount" in catalog_html, "High discount styling is missing")
        assert_true("out-of-stock" in catalog_html, "Out-of-stock styling is missing")
        assert_true("picture.png" in catalog_html, "Admin placeholder is missing")

        fragment = client.get("/api/catalog", params={"q": "VNL001"})
        assert_true(fragment.status_code == 200, "Admin catalog API failed")
        assert_true('name="csrf"' in fragment.text, "Admin catalog fragment lost CSRF token")

        add_csrf = get_csrf(client, "/admin/product/new")
        image_one = make_png(200)
        form_data = {
            "csrf": add_csrf,
            "article": "VNL999",
            "name": "QA Pressing",
            "artist": "QA Artist",
            "category_id": "10",
            "label_id": "10",
            "manufacturer_id": "1",
            "supplier_id": "1",
            "format_id": "1",
            "price": "1999.99",
            "unit": "шт.",
            "stock_quantity": "9",
            "discount": "20",
            "description": "Temporary QA record.",
            "is_new": "on",
        }
        created = client.post(
            "/admin/product/new",
            data=form_data,
            files={"image": ("qa-one.png", image_one, "image/png")},
            follow_redirects=False,
        )
        assert_true(created.status_code == 303, "Product add failed")
        with SessionLocal() as db:
            qa_product = db.scalar(select(Product).where(Product.article == "VNL999"))
            assert_true(qa_product is not None, "Added product is missing")
            assert_true(qa_product.product_id == 31, "Product ID was not max + 1")
            first_path = qa_product.image_path
            first_file = root / first_path.lstrip("/")
            assert_true(first_file.exists(), "Uploaded image was not saved")
            with Image.open(first_file) as image:
                assert_true(image.width <= 300 and image.height <= 200, "Image exceeds 300x200")

        edit_html = client.get("/admin/product/31/edit").text
        assert_true("readonly" in edit_html and 'value="31"' in edit_html, "Edit form does not show read-only ID")
        edit_lock = client.get("/admin/product/3/edit", follow_redirects=False)
        assert_true(edit_lock.status_code == 303, "Second edit window was not blocked")
        assert_true("другой пластинки" in client.get("/catalog").text, "Edit lock warning is missing")
        client.get("/admin/product/31/cancel")

        edit_csrf = get_csrf(client, "/admin/product/31/edit")
        image_two = make_png(80)
        changed_data = dict(form_data)
        changed_data.update(
            {
                "csrf": edit_csrf,
                "name": "QA Pressing Updated",
                "stock_quantity": "11",
                "discount": "5",
            }
        )
        changed = client.post(
            "/admin/product/31/edit",
            data=changed_data,
            files={"image": ("qa-two.png", image_two, "image/png")},
            follow_redirects=False,
        )
        assert_true(changed.status_code == 303, "Product edit failed")
        with SessionLocal() as db:
            qa_product = db.scalar(select(Product).where(Product.article == "VNL999"))
            second_path = qa_product.image_path
            second_file = root / second_path.lstrip("/")
            assert_true(second_file.exists(), "Replacement image was not saved")
        assert_true(not first_file.exists(), "Old image was not removed after replacement")

        delete_csrf = get_csrf(client, "/catalog")
        deleted = client.post(
            "/admin/product/31/delete",
            data={"csrf": delete_csrf},
            follow_redirects=False,
        )
        assert_true(deleted.status_code == 303, "Temporary product delete failed")
        assert_true(not second_file.exists(), "Product image was not removed on delete")

        with SessionLocal() as db:
            order_product_id = db.scalar(select(OrderItem.product_id).order_by(OrderItem.order_item_id))
        forbidden_csrf = get_csrf(client, "/catalog")
        forbidden = client.post(
            f"/admin/product/{order_product_id}/delete",
            data={"csrf": forbidden_csrf},
            follow_redirects=False,
        )
        assert_true(forbidden.status_code == 303, "Delete of ordered product did not redirect")
        assert_true("присутствует хотя бы в одном заказе" in client.get("/catalog").text, "Forbidden deletion warning is missing")

        invalid_csrf = get_csrf(client, "/admin/product/new")
        invalid_data = dict(form_data)
        invalid_data.update({"csrf": invalid_csrf, "article": "VNL998", "price": "-1"})
        invalid = client.post("/admin/product/new", data=invalid_data, follow_redirects=False)
        assert_true(invalid.status_code == 303, "Negative price did not redirect")
        assert_true("Цена не может быть отрицательной" in client.get("/admin/product/new").text, "Negative price message is missing")

        order_csrf = get_csrf(client, "/admin/order/new")
        new_order_data = {
            "csrf": order_csrf,
            "order_number": "99",
            "client_id": "3",
            "pickup_point_id": "1",
            "status": "new",
            "order_date": "2026-09-24",
            "delivery_date": "2026-09-26",
            "pickup_code": "999",
            "item_text": "VNL003, 2, VNL004, 1",
        }
        new_order = client.post(
            "/admin/order/new",
            data=new_order_data,
            follow_redirects=False,
        )
        assert_true(new_order.status_code == 303, "Order add failed")
        with SessionLocal() as db:
            qa_order = db.scalar(select(Order).where(Order.order_number == 99))
            assert_true(qa_order is not None, "Added order missing")
            qa_order_id = qa_order.order_id
            assert_true(len(qa_order.items) == 2, "Added order items are wrong")

        order_edit_csrf = get_csrf(client, f"/admin/order/{qa_order_id}/edit")
        edit_order_data = dict(new_order_data)
        edit_order_data.update(
            {
                "csrf": order_edit_csrf,
                "status": "ready",
                "item_text": "VNL005, 1",
            }
        )
        edited_order = client.post(
            f"/admin/order/{qa_order_id}/edit",
            data=edit_order_data,
            follow_redirects=False,
        )
        assert_true(edited_order.status_code == 303, "Order edit failed")
        with SessionLocal() as db:
            qa_order = db.get(Order, qa_order_id)
            assert_true(qa_order.status == "ready", "Order status did not update")
            assert_true(len(qa_order.items) == 1, "Order items did not refresh on edit")
            assert_true(qa_order.items[0].product.article == "VNL005", "Order item did not refresh")

        order_delete_csrf = get_csrf(client, "/orders")
        deleted_order = client.post(
            f"/admin/order/{qa_order_id}/delete",
            data={"csrf": order_delete_csrf},
            follow_redirects=False,
        )
        assert_true(deleted_order.status_code == 303, "Order delete failed")

        with SessionLocal() as db:
            assert_true(db.scalar(select(func.count(Order.order_id))) == 10, "Final order count is not restored")
            assert_true(db.scalar(select(func.count(Product.product_id))) == 30, "Final product count is not restored")

    with TestClient(app) as client:
        assert_true(client.get("/cart").status_code == 200, "Cart page failed")
        token = get_csrf(client, "/login")
        added = client.post("/cart/add", data={"csrf": token, "product_id": "1"}, follow_redirects=False)
        assert_true(added.status_code == 303, "Cart add failed")
        cart_html = client.get("/cart").text
        assert_true("Graduation" in cart_html, "Cart item is missing")
        token = get_csrf(client, "/login")
        removed = client.post("/cart/remove", data={"csrf": token, "product_id": "1"}, follow_redirects=False)
        assert_true(removed.status_code == 303, "Cart remove failed")
        assert_true("Graduation" not in client.get("/cart").text, "Cart item was not removed")

    seed_database()
    print("SMOKE TEST PASS")
    print(counts)


if __name__ == "__main__":
    main()
