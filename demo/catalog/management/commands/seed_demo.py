import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from catalog.models import Category, Product, ProductNote, Supplier, Tag, Variant


class Command(BaseCommand):
    help = "Create demo users and catalog data (idempotent)."

    def handle(self, *args, **options):
        rnd = random.Random(42)
        admin, created = User.objects.get_or_create(username="admin", defaults={"email": "admin@example.com"})
        admin.is_staff = admin.is_superuser = True
        admin.first_name = "Ada"
        admin.set_password("admin")
        admin.save()

        editors, _ = Group.objects.get_or_create(name="Catalog editors")
        editors.permissions.set(
            Permission.objects.filter(
                content_type__app_label="catalog",
                codename__in=["view_product", "change_product", "view_category", "view_supplier", "view_tag",
                              "view_variant", "change_variant", "add_variant"],
            )
        )
        editor, _ = User.objects.get_or_create(username="editor", defaults={"email": "editor@example.com"})
        editor.is_staff = True
        editor.is_superuser = False
        editor.set_password("editor")
        editor.save()
        editor.groups.set([editors])

        if Product.objects.exists():
            self.stdout.write("Catalog already seeded.")
            return

        cats = {}
        for name in ["Wellness", "Couples", "Accessories", "Gift sets", "Bath & body", "Books"]:
            cats[name] = Category.objects.create(name=name, slug=slugify(name))
        suppliers = [
            Supplier.objects.create(name=n, email=f"sales@{slugify(n)}.example", country=c, active=a,
                                    website=f"https://{slugify(n)}.example")
            for n, c, a in [("Northwind Goods", "CA", True), ("Maple & Co", "CA", True), ("Lumen Labs", "US", True),
                            ("Oslo Supply", "NO", False)]
        ]
        tags = [Tag.objects.create(name=t) for t in ["bestseller", "new", "eco", "gift", "limited", "vegan"]]
        adjectives = ["Velvet", "Aurora", "Coastal", "Midnight", "Linen", "Ember", "Juniper", "Halo", "Cedar", "Nova"]
        nouns = ["Kit", "Set", "Collection", "Duo", "Essentials", "Box", "Edition", "Bundle"]
        statuses = ["active"] * 5 + ["draft"] * 2 + ["archived"]
        today = date.today()
        for i in range(48):
            name = f"{rnd.choice(adjectives)} {rnd.choice(nouns)} {i + 1:02d}"
            p = Product.objects.create(
                name=name,
                slug=slugify(name),
                sku=f"PLT-{1000 + i}",
                category=rnd.choice(list(cats.values())),
                supplier=rnd.choice(suppliers),
                status=rnd.choice(statuses),
                price=Decimal(rnd.randrange(1500, 18000)) / 100,
                stock=rnd.choice([0, 2, 5, 8, 12, 25, 40, 75, 120, 180]),
                is_featured=rnd.random() < 0.2,
                description="Demo product used to exercise the dsadmin change list and forms.",
                launch_date=today - timedelta(days=rnd.randrange(0, 400)),
            )
            p.tags.set(rnd.sample(tags, rnd.randrange(0, 3)))
            for v in range(rnd.randrange(0, 3)):
                Variant.objects.create(product=p, name=["Small", "Medium", "Large"][v], sku=f"{p.sku}-{v}",
                                       stock=rnd.randrange(0, 50))
            if i % 7 == 0:
                ProductNote.objects.create(product=p, author=admin, body="Check supplier lead time before restock.")
        self.stdout.write(self.style.SUCCESS("Seeded demo data. Users: admin/admin (superuser), editor/editor (staff)."))
