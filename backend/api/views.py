import hashlib

from core.utils import GenPdfShoppingCart
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.conf import settings
from djoser.views import UserViewSet
from recipes.models import (Favorite, Ingredient, Recipe, ShoppingCart,
                            ShortLinkForRecipe, Tag, User)
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

from .filters import IngredientFilter, RecipeFilter
from .pagination import RecipePagination
from .permissions import RecipePermissiom
from .serializers import (AvatarSerializer, IngredientSerializer,
                          RecipeActionSerializer, RecipeSerializer,
                          ShortLinkSerializer, SubscribeSerializer,
                          TagSerializer)


class CustomUserviewSet(UserViewSet):
    http_method_names = ['get', 'post', 'put', 'delete']
    pagination_class = LimitOffsetPagination

    def get_permissions(self):
        if self.action == 'update':
            self.permission_classes = settings.PERMISSIONS.user_put
        return super().get_permissions()

    @action(detail=False, permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(self.get_instance())
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['put', 'delete'],
        permission_classes=[permissions.IsAuthenticated],
        url_path='me/avatar'
    )
    def me_avatar(self, request):
        user = self.get_instance()
        if request.method == 'PUT':
            serializer = AvatarSerializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        if request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[permissions.IsAuthenticated],
    )
    def subscribe(self, request, id=None):
        if request.method == 'POST':
            request.data['id'] = id
            serializer = SubscribeSerializer(
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            user = self.get_instance()
            author = get_object_or_404(User, id=id)
            if user.subscription.filter(id=author.id).exists():
                user.subscription.remove(author)
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {"errors": "Подписка на автора не найдена"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=False,
        serializer_class=SubscribeSerializer,
        permission_classes=[permissions.IsAuthenticated],
        pagination_class=LimitOffsetPagination,
    )
    def subscriptions(self, request):
        user = self.get_instance()
        queruset = user.subscription.all()
        page = self.paginate_queryset(queruset)

        if page is not None:
            serializer = self.get_serializer(
                page,
                many=True,
                context={'request': request},
            )
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(
            queruset,
            many=True,
            context={'request': request},
        )
        return Response(serializer.data)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend, IngredientFilter)
    search_fields = ('^name',)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [RecipePermissiom]
    pagination_class = RecipePagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    filterset_fields = (
        'author',
        'tags',
        'is_favorited',
        'is_in_shopping_cart',
    )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def action_for_reicpe(self, request, pk, model):
        recipe = get_object_or_404(self.queryset, id=pk)
        if request.method == 'POST':
            request.data['id'] = recipe.id
            serializer = self.get_serializer(
                data=request.data,
                context={'request': request}
            )
            serializer.Meta.model = model
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            if not model.objects.filter(
                recipe=recipe, user=request.user
            ).exists():
                raise serializers.ValidationError(
                    {'error': 'Рецепт не найден'}
                )

            model.objects.filter(recipe=pk, user=request.user).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post', 'delete'],
        serializer_class=RecipeActionSerializer,
        permission_classes=[permissions.IsAuthenticated],
        pagination_class=RecipePagination
    )
    def favorite(self, request, pk=None):
        return self.action_for_reicpe(request, pk, Favorite)

    @action(
        detail=True,
        methods=['post', 'delete',],
        serializer_class=RecipeActionSerializer,
        permission_classes=[permissions.IsAuthenticated],
    )
    def shopping_cart(self, request, pk=None):
        return self.action_for_reicpe(request, pk, ShoppingCart)

    @action(detail=False, permission_classes=[permissions.IsAuthenticated])
    def download_shopping_cart(self, request):
        user_shopping_cart = request.user.shoppingcart_user.select_related(
            'recipe',
        ).prefetch_related('recipe__recipe_ingredient__ingredient',)

        shopping_cart = {}

        for obj_shop_cart in user_shopping_cart:
            obj_recipe_ingred = obj_shop_cart.recipe.recipe_ingredient.all()
            for recipe_ing in obj_recipe_ingred:
                ingredient_name = recipe_ing.ingredient.name
                if ingredient_name in shopping_cart:
                    shopping_cart[ingredient_name]['amount'] += (
                        recipe_ing.amount
                    )
                else:
                    shopping_cart[recipe_ing.ingredient.name] = {
                        'amount': recipe_ing.amount,
                        'meas_unit': (
                            recipe_ing.ingredient.measurement_unit
                        )
                    }
        pdf_file = GenPdfShoppingCart(shopping_cart)
        return pdf_file.return_pdf()

    @action(
        detail=True,
        url_path='get-link',
        serializer_class=ShortLinkSerializer,
    )
    def get_link(self, request, pk=None):
        short_url = str(hashlib.md5(str(pk).encode()).hexdigest()[:6])
        serializer = ShortLinkSerializer(
            data={
                'id': pk,
                'short_url': short_url,
            },
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def redirect_to_recipe(request, short_url):
    obj = get_object_or_404(ShortLinkForRecipe, short_url=short_url)
    base_url = request.build_absolute_uri('/')
    return redirect(f'{base_url}recipes/{obj.recipe.id}')
