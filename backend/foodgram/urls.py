from django.contrib import admin
from django.urls import include, path

from api.views import redirect_to_recipe

urlpatterns = [
    path('api/', include('api.urls')),
    path('admin/', admin.site.urls),
    path('s/<str:short_url>/', redirect_to_recipe),
]
