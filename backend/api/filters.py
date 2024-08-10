from django_filters.rest_framework import (AllValuesMultipleFilter,
                                           BooleanFilter, CharFilter,
                                           FilterSet)
from rest_framework.filters import SearchFilter

from recipes.models import Recipe


class IngredientFilter(SearchFilter):
    search_param = 'name'


class RecipeFilter(FilterSet):
    author = CharFilter(field_name='author', lookup_expr='exact')
    tags = AllValuesMultipleFilter(field_name='tags__slug')
    is_favorited = BooleanFilter(field_name='is_favorited')
    is_in_shopping_cart = BooleanFilter(field_name='is_in_shopping_cart')

    class Meta:
        models = Recipe
        fields = ('author', 'tags', 'is_favorited', 'is_in_shopping_cart',)
