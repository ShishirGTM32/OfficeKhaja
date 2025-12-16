import jwt
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.conf import settings

User = get_user_model()


@database_sync_to_async
def get_user_from_jwt(token):
    try:
        UntypedToken(token)

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )

        user_id = payload.get("user_id")
        return User.objects.get(id=user_id)

    except (InvalidToken, TokenError, User.DoesNotExist, jwt.DecodeError):
        return AnonymousUser()



class JwtAuthMiddleware:
    def __init__(self, app):
        self.app = app 

    async def __call__(self, scope, receive, send):
        
        scope["user"] = AnonymousUser()

        
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token_list = params.get("token")
        token = token_list[0] if token_list else None

        if token:
            user = await get_user_from_jwt(token)
            scope["user"] = user

        return await self.app(scope, receive, send)
