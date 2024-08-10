from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import IngredientViewSet, RecipeViewSet, TagViewSet, UserviewSet

router = DefaultRouter()
router.register('users', UserviewSet, basename='users')
router.register('tags', TagViewSet)
router.register('ingredients', IngredientViewSet)
router.register('recipes', RecipeViewSet, basename='recipe')

urlpatterns = [
    path('', include(router.urls)),
    path('auth', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
