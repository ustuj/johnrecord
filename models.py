from datetime import date, datetime
from pathlib import Path
from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

base_dir = Path(__file__).resolve().parent

class User(Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    login: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    orders: Mapped[list["Order"]] = relationship(back_populates="client")
    __table_args__ = (CheckConstraint("role IN ('client','manager','admin')", name="ck_user_role"),)

class Supplier(Base):
    __tablename__ = "suppliers"
    supplier_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    products: Mapped[list["Product"]] = relationship(back_populates="supplier")

class Manufacturer(Base):
    __tablename__ = "manufacturers"
    manufacturer_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    products: Mapped[list["Product"]] = relationship(back_populates="manufacturer")

class Category(Base):
    __tablename__ = "categories"
    category_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    products: Mapped[list["Product"]] = relationship(back_populates="category")

class Label(Base):
    __tablename__ = "labels"
    label_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    products: Mapped[list["Product"]] = relationship(back_populates="label")

class RecordFormat(Base):
    __tablename__ = "record_formats"
    format_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    products: Mapped[list["Product"]] = relationship(back_populates="record_format")

class Product(Base):
    __tablename__ = "products"
    product_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    article: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    artist: Mapped[str] = mapped_column(String(160), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.category_id", ondelete="RESTRICT"), nullable=False)
    label_id: Mapped[int] = mapped_column(ForeignKey("labels.label_id", ondelete="RESTRICT"), nullable=False)
    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("manufacturers.manufacturer_id", ondelete="RESTRICT"), nullable=False)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.supplier_id", ondelete="RESTRICT"), nullable=False)
    format_id: Mapped[int] = mapped_column(ForeignKey("record_formats.format_id", ondelete="RESTRICT"), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="шт.")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    discount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    image_path: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_new: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_bestseller: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_staff_pick: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_preorder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_color_vinyl: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    category: Mapped["Category"] = relationship(back_populates="products")
    label: Mapped["Label"] = relationship(back_populates="products")
    manufacturer: Mapped["Manufacturer"] = relationship(back_populates="products")
    supplier: Mapped["Supplier"] = relationship(back_populates="products")
    record_format: Mapped["RecordFormat"] = relationship(back_populates="products")
    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="product")
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_product_price_nonnegative"),
        CheckConstraint("stock_quantity >= 0", name="ck_product_stock_nonnegative"),
        CheckConstraint("discount >= 0 AND discount <= 100", name="ck_product_discount_range"),
    )
    @property
    def discounted_price(self) -> Decimal:
        return (self.price * Decimal(100 - self.discount) / Decimal(100)).quantize(Decimal("0.01"))
    @property
    def image_url(self) -> str:
        if self.image_path:
            if self.image_path.startswith(("http://", "https://")):
                return self.image_path
            image_file = base_dir / self.image_path.lstrip("/")
            if image_file.exists():
                return self.image_path
        return "/static/resources/picture.png"

class PickupPoint(Base):
    __tablename__ = "pickup_points"
    pickup_point_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    address: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    orders: Mapped[list["Order"]] = relationship(back_populates="pickup_point")

class Order(Base):
    __tablename__ = "orders"
    order_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    order_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    pickup_point_id: Mapped[int] = mapped_column(ForeignKey("pickup_points.pickup_point_id", ondelete="RESTRICT"), nullable=False)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    pickup_code: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    client: Mapped["User"] = relationship(back_populates="orders")
    pickup_point: Mapped["PickupPoint"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    __table_args__ = (
        CheckConstraint("pickup_code >= 0", name="ck_order_pickup_code_nonnegative"),
        CheckConstraint("status IN ('new','processing','ready','completed','cancelled')", name="ck_order_status"),
    )

class OrderItem(Base):
    __tablename__ = "order_items"
    order_item_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="order_items")
    __table_args__ = (
        UniqueConstraint("order_id", "product_id", name="uq_order_product"),
        CheckConstraint("quantity > 0", name="ck_order_item_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_order_item_unit_price_nonnegative"),
    )
