from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission, User

from catalog.models import Category, Product, Supplier, Tag


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser("root", "root@example.com", "pw")


@pytest.fixture
def admin_client(client, admin_user):
    client.force_login(admin_user)
    return client


def _staff(username, perms):
    user = User.objects.create_user(username, f"{username}@example.com", "pw", is_staff=True)
    user.user_permissions.set(Permission.objects.filter(codename__in=perms))
    return user


@pytest.fixture
def editor(db):
    """Can view/change products, view categories. Nothing else."""
    return _staff("editor", ["view_product", "change_product", "view_category"])


@pytest.fixture
def viewer(db):
    return _staff("viewer", ["view_product"])


@pytest.fixture
def catalog(db):
    cat = Category.objects.create(name="Wellness", slug="wellness")
    other = Category.objects.create(name="Books", slug="books")
    sup = Supplier.objects.create(name="Northwind", email="n@example.com")
    tag = Tag.objects.create(name="eco")
    products = []
    for i in range(30):
        p = Product.objects.create(
            name=f"Velvet Kit {i:02d}" if i % 2 else f"Cedar Box {i:02d}",
            slug=f"p-{i}",
            sku=f"SKU-{i:03d}",
            category=cat if i % 3 else other,
            supplier=sup,
            status="active" if i % 4 else "draft",
            price=Decimal("10.00") + i,
            stock=i,
        )
        products.append(p)
    products[0].tags.add(tag)
    return {"category": cat, "other": other, "supplier": sup, "tag": tag, "products": products}
