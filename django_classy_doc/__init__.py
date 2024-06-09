from django.conf import settings as user_settings
from . import app_settings as default_settings


class AppSettings:
    def __getattr__(self, name):
        if hasattr(user_settings, name):
            return getattr(user_settings, name)

        if hasattr(default_settings, name):
            return getattr(default_settings, name)

        raise AttributeError(f"Settings object has no attribute '{name}'")


settings = AppSettings()
