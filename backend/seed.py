"""
Run this once after docker compose up to seed the database.
Usage: python seed.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uuid
from app.database import SessionLocal, create_all_tables
from app.models.user import User, UserRole
from app.models.product import Product
from app.auth import hash_password

create_all_tables()
db = SessionLocal()

print("Seeding database...")

# ── Admin User ────────────────────────────────────────────────────────────────
admin = db.query(User).filter(User.email == "admin@dairip.com").first()
if not admin:
    admin = User(
        id=str(uuid.uuid4()),
        email="admin@dairip.com",
        full_name="System Admin",
        hashed_password=hash_password("Admin1234!"),
        role=UserRole.ADMIN,
    )
    db.add(admin)
    print("  Created admin user: admin@dairip.com / Admin1234!")

# ── Manager User ──────────────────────────────────────────────────────────────
manager = db.query(User).filter(User.email == "manager@dairip.com").first()
if not manager:
    manager = User(
        id=str(uuid.uuid4()),
        email="manager@dairip.com",
        full_name="Branch Manager",
        hashed_password=hash_password("Manager1234!"),
        role=UserRole.MANAGER,
        branch_id="branch-001",
    )
    db.add(manager)
    print("  Created manager: manager@dairip.com / Manager1234!")

# ── Sample Products ───────────────────────────────────────────────────────────
products = [
    Product(
        id=str(uuid.uuid4()),
        barcode="5000117100481",
        name="Whole Milk 1L",
        sku="DAIRY-MILK-1L",
        category="Dairy",
        is_perishable=True,
        base_price=1.50,
        current_price=1.50,
        expiry_days=7,
    ),
    Product(
        id=str(uuid.uuid4()),
        barcode="5010123001234",
        name="Sourdough Bread",
        sku="BAKERY-SOUR-400G",
        category="Bakery",
        is_perishable=True,
        base_price=3.00,
        current_price=3.00,
        expiry_days=3,
    ),
    Product(
        id=str(uuid.uuid4()),
        barcode="8076800195057",
        name="Pasta 500g",
        sku="DRY-PASTA-500G",
        category="Dry Goods",
        is_perishable=False,
        base_price=1.20,
        current_price=1.20,
    ),
    Product(
        id=str(uuid.uuid4()),
        barcode="5000000501234",
        name="Chicken Breast 500g",
        sku="MEAT-CHKN-500G",
        category="Meat",
        is_perishable=True,
        base_price=5.00,
        current_price=5.00,
        expiry_days=4,
    ),
]

for p in products:
    existing = db.query(Product).filter(Product.sku == p.sku).first()
    if not existing:
        db.add(p)
        print(f"  Created product: {p.sku}")

db.commit()
db.close()
print("\nSeed complete. You can now log in and receive stock.")
print("Branch ID for testing: branch-001")