import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from chatapp.middleware import JWTAuthMiddleware
import chatapp.routing as cr
import notifications.routing as nr

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "officekhaja.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(
        URLRouter(
            cr.websocket_urlpatterns + nr.websocket_urlpatterns
        )
    ),
})
