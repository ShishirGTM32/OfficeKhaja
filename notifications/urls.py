from django.urls import path
from .views import NotificationView

urlpatterns = [
    path('notification/', NotificationView.as_view(), name="notifications"),
    path('notification/<int:id>/', NotificationView.as_view(), name="read-notification")
]