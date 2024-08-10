from rest_framework.pagination import LimitOffsetPagination
from rest_framework.pagination import PageNumberPagination


class AuthorRecipesPagination(LimitOffsetPagination):
    limit_query_param = 'recipes_limit'


class RecipePagination(PageNumberPagination):
    page_size_query_param = 'limit'
