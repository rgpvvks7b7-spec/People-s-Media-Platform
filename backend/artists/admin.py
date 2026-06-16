from django.contrib import admin
from . import models

for name in dir(models):
    obj = getattr(models, name)
    if hasattr(obj, '_meta') and getattr(obj._meta, 'app_label', None) == 'artists':
        try:
            admin.site.register(obj)
        except admin.sites.AlreadyRegistered:
            pass
