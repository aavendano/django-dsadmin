from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView

from catalog.backoffice import backoffice

urlpatterns = [
    path("", RedirectView.as_view(url="/admin/", permanent=False)),
    path("admin/", admin.site.urls),          # configuration #1 (settings.DSADMIN)
    path("backoffice/", backoffice.urls),     # configuration #2 (DSAdminSite options)
]
