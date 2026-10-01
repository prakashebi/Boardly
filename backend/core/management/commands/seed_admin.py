from django.core.management.base import BaseCommand
from core.models import User, UserRole
from core.security import hash_password

_ADMIN_EMAIL = "admin@orqestra.local"
_ADMIN_USERNAME = "admin"
_ADMIN_PASSWORD = "admin"


def seed_default_admin():
    if User.objects.exists():
        return

    admin = User.objects.create(
        email=_ADMIN_EMAIL,
        username=_ADMIN_USERNAME,
        hashed_password=hash_password(_ADMIN_PASSWORD),
        role=UserRole.ADMIN,
        is_active=True,
    )
    print(
        f"[seed] Default admin created — "
        f"email: {_ADMIN_EMAIL}  password: {_ADMIN_PASSWORD}  "
        f"(change this password after first login)"
    )


class Command(BaseCommand):
    help = "Seed default admin user if no users exist"

    def handle(self, *args, **options):
        seed_default_admin()
