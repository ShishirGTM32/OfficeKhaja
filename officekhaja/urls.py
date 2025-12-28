"""
URL configuration for officekhaja project using DRF Spectacular.

This setup includes:
- Versioned API URLs for frontend integration
- Swagger UI and Redoc for API documentation
- Nested/related fields support in serializers
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# DRF Spectacular
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView
)

urlpatterns = [

    path('admin/', admin.site.urls),

    path('api/khaja/', include('khaja.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/auth/', include('users.urls')),
    # path('api/admin/', include('orders.admin_urls')),
    # path('api/staff/', include('orders.staff_urls')),
    # path('api/blogs/', include('blog.urls')),
    # path('api/noti/', include('notifications.urls')),
    # path('api/chat/', include('chatapp.urls')),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'), 
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
