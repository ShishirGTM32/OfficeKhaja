from django.urls import path
from .views import ConversationView, MessageView

urlpatterns = [
    path('conversation/', ConversationView.as_view(), name="conversation"),
    path('conversation/<uuid:uuid>/messages/', MessageView.as_view(), name="messages")
]   