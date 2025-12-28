from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    
    def ready(self):
        import accounts.signals
        # --- Auto-create default admin user for Render deployment ---
        from django.contrib.auth.models import User
        from django.db.utils import OperationalError
        default_admin_username = 'admin'
        default_admin_email = 'admin@example.com'
        default_admin_password = 'admin1234'
        try:
            if not User.objects.filter(username=default_admin_username).exists():
                User.objects.create_superuser(
                    username=default_admin_username,
                    email=default_admin_email,
                    password=default_admin_password
                )
        except OperationalError:
            # Database might not be ready (e.g., during migrations)
            pass
