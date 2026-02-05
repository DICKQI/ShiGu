from django.core.management.base import BaseCommand
from django.db import transaction

from apps.users.models import Role, User

"""
python .\manage.py seed_users --admin-username admin --admin-password "你的强密码"
"""
class Command(BaseCommand):
    help = "Seed default roles and admin user (id=1)."

    def add_arguments(self, parser):
        parser.add_argument("--admin-username", default="admin", help="Admin username")
        parser.add_argument("--admin-password", default=None, help="Admin password")

    @transaction.atomic
    def handle(self, *args, **options):
        admin_role, _ = Role.objects.get_or_create(name="Admin")
        user_role, _ = Role.objects.get_or_create(name="User")

        self.stdout.write(self.style.SUCCESS("Roles ensured: Admin, User"))

        admin_password = options.get("admin_password")
        if not admin_password:
            self.stdout.write(self.style.WARNING("Skip admin user creation: --admin-password not provided"))
            return

        admin_username = (options.get("admin_username") or "admin").strip()

        # Ensure there is an admin user with id=1 (required by migrations backfill default)
        user_qs = User.objects.select_for_update()
        admin_user = user_qs.filter(id=1).first()
        if admin_user:
            # Update role/username/password if needed
            changed = False
            if admin_user.role_id != admin_role.id:
                admin_user.role = admin_role
                changed = True
            if admin_user.username != admin_username:
                admin_user.username = admin_username
                changed = True
            admin_user.set_password(admin_password)
            changed = True
            admin_user.is_active = True
            changed = True
            if changed:
                admin_user.save()
            self.stdout.write(self.style.SUCCESS(f"Admin user ensured: id=1 username={admin_user.username}"))
            return

        # If id=1 is free, create admin user then force pk=1
        admin_user = User(id=1, username=admin_username, role=admin_role, is_active=True)
        admin_user.set_password(admin_password)
        admin_user.save(force_insert=True)
        self.stdout.write(self.style.SUCCESS(f"Admin user created: id=1 username={admin_user.username}"))

