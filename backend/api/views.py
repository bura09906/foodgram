import hashlib

from django.db.models import BooleanField, Exists, OuterRef, Value
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

from recipes.models import (Favorite, Ingredient, Recipe, ShoppingCart,
                            ShortLinkForRecipe, Tag, User)

from .filters import IngredientFilter, RecipeFilter
from .pagination import RecipePagination
from .permissions import IsAuthorReciepOrReadonly
from .serializers import (AvatarSerializer, IngredientSerializer,
                          RecipeActionSerializer, RecipeReadSerializer,
                          RecipeWriteSerializer, ShortLinkSerializer,
                          SubscribeSerializer, TagSerializer)
from .shopping_cart import shopping_cart_pdf_generator


class UserviewSet(DjoserUserViewSet):
    http_method_names = ['get', 'post', 'put', 'delete']
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if user.is_authenticated:
            is_subscribed_subquery = User.objects.filter(
                subscription=user,
                id=OuterRef('pk')
            )
            queryset = queryset.annotate(
                is_subscribed=Exists(is_subscribed_subquery)
            )
        else:
            queryset = queryset.annotate(
                is_subscribed=Value(
                    False,
                    output_field=BooleanField()
                )
            )
        return queryset

    @action(detail=False, permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(self.get_instance())
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['put'],
        permission_classes=[permissions.IsAuthenticated],
        url_path='me/avatar'
    )
    def me_avatar(self, request):
        user = self.get_instance()
        serializer = AvatarSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @me_avatar.mapping.delete
    def delete_me_avatar(self, request):
        user = self.get_instance()
        if user.avatar:
            user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post'],
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

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id=None):
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
    filter_backends = [IngredientFilter]
    search_fields = ('^name',)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.with_related_data()
    permission_classes = [IsAuthorReciepOrReadonly]
    pagination_class = RecipePagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    filterset_fields = (
        'author',
        'tags__slug',
        'is_favorited',
        'is_in_shopping_cart',
    )

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if user.is_authenticated:
            return queryset.annotation_relation_with_user(user)
        return queryset.annotate_relation_with_anonymous()

    def get_serializer_class(self):
        if self.action in ['retrive', 'list']:
            return RecipeReadSerializer
        if self.action in ['favorite', 'shopping_cart']:
            return RecipeActionSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def action_create_for_reicpe(self, request, pk, model):
        recipe = get_object_or_404(self.queryset, id=pk)
        request.data['id'] = recipe.id
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}
        )
        serializer.Meta.model = model
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def action_delete_for_recipe(self, request, pk, model):
        recipe = get_object_or_404(self.queryset, id=pk)
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
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated],
        pagination_class=RecipePagination
    )
    def favorite(self, request, pk=None):
        return self.action_create_for_reicpe(request, pk, Favorite)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        return self.action_delete_for_recipe(request, pk, Favorite)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated],
    )
    def shopping_cart(self, request, pk=None):
        return self.action_create_for_reicpe(request, pk, ShoppingCart)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        return self.action_delete_for_recipe(request, pk, ShoppingCart)

    @action(detail=False, permission_classes=[permissions.IsAuthenticated])
    def download_shopping_cart(self, request):
        response = shopping_cart_pdf_generator(request.user)
        return response

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
