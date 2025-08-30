"""
URL configuration for sistema_checkin project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Rota para o painel de administração do Django
    path('admin/', admin.site.urls),
    
    # Esta linha inclui todas as URLs do nosso aplicativo 'core'.
    # Qualquer acesso à raiz do site (ex: http://127.0.0.1:8000/)
    # será gerenciado pelo arquivo core/urls.py.
    path('', include('core.urls')),
]

# --- Configuração para Servir Arquivos de Mídia (QR Codes) ---
# Esta parte é crucial para que as imagens dos QR Codes apareçam no site
# durante o desenvolvimento (quando DEBUG=True).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

