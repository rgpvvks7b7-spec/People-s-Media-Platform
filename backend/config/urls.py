from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('accounts.urls')),
    path('api/artists/', include('artists.urls')),
    path('api/posts/', include('posts.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
    path('api/media/', include('mediahub.urls')),
    path('api/marketplace/', include('marketplace.urls')),
    path('api/discovery/', include('discovery.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
