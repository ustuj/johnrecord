from pathlib import Path
import csv
import sys
from decimal import Decimal

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from database import Base, engine, SessionLocal
from models import User, Supplier, Manufacturer, Category, Label, RecordFormat, Product, PickupPoint, Order, OrderItem
from security import hash_password


def rows(name):
    with (root / "data" / "processed" / name).open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file, delimiter=";"))


def seed_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        users = rows("users.csv")
        suppliers = sorted({r["supplier"] for r in rows("products.csv")})
        manufacturers = sorted({r["manufacturer"] for r in rows("products.csv")})
        categories = sorted({r["genre"] for r in rows("products.csv")})
        labels = sorted({r["label"] for r in rows("products.csv")})
        formats = ["1LP", "2LP", "7 INCH", "BOX SET"]
        db.add_all([Supplier(supplier_id=i, name=name) for i, name in enumerate(suppliers, 1)])
        db.add_all([Manufacturer(manufacturer_id=i, name=name) for i, name in enumerate(manufacturers, 1)])
        db.add_all([Category(category_id=i, name=name) for i, name in enumerate(categories, 1)])
        db.add_all([Label(label_id=i, name=name) for i, name in enumerate(labels, 1)])
        db.add_all([RecordFormat(format_id=i, name=name) for i, name in enumerate(formats, 1)])
        db.flush()
        supplier_ids={x.name:x.supplier_id for x in db.query(Supplier).all()}
        manufacturer_ids={x.name:x.manufacturer_id for x in db.query(Manufacturer).all()}
        category_ids={x.name:x.category_id for x in db.query(Category).all()}
        label_ids={x.name:x.label_id for x in db.query(Label).all()}
        format_ids={x.name:x.format_id for x in db.query(RecordFormat).all()}
        db.add_all([
            User(user_id=int(r["source_user_id"]), full_name=r["full_name"], login=r["login"], password_hash=hash_password(r["initial_password"]), role=r["role"])
            for r in users
        ])
        db.flush()
        for i, row in enumerate(rows("pickup_points.csv"), 1):
            db.add(PickupPoint(pickup_point_id=int(row["pickup_point_id"]), address=row["address"]))
        db.flush()
        products = rows("products.csv")
        db.add_all([
            Product(
                product_id=int(r["product_id"]), article=r["article"], name=r["name"], artist=r["artist"],
                category_id=category_ids[r["genre"]], label_id=label_ids[r["label"]],
                manufacturer_id=manufacturer_ids[r["manufacturer"]], supplier_id=supplier_ids[r["supplier"]],
                format_id=format_ids[r["format"]], unit=r["unit"], price=Decimal(r["price"]),
                stock_quantity=int(r["stock_quantity"]), discount=int(r["discount"]), description=r["description"], image_path=r["image_path"],
                is_new=bool(int(r["is_new"])), is_bestseller=bool(int(r["is_bestseller"])),
                is_staff_pick=bool(int(r["is_staff_pick"])), is_preorder=bool(int(r["is_preorder"])),
                is_color_vinyl=bool(int(r["is_color_vinyl"]))
            ) for r in products
        ])
        db.flush()
        orders = rows("orders.csv")
        db.add_all([
            Order(order_id=int(r["order_id"]), order_number=int(r["order_number"]), client_id=int(r["client_user_id"]), pickup_point_id=int(r["pickup_point_id"]),
                  order_date=__import__("datetime").date.fromisoformat(r["order_date"]), delivery_date=__import__("datetime").date.fromisoformat(r["delivery_date"]),
                  pickup_code=int(r["pickup_code"]), status=r["status"])
            for r in orders
        ])
        db.flush()
        items = rows("order_items.csv")
        db.add_all([
            OrderItem(order_id=int(r["order_id"]), product_id=int(r["product_id"]), quantity=int(r["quantity"]), unit_price=Decimal(r["unit_price"]))
            for r in items
        ])
        db.commit()
        print("Database initialized successfully.")
        print(f"Users: {len(users)} | Products: {len(products)} | Orders: {len(orders)} | Order items: {len(items)} | Pickup points: {len(rows('pickup_points.csv'))}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
