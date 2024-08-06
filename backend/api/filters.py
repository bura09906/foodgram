from django_filters.rest_framework import BooleanFilter, CharFilter, FilterSet
from recipes.models import Recipe
from rest_framework.filters import SearchFilter


class IngredientFilter(SearchFilter):
    search_param = 'name'


class RecipeFilter(FilterSet):
    author = CharFilter(field_name='author', lookup_expr='exact')
    tags = CharFilter(field_name='tags__slug', lookup_expr='exact')
    is_favorited = BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = BooleanFilter(method='filter_is_in_shopping_cart')

    class Meta:
        models = Recipe
        fields = ('author', 'tags', 'is_favorited', 'is_in_shopping_cart',)

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(favorite_recipes__user=user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(shoppingcart_recipes__user=user)
        return queryset
