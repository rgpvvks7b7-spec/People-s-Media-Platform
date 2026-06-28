from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from artists.public import robots_txt, sitemap_xml
from config.health import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('robots.txt', robots_txt),
    path('sitemap.xml', sitemap_xml),
    path('api/health/', health_check),
    path('api/accounts/', include('accounts.urls')),
    path('api/artists/', include('artists.urls')),
    path('api/posts/', include('posts.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
    path('api/media/', include('mediahub.urls')),
    path('api/marketplace/', include('marketplace.urls')),
    path('api/discovery/', include('discovery.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/live/', include('livehub.urls')),
    path('api/challenges/', include('challenges.urls')),
    path('api/spaces/', include('spaces.urls')),
    path('api/promotions/', include('promotions.urls')),
    path('api/campaigns/', include('campaigns.urls')),
    path('api/moderation/', include('moderation.urls')),
]
if settings.DEBUG or settings.SERVE_LOCAL_MEDIA:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
