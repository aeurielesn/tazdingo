import os
import sys
from django.core.wsgi import get_wsgi_application


# Django specific settings
if "--dev" in sys.argv:
    sys.argv.remove("--dev")
    _settings = "settings.development"
else:
    _settings = "settings.production"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", _settings)

# Ensure settings are read
application = get_wsgi_application()

# Your application specific imports
from django.conf import settings
