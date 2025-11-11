from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Todas las vistas de cuentas bajo el namespace 'accounts'
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),

    # Operaciones con su namespace (para usar 'operaciones:...')
    path("", include(("operaciones.urls", "operaciones"), namespace="operaciones")),

    # Página raíz: redirige al login (o cambia a 'accounts:dashboard' si prefieres)
    path("", RedirectView.as_view(pattern_name="accounts:login", permanent=False)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
