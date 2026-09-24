from __future__ import annotations

import io
import secrets
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload
from starlette.middleware.sessions import SessionMiddleware

from database import SessionLocal
from models import (
    Category,
    Label,
    Manufacturer,
    Order,
    OrderItem,
    PickupPoint,
    Product,
    RecordFormat,
    Supplier,
    User,
)
from security import verify_password

base_dir = Path(__file__).resolve().parent
media_dir = base_dir / "media"
product_media_dir = media_dir / "products"
product_media_dir.mkdir(parents=True, exist_ok=True)

templates = Environment(
    loader=FileSystemLoader(str(base_dir / "templates")),
    autoescape=select_autoescape(["html"]),
)
templates.globals["money"] = (
    lambda value: f"{Decimal(str(value)):.2f}".replace(".", ",") + " ₽"
)
templates.globals["status_label"] = {
    "new": "Новый",
    "processing": "В обработке",
    "ready": "Готов к выдаче",
    "completed": "Завершен",
    "cancelled": "Отменен",
}.get

app = FastAPI(title="USTUJ RECORDS")
app.add_middleware(
    SessionMiddleware,
    secret_key="vinyl-records-demo-session-key",
    max_age=8 * 60 * 60,
)
app.mount("/static", StaticFiles(directory=base_dir / "static"), name="static")
app.mount("/media", StaticFiles(directory=media_dir), name="media")

role_labels = {
    "client": "Авторизированный клиент",
    "manager": "Менеджер",
    "admin": "Администратор",
}
status_values = ("new", "processing", "ready", "completed", "cancelled")
section_names = {
    "new": "Новинки",
    "bestsellers": "Бестселлеры",
    "staff": "Выбор команды",
    "color": "Цветной винил",
    "preorder": "Предзаказ",
}


def csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(24)
        request.session["csrf_token"] = token
    return token


def valid_csrf(request: Request, token: str) -> bool:
    stored = request.session.get("csrf_token", "")
    return bool(token) and secrets.compare_digest(stored, token)


def current_user(request: Request) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    with SessionLocal() as db:
        return db.get(User, user_id)


def flash(request: Request, level: str, message: str) -> None:
    request.session.setdefault("flash", []).append(
        {"level": level, "message": message}
    )


def pop_flash(request: Request) -> list[dict[str, str]]:
    items = request.session.get("flash", [])
    request.session["flash"] = []
    return items


def render(
    template_name: str,
    request: Request,
    context: dict | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    context = context or {}
    user = current_user(request)
    cart = request.session.get("cart", {})
    cart_count = 0
    for quantity in cart.values():
        try:
            cart_count += int(quantity)
        except (TypeError, ValueError):
            continue

    context.update(
        {
            "request": request,
            "current_user": user,
            "role": user.role if user else "guest",
            "role_label": role_labels.get(user.role, "Гость") if user else "Гость",
            "flash_messages": pop_flash(request),
            "csrf_token": csrf_token(request),
            "cart_count": cart_count,
            "show_footer": context.get("show_footer", True),
        }
    )
    return HTMLResponse(
        templates.get_template(template_name).render(**context),
        status_code=status_code,
    )


def require_role(request: Request, allowed: Iterable[str]) -> User | None:
    user = current_user(request)
    if not user:
        return None
    return user if user.role in allowed else None


def product_query(
    db: Session,
    request: Request,
    controls_enabled: bool,
):
    stmt = select(Product).options(
        joinedload(Product.category),
        joinedload(Product.label),
        joinedload(Product.manufacturer),
        joinedload(Product.supplier),
        joinedload(Product.record_format),
    )

    query = request.query_params.get("q", "").strip()
    supplier_id = request.query_params.get("supplier", "").strip()
    stock_sort = request.query_params.get("stock_sort", "").strip()
    section = request.query_params.get("section", "").strip()

    if controls_enabled and query:
        term = f"%{query}%"
        stmt = (
            stmt.join(Product.category)
            .join(Product.label)
            .join(Product.manufacturer)
            .join(Product.supplier)
            .join(Product.record_format)
            .where(
                or_(
                    Product.article.ilike(term),
                    Product.name.ilike(term),
                    Product.artist.ilike(term),
                    Product.description.ilike(term),
                    Product.unit.ilike(term),
                    Category.name.ilike(term),
                    Label.name.ilike(term),
                    Manufacturer.name.ilike(term),
                    Supplier.name.ilike(term),
                    RecordFormat.name.ilike(term),
                )
            )
        )

    if controls_enabled and supplier_id.isdigit() and int(supplier_id) > 0:
        stmt = stmt.where(Product.supplier_id == int(supplier_id))

    if controls_enabled:
        section_column = {
            "new": Product.is_new,
            "bestsellers": Product.is_bestseller,
            "staff": Product.is_staff_pick,
            "color": Product.is_color_vinyl,
            "preorder": Product.is_preorder,
        }.get(section)
        if section_column is not None:
            stmt = stmt.where(section_column.is_(True))

    if controls_enabled and stock_sort == "asc":
        stmt = stmt.order_by(Product.stock_quantity.asc(), Product.product_id.asc())
    elif controls_enabled and stock_sort == "desc":
        stmt = stmt.order_by(Product.stock_quantity.desc(), Product.product_id.asc())
    elif section == "new":
        stmt = stmt.order_by(Product.product_id.desc())
    else:
        stmt = stmt.order_by(Product.product_id.asc())

    return stmt, query, supplier_id, stock_sort, section


def required_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name}: поле не должно быть пустым.")
    return cleaned


def parse_money(value: str) -> Decimal:
    try:
        amount = Decimal(value.replace(",", ".")).quantize(Decimal("0.01"))
    except (InvalidOperation, AttributeError):
        raise ValueError("Цена: укажите корректное число.") from None
    if amount < 0:
        raise ValueError("Цена не может быть отрицательной.")
    return amount


def parse_nonnegative_int(
    value: str,
    field_name: str,
    allow_zero: bool = True,
) -> int:
    try:
        number = int(value)
    except (ValueError, TypeError):
        raise ValueError(f"{field_name}: укажите целое число.") from None
    if number < 0 or (not allow_zero and number == 0):
        raise ValueError(f"{field_name}: значение не может быть отрицательным.")
    return number


def store_image(upload: UploadFile | None) -> str:
    if not upload or not upload.filename:
        return ""

    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    suffix = Path(upload.filename).suffix.lower()
    if suffix not in allowed:
        raise ValueError("Изображение: используйте JPG, PNG или WEBP.")

    payload = upload.file.read()
    if not payload:
        raise ValueError("Изображение: файл пустой.")

    filename = f"{uuid.uuid4().hex}.jpg"
    target = product_media_dir / filename
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image = image.convert("RGB")
            image.thumbnail((300, 200), Image.Resampling.LANCZOS)
            image.save(target, "JPEG", quality=88, optimize=True)
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise ValueError(
            "Изображение: не удалось обработать файл."
        ) from exc

    return f"/media/products/{filename}"


def remove_product_image(image_path: str) -> None:
    if not image_path.startswith("/media/products/"):
        return
    (base_dir / image_path.lstrip("/")).unlink(missing_ok=True)




def get_cart_items(request: Request) -> tuple[list[dict], Decimal]:
    raw_cart = request.session.get("cart", {})
    if not isinstance(raw_cart, dict):
        raw_cart = {}

    product_ids = []
    quantities: dict[int, int] = {}
    for raw_product_id, raw_quantity in raw_cart.items():
        try:
            product_id = int(raw_product_id)
            quantity = int(raw_quantity)
        except (TypeError, ValueError):
            continue
        if product_id > 0 and quantity > 0:
            product_ids.append(product_id)
            quantities[product_id] = quantity

    if not product_ids:
        request.session["cart"] = {}
        return [], Decimal("0.00")

    with SessionLocal() as db:
        products = db.scalars(
            select(Product)
            .options(
                joinedload(Product.category),
                joinedload(Product.supplier),
                joinedload(Product.record_format),
            )
            .where(Product.product_id.in_(product_ids))
        ).all()

    items = []
    total = Decimal("0.00")
    valid_cart: dict[str, int] = {}
    for product in products:
        requested_quantity = quantities.get(product.product_id, 0)
        if product.stock_quantity <= 0:
            continue
        quantity = min(requested_quantity, product.stock_quantity)
        if quantity <= 0:
            continue
        valid_cart[str(product.product_id)] = quantity
        items.append({"product": product, "quantity": quantity})
        total += product.discounted_price * quantity

    request.session["cart"] = valid_cart
    return items, total

def form_context(db: Session) -> dict:
    return {
        "suppliers": db.scalars(select(Supplier).order_by(Supplier.name)).all(),
        "manufacturers": db.scalars(
            select(Manufacturer).order_by(Manufacturer.name)
        ).all(),
        "categories": db.scalars(select(Category).order_by(Category.name)).all(),
        "labels": db.scalars(select(Label).order_by(Label.name)).all(),
        "formats": db.scalars(
            select(RecordFormat).order_by(RecordFormat.format_id)
        ).all(),
    }


def parse_article_items(raw: str) -> list[tuple[int, int]]:
    chunks = [item.strip() for item in raw.split(",") if item.strip()]
    if len(chunks) % 2 != 0:
        raise ValueError(
            "Артикул заказа: используйте формат «VNL001, 2, VNL002, 1»."
        )

    values: list[tuple[int, int]] = []
    with SessionLocal() as db:
        for index in range(0, len(chunks), 2):
            article = chunks[index].upper()
            quantity = parse_nonnegative_int(
                chunks[index + 1], "Количество", allow_zero=False
            )
            product = db.scalar(select(Product).where(Product.article == article))
            if not product:
                raise ValueError(f"Артикул заказа: товар «{article}» не найден.")
            values.append((product.product_id, quantity))

    if not values:
        raise ValueError("Артикул заказа: добавьте хотя бы один товар.")

    if len({product_id for product_id, _ in values}) != len(values):
        raise ValueError(
            "Артикул заказа: один товар указан несколько раз. "
            "Объедините количества в одну строку."
        )
    return values


def format_order_items(order: Order) -> str:
    return ", ".join(
        f"{item.product.article}, {item.quantity}" for item in order.items
    )


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return RedirectResponse("/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return render("login.html", request, {"title": "Вход", "show_footer": False})


@app.post("/login")
def login(
    request: Request,
    login: str = Form(...),
    password: str = Form(...),
    csrf: str = Form(...),
):
    if not valid_csrf(request, csrf):
        flash(
            request,
            "error",
            "Сессия устарела. Перезагрузите страницу входа и повторите попытку.",
        )
        return RedirectResponse("/login", status_code=303)

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.login == login.strip()))
        if not user or not verify_password(password, user.password_hash):
            flash(
                request,
                "error",
                "Неверный логин или пароль. Проверьте данные и повторите ввод.",
            )
            return RedirectResponse("/login", status_code=303)
        request.session["user_id"] = user.user_id
        request.session.pop("product_edit_lock", None)

    return RedirectResponse("/catalog", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/guest", response_class=HTMLResponse)
def guest_catalog(request: Request):
    with SessionLocal() as db:
        stmt, _, _, _, section = product_query(db, request, controls_enabled=False)
        products = db.scalars(stmt).unique().all()
    return render(
        "catalog.html",
        request,
        {
            "title": "Каталог",
            "products": products,
            "controls_enabled": False,
            "guest_mode": True,
            "section": section,
            "section_name": section_names.get(section),
        },
    )


@app.get("/catalog", response_class=HTMLResponse)
def catalog(request: Request):
    user = require_role(request, {"client", "manager", "admin"})
    if not user:
        return RedirectResponse("/login", status_code=303)

    controls_enabled = user.role in {"manager", "admin"}
    with SessionLocal() as db:
        stmt, query, supplier_id, stock_sort, section = product_query(
            db, request, controls_enabled
        )
        products = db.scalars(stmt).unique().all()
        suppliers = db.scalars(select(Supplier).order_by(Supplier.name)).all()

    return render(
        "catalog.html",
        request,
        {
            "title": "Каталог",
            "products": products,
            "controls_enabled": controls_enabled,
            "guest_mode": False,
            "section": section,
            "section_name": section_names.get(section),
            "search": query,
            "selected_supplier": supplier_id,
            "stock_sort": stock_sort,
            "suppliers": suppliers,
        },
    )


@app.get("/api/catalog", response_class=HTMLResponse)
def catalog_fragment(request: Request):
    user = require_role(request, {"manager", "admin"})
    if not user:
        return HTMLResponse("Недостаточно прав", status_code=403)

    with SessionLocal() as db:
        stmt, _, _, _, _ = product_query(db, request, controls_enabled=True)
        products = db.scalars(stmt).unique().all()

    return HTMLResponse(
        templates.get_template("partials/product_grid.html").render(
            products=products,
            role=user.role,
            current_user=user,
            csrf_token=csrf_token(request),
        )
    )




@app.get("/cart", response_class=HTMLResponse)
def cart_page(request: Request):
    items, total = get_cart_items(request)
    return render(
        "cart.html",
        request,
        {"title": "Корзина", "items": items, "total": total},
    )


@app.post("/cart/add")
def cart_add(
    request: Request,
    product_id: str = Form(...),
    csrf: str = Form(...),
):
    if not valid_csrf(request, csrf):
        flash(request, "error", "Сессия устарела. Повторите действие.")
        return RedirectResponse("/catalog", status_code=303)

    try:
        product_id_value = int(product_id)
    except (TypeError, ValueError):
        flash(request, "error", "Товар не найден.")
        return RedirectResponse("/catalog", status_code=303)

    with SessionLocal() as db:
        product = db.get(Product, product_id_value)
        if not product:
            flash(request, "error", "Товар не найден.")
            return RedirectResponse("/catalog", status_code=303)
        if product.stock_quantity <= 0:
            flash(request, "warning", "Нельзя добавить товар: пластинки нет на складе.")
            return RedirectResponse(f"/product/{product_id_value}", status_code=303)

    cart = request.session.setdefault("cart", {})
    key = str(product_id_value)
    current_quantity = int(cart.get(key, 0))
    if current_quantity >= product.stock_quantity:
        flash(request, "warning", "В корзине уже находится максимальное доступное количество.")
    else:
        cart[key] = current_quantity + 1
        request.session["cart"] = cart
        flash(request, "success", f"«{product.name}» добавлена в корзину.")
    return RedirectResponse(request.headers.get("referer", "/catalog"), status_code=303)


@app.post("/cart/update")
def cart_update(
    request: Request,
    product_id: str = Form(...),
    quantity: str = Form(...),
    csrf: str = Form(...),
):
    if not valid_csrf(request, csrf):
        flash(request, "error", "Сессия устарела. Повторите действие.")
        return RedirectResponse("/cart", status_code=303)

    try:
        product_id_value = int(product_id)
        quantity_value = int(quantity)
    except (TypeError, ValueError):
        flash(request, "error", "Количество должно быть целым числом.")
        return RedirectResponse("/cart", status_code=303)

    with SessionLocal() as db:
        product = db.get(Product, product_id_value)
        if not product:
            flash(request, "error", "Товар не найден.")
            return RedirectResponse("/cart", status_code=303)
        if quantity_value < 1 or quantity_value > product.stock_quantity:
            flash(request, "error", f"Для этого товара доступно от 1 до {product.stock_quantity} шт.")
            return RedirectResponse("/cart", status_code=303)

    cart = request.session.setdefault("cart", {})
    cart[str(product_id_value)] = quantity_value
    request.session["cart"] = cart
    flash(request, "success", "Количество в корзине обновлено.")
    return RedirectResponse("/cart", status_code=303)


@app.post("/cart/remove")
def cart_remove(
    request: Request,
    product_id: str = Form(...),
    csrf: str = Form(...),
):
    if not valid_csrf(request, csrf):
        flash(request, "error", "Сессия устарела. Повторите действие.")
        return RedirectResponse("/cart", status_code=303)
    cart = request.session.setdefault("cart", {})
    cart.pop(str(product_id), None)
    request.session["cart"] = cart
    flash(request, "success", "Товар удалён из корзины.")
    return RedirectResponse("/cart", status_code=303)


@app.post("/cart/clear")
def cart_clear(request: Request, csrf: str = Form(...)):
    if not valid_csrf(request, csrf):
        flash(request, "error", "Сессия устарела. Повторите действие.")
        return RedirectResponse("/cart", status_code=303)
    request.session["cart"] = {}
    flash(request, "success", "Корзина очищена.")
    return RedirectResponse("/cart", status_code=303)


@app.get("/product/{product_id}", response_class=HTMLResponse)
def product_detail(request: Request, product_id: int):
    with SessionLocal() as db:
        product = db.scalar(
            select(Product)
            .options(
                joinedload(Product.category),
                joinedload(Product.label),
                joinedload(Product.manufacturer),
                joinedload(Product.supplier),
                joinedload(Product.record_format),
            )
            .where(Product.product_id == product_id)
        )
        if not product:
            return render(
                "error.html",
                request,
                {
                    "title": "Товар не найден",
                    "message": "Пластинка не найдена. Вернитесь в каталог и выберите другой товар.",
                },
                404,
            )
    return render(
        "product_detail.html",
        request,
        {"title": product.name, "product": product},
    )


@app.get("/admin/product/new", response_class=HTMLResponse)
def product_new_page(request: Request):
    if not require_role(request, {"admin"}):
        flash(request, "error", "Добавлять товары может только администратор.")
        return RedirectResponse("/catalog", status_code=303)

    with SessionLocal() as db:
        next_id = (db.scalar(select(func.max(Product.product_id))) or 0) + 1
        context = form_context(db)

    return render(
        "product_form.html",
        request,
        {
            "title": "Добавление пластинки",
            "mode": "Добавление",
            "product": None,
            "next_id": next_id,
            **context,
        },
    )


@app.post("/admin/product/new")
def product_new_submit(
    request: Request,
    csrf: str = Form(...),
    article: str = Form(...),
    name: str = Form(...),
    artist: str = Form(...),
    category_id: str = Form(...),
    label_id: str = Form(...),
    manufacturer_id: str = Form(...),
    supplier_id: str = Form(...),
    format_id: str = Form(...),
    price: str = Form(...),
    unit: str = Form(...),
    stock_quantity: str = Form(...),
    discount: str = Form(...),
    description: str = Form(""),
    is_new: str | None = Form(None),
    is_bestseller: str | None = Form(None),
    is_staff_pick: str | None = Form(None),
    is_preorder: str | None = Form(None),
    is_color_vinyl: str | None = Form(None),
    image: UploadFile | None = File(None),
):
    if not require_role(request, {"admin"}):
        flash(request, "error", "Недостаточно прав для добавления товара.")
        return RedirectResponse("/catalog", status_code=303)
    if not valid_csrf(request, csrf):
        flash(request, "error", "Сессия устарела. Повторите действие.")
        return RedirectResponse("/catalog", status_code=303)

    product_image = ""
    try:
        product_image = store_image(image)
        with SessionLocal() as db:
            next_id = (db.scalar(select(func.max(Product.product_id))) or 0) + 1
            product = Product(
                product_id=next_id,
                article=required_text(article, "Артикул"),
                name=required_text(name, "Наименование товара"),
                artist=required_text(artist, "Исполнитель / артист"),
                category_id=parse_nonnegative_int(category_id, "Категория", False),
                label_id=parse_nonnegative_int(label_id, "Лейбл", False),
                manufacturer_id=parse_nonnegative_int(
                    manufacturer_id, "Производитель", False
                ),
                supplier_id=parse_nonnegative_int(supplier_id, "Поставщик", False),
                format_id=parse_nonnegative_int(format_id, "Формат", False),
                price=parse_money(price),
                unit=required_text(unit, "Единица измерения"),
                stock_quantity=parse_nonnegative_int(
                    stock_quantity, "Количество на складе"
                ),
                discount=parse_nonnegative_int(discount, "Скидка"),
                description=description.strip(),
                image_path=product_image,
                is_new=is_new is not None,
                is_bestseller=is_bestseller is not None,
                is_staff_pick=is_staff_pick is not None,
                is_preorder=is_preorder is not None,
                is_color_vinyl=is_color_vinyl is not None,
            )
            db.add(product)
            db.commit()
    except ValueError as exc:
        if product_image:
            remove_product_image(product_image)
        flash(request, "error", str(exc))
        return RedirectResponse("/admin/product/new", status_code=303)
    except Exception:
        if product_image:
            remove_product_image(product_image)
        flash(
            request,
            "error",
            "Не удалось добавить товар. Проверьте уникальность артикула и обязательные поля.",
        )
        return RedirectResponse("/admin/product/new", status_code=303)

    flash(request, "success", "Пластинка добавлена. Список каталога обновлен.")
    return RedirectResponse("/catalog", status_code=303)


@app.get("/admin/product/{product_id}/edit", response_class=HTMLResponse)
def product_edit_page(request: Request, product_id: int):
    if not require_role(request, {"admin"}):
        flash(request, "error", "Редактировать товары может только администратор.")
        return RedirectResponse("/catalog", status_code=303)

    lock = request.session.get("product_edit_lock")
    if lock and int(lock) != product_id:
        flash(
            request,
            "warning",
            "Уже открыта форма редактирования другой пластинки. "
            "Сохраните или отмените текущую форму перед открытием следующей.",
        )
        return RedirectResponse("/catalog", status_code=303)

    request.session["product_edit_lock"] = product_id
    with SessionLocal() as db:
        product = db.scalar(select(Product).where(Product.product_id == product_id))
        if not product:
            request.session.pop("product_edit_lock", None)
            return render(
                "error.html",
                request,
                {
                    "title": "Товар не найден",
                    "message": "Пластинка для редактирования не найдена.",
                },
                404,
            )
        context = form_context(db)

    return render(
        "product_form.html",
        request,
        {
            "title": "Редактирование пластинки",
            "mode": "Редактирование",
            "product": product,
            "next_id": product.product_id,
            **context,
        },
    )


@app.post("/admin/product/{product_id}/edit")
def product_edit_submit(
    request: Request,
    product_id: int,
    csrf: str = Form(...),
    article: str = Form(...),
    name: str = Form(...),
    artist: str = Form(...),
    category_id: str = Form(...),
    label_id: str = Form(...),
    manufacturer_id: str = Form(...),
    supplier_id: str = Form(...),
    format_id: str = Form(...),
    price: str = Form(...),
    unit: str = Form(...),
    stock_quantity: str = Form(...),
    discount: str = Form(...),
    description: str = Form(""),
    is_new: str | None = Form(None),
    is_bestseller: str | None = Form(None),
    is_staff_pick: str | None = Form(None),
    is_preorder: str | None = Form(None),
    is_color_vinyl: str | None = Form(None),
    image: UploadFile | None = File(None),
):
    if not require_role(request, {"admin"}):
        flash(request, "error", "Недостаточно прав для редактирования товара.")
        return RedirectResponse("/catalog", status_code=303)
    if not valid_csrf(request, csrf):
        flash(request, "error", "Сессия устарела. Повторите действие.")
        return RedirectResponse("/catalog", status_code=303)
    if request.session.get("product_edit_lock") not in (None, product_id):
        flash(request, "warning", "Форма редактирования уже занята другой пластинкой.")
        return RedirectResponse("/catalog", status_code=303)

    new_image = ""
    old_image = ""
    try:
        if image and image.filename:
            new_image = store_image(image)

        with SessionLocal() as db:
            product = db.get(Product, product_id)
            if not product:
                raise ValueError("Пластинка не найдена.")

            old_image = product.image_path
            product.article = required_text(article, "Артикул")
            product.name = required_text(name, "Наименование товара")
            product.artist = required_text(artist, "Исполнитель / артист")
            product.category_id = parse_nonnegative_int(
                category_id, "Категория", False
            )
            product.label_id = parse_nonnegative_int(label_id, "Лейбл", False)
            product.manufacturer_id = parse_nonnegative_int(
                manufacturer_id, "Производитель", False
            )
            product.supplier_id = parse_nonnegative_int(
                supplier_id, "Поставщик", False
            )
            product.format_id = parse_nonnegative_int(format_id, "Формат", False)
            product.price = parse_money(price)
            product.unit = unit.strip() or "шт."
            product.stock_quantity = parse_nonnegative_int(
                stock_quantity, "Количество на складе"
            )
            product.discount = parse_nonnegative_int(discount, "Скидка")
            product.description = description.strip()
            product.is_new = is_new is not None
            product.is_bestseller = is_bestseller is not None
            product.is_staff_pick = is_staff_pick is not None
            product.is_preorder = is_preorder is not None
            product.is_color_vinyl = is_color_vinyl is not None
            if new_image:
                product.image_path = new_image
            db.commit()

        if new_image and old_image and old_image != new_image:
            remove_product_image(old_image)
    except ValueError as exc:
        if new_image:
            remove_product_image(new_image)
        flash(request, "error", str(exc))
        return RedirectResponse(
            f"/admin/product/{product_id}/edit", status_code=303
        )
    except Exception:
        if new_image:
            remove_product_image(new_image)
        flash(
            request,
            "error",
            "Не удалось сохранить изменения. Проверьте уникальность артикула и заполнение полей.",
        )
        return RedirectResponse(
            f"/admin/product/{product_id}/edit", status_code=303
        )

    request.session.pop("product_edit_lock", None)
    flash(request, "success", "Изменения сохранены. Список товаров обновлен.")
    return RedirectResponse("/catalog", status_code=303)


@app.get("/admin/product/{product_id}/cancel")
def product_edit_cancel(request: Request, product_id: int):
    if request.session.get("product_edit_lock") == product_id:
        request.session.pop("product_edit_lock", None)
    return RedirectResponse("/catalog", status_code=303)


@app.post("/admin/product/{product_id}/delete")
def product_delete(
    request: Request,
    product_id: int,
    csrf: str = Form(...),
):
    if not require_role(request, {"admin"}):
        flash(request, "error", "Удалять товары может только администратор.")
        return RedirectResponse("/catalog", status_code=303)
    if not valid_csrf(request, csrf):
        flash(request, "error", "Сессия устарела. Повторите действие.")
        return RedirectResponse("/catalog", status_code=303)

    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if not product:
            flash(request, "error", "Товар не найден.")
            return RedirectResponse("/catalog", status_code=303)
        if db.scalar(
            select(func.count(OrderItem.order_item_id)).where(
                OrderItem.product_id == product_id
            )
        ):
            flash(
                request,
                "warning",
                "Удаление запрещено: эта пластинка присутствует хотя бы в одном заказе.",
            )
            return RedirectResponse("/catalog", status_code=303)

        image_path = product.image_path
        db.delete(product)
        db.commit()

    remove_product_image(image_path)
    flash(request, "success", "Пластинка удалена. Список товаров обновлен.")
    return RedirectResponse("/catalog", status_code=303)


@app.get("/orders", response_class=HTMLResponse)
def orders(request: Request):
    user = require_role(request, {"manager", "admin"})
    if not user:
        flash(request, "error", "Раздел «Заказы» доступен менеджеру и администратору.")
        return RedirectResponse("/catalog", status_code=303)

    with SessionLocal() as db:
        order_list = db.scalars(
            select(Order)
            .options(
                joinedload(Order.client),
                joinedload(Order.pickup_point),
                joinedload(Order.items).joinedload(OrderItem.product),
            )
            .order_by(Order.order_number.asc())
        ).unique().all()

    return render(
        "orders.html",
        request,
        {
            "title": "Заказы",
            "orders": order_list,
            "can_edit": user.role == "admin",
        },
    )


@app.get("/admin/order/new", response_class=HTMLResponse)
def order_new_page(request: Request):
    if not require_role(request, {"admin"}):
        flash(request, "error", "Добавлять заказы может только администратор.")
        return RedirectResponse("/orders", status_code=303)

    with SessionLocal() as db:
        next_number = (db.scalar(select(func.max(Order.order_number))) or 0) + 1
        clients = db.scalars(select(User).order_by(User.full_name)).all()
        pickup_points = db.scalars(
            select(PickupPoint).order_by(PickupPoint.pickup_point_id)
        ).all()

    return render(
        "order_form.html",
        request,
        {
            "title": "Добавление заказа",
            "mode": "Добавление",
            "order": None,
            "next_number": next_number,
            "clients": clients,
            "pickup_points": pickup_points,
            "status_values": status_values,
            "item_text": "",
        },
    )


@app.post("/admin/order/new")
def order_new_submit(
    request: Request,
    csrf: str = Form(...),
    order_number: str = Form(...),
    client_id: str = Form(...),
    pickup_point_id: str = Form(...),
    status: str = Form(...),
    order_date: str = Form(...),
    delivery_date: str = Form(...),
    pickup_code: str = Form(...),
    item_text: str = Form(...),
):
    if not require_role(request, {"admin"}):
        flash(request, "error", "Добавлять заказы может только администратор.")
        return RedirectResponse("/orders", status_code=303)
    if not valid_csrf(request, csrf):
        flash(request, "error", "Сессия устарела. Повторите действие.")
        return RedirectResponse("/orders", status_code=303)

    try:
        items = parse_article_items(item_text)
        order_number_i = parse_nonnegative_int(
            order_number, "Номер заказа", allow_zero=False
        )
        client_i = parse_nonnegative_int(client_id, "Клиент", allow_zero=False)
        pickup_i = parse_nonnegative_int(
            pickup_point_id, "Пункт выдачи", allow_zero=False
        )
        code_i = parse_nonnegative_int(pickup_code, "Код получения")
        if status not in status_values:
            raise ValueError("Статус заказа: выберите значение из списка.")

        order_date_value = date.fromisoformat(order_date)
        delivery_date_value = (
            date.fromisoformat(delivery_date) if delivery_date else None
        )
        if delivery_date_value and delivery_date_value < order_date_value:
            raise ValueError("Дата выдачи не может быть раньше даты заказа.")

        with SessionLocal() as db:
            order = Order(
                order_id=(db.scalar(select(func.max(Order.order_id))) or 0) + 1,
                order_number=order_number_i,
                client_id=client_i,
                pickup_point_id=pickup_i,
                order_date=order_date_value,
                delivery_date=delivery_date_value,
                pickup_code=code_i,
                status=status,
            )
            db.add(order)
            db.flush()
            for product_id, quantity in items:
                product = db.get(Product, product_id)
                order.items.append(
                    OrderItem(
                        product_id=product_id,
                        quantity=quantity,
                        unit_price=product.discounted_price,
                    )
                )
            db.commit()
    except (ValueError, TypeError) as exc:
        flash(request, "error", str(exc))
        return RedirectResponse("/admin/order/new", status_code=303)
    except Exception:
        flash(
            request,
            "error",
            "Не удалось добавить заказ. Проверьте номер заказа и связанные данные.",
        )
        return RedirectResponse("/admin/order/new", status_code=303)

    flash(request, "success", "Заказ добавлен. Список заказов обновлен.")
    return RedirectResponse("/orders", status_code=303)


@app.get("/admin/order/{order_id}/edit", response_class=HTMLResponse)
def order_edit_page(request: Request, order_id: int):
    if not require_role(request, {"admin"}):
        flash(request, "error", "Редактировать заказы может только администратор.")
        return RedirectResponse("/orders", status_code=303)

    with SessionLocal() as db:
        order = db.scalar(
            select(Order)
            .options(joinedload(Order.items).joinedload(OrderItem.product))
            .where(Order.order_id == order_id)
        )
        clients = db.scalars(select(User).order_by(User.full_name)).all()
        pickup_points = db.scalars(
            select(PickupPoint).order_by(PickupPoint.pickup_point_id)
        ).all()

    if not order:
        return render(
            "error.html",
            request,
            {
                "title": "Заказ не найден",
                "message": "Заказ для редактирования не найден.",
            },
            404,
        )

    return render(
        "order_form.html",
        request,
        {
            "title": "Редактирование заказа",
            "mode": "Редактирование",
            "order": order,
            "next_number": order.order_number,
            "clients": clients,
            "pickup_points": pickup_points,
            "status_values": status_values,
            "item_text": format_order_items(order),
        },
    )


@app.post("/admin/order/{order_id}/edit")
def order_edit_submit(
    request: Request,
    order_id: int,
    csrf: str = Form(...),
    order_number: str = Form(...),
    client_id: str = Form(...),
    pickup_point_id: str = Form(...),
    status: str = Form(...),
    order_date: str = Form(...),
    delivery_date: str = Form(...),
    pickup_code: str = Form(...),
    item_text: str = Form(...),
):
    if not require_role(request, {"admin"}):
        flash(request, "error", "Редактировать заказы может только администратор.")
        return RedirectResponse("/orders", status_code=303)
    if not valid_csrf(request, csrf):
        flash(request, "error", "Сессия устарела. Повторите действие.")
        return RedirectResponse("/orders", status_code=303)

    try:
        items = parse_article_items(item_text)
        order_number_i = parse_nonnegative_int(
            order_number, "Номер заказа", allow_zero=False
        )
        client_i = parse_nonnegative_int(client_id, "Клиент", allow_zero=False)
        pickup_i = parse_nonnegative_int(
            pickup_point_id, "Пункт выдачи", allow_zero=False
        )
        code_i = parse_nonnegative_int(pickup_code, "Код получения")
        if status not in status_values:
            raise ValueError("Статус заказа: выберите значение из списка.")

        order_date_value = date.fromisoformat(order_date)
        delivery_date_value = (
            date.fromisoformat(delivery_date) if delivery_date else None
        )
        if delivery_date_value and delivery_date_value < order_date_value:
            raise ValueError("Дата выдачи не может быть раньше даты заказа.")

        with SessionLocal() as db:
            order = db.get(Order, order_id)
            if not order:
                raise ValueError("Заказ не найден.")

            order.order_number = order_number_i
            order.client_id = client_i
            order.pickup_point_id = pickup_i
            order.status = status
            order.order_date = order_date_value
            order.delivery_date = delivery_date_value
            order.pickup_code = code_i

            for old_item in list(order.items):
                db.delete(old_item)
            db.flush()
            for product_id, quantity in items:
                product = db.get(Product, product_id)
                order.items.append(
                    OrderItem(
                        product_id=product_id,
                        quantity=quantity,
                        unit_price=product.discounted_price,
                    )
                )
            db.commit()
    except (ValueError, TypeError) as exc:
        flash(request, "error", str(exc))
        return RedirectResponse(
            f"/admin/order/{order_id}/edit", status_code=303
        )
    except Exception:
        flash(
            request,
            "error",
            "Не удалось сохранить заказ. Проверьте уникальность номера и данные формы.",
        )
        return RedirectResponse(
            f"/admin/order/{order_id}/edit", status_code=303
        )

    flash(request, "success", "Изменения заказа сохранены. Список заказов обновлен.")
    return RedirectResponse("/orders", status_code=303)


@app.post("/admin/order/{order_id}/delete")
def order_delete(
    request: Request,
    order_id: int,
    csrf: str = Form(...),
):
    if not require_role(request, {"admin"}):
        flash(request, "error", "Удалять заказы может только администратор.")
        return RedirectResponse("/orders", status_code=303)
    if not valid_csrf(request, csrf):
        flash(request, "error", "Сессия устарела. Повторите действие.")
        return RedirectResponse("/orders", status_code=303)

    with SessionLocal() as db:
        order = db.get(Order, order_id)
        if not order:
            flash(request, "error", "Заказ не найден.")
            return RedirectResponse("/orders", status_code=303)
        db.delete(order)
        db.commit()

    flash(request, "success", "Заказ удален. Список заказов обновлен.")
    return RedirectResponse("/orders", status_code=303)


@app.get("/health")
def health():
    with SessionLocal() as db:
        return {
            "status": "ok",
            "users": db.scalar(select(func.count(User.user_id))) or 0,
            "products": db.scalar(select(func.count(Product.product_id))) or 0,
            "orders": db.scalar(select(func.count(Order.order_id))) or 0,
            "order_items": db.scalar(
                select(func.count(OrderItem.order_item_id))
            )
            or 0,
            "pickup_points": db.scalar(
                select(func.count(PickupPoint.pickup_point_id))
            )
            or 0,
        }
