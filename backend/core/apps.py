from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        from django.db.models.signals import post_migrate
        from .management.commands.seed_admin import seed_default_admin

        def run_seed(sender, **kwargs):
            seed_default_admin()

        post_migrate.connect(run_seed, sender=self)
