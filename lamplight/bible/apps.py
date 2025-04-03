"""Bible app management"""

from django.apps import AppConfig


class BibleConfig(AppConfig):
    """Bible configuration"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "bible"
