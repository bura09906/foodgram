from django.conf import settings
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.shortcuts import get_object_or_404
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, ShortLinkForRecipe, Tag, User)
from .pagination import AuthorRecipesPagination


class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        validators=(UnicodeUsernameValidator,),
    )
    avatar = Base64ImageField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar',
        )
        read_only_fields = ('id', 'avatar', 'is_subscribed',)

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request.user.is_authenticated:
            return request.user.subscription.filter(id=obj.id).exists()
        return False


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=False)

    class Meta:
        model = User
        fields = ('avatar',)

    def validate(self, attrs):
        if 'avatar' not in attrs or attrs['avatar'] is None:
            raise serializers.ValidationError(
                {'avatar': 'Необходимо передать изображение для аватара.'}
            )
        return attrs

    def update(self, instance, validated_data):
        new_avatar = validated_data.get('avatar')
        if instance.avatar:
            instance.avatar.delete()
        instance.avatar = new_avatar
        instance.save()
        return instance


class RecipeMinInfoSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = fields


class SubscribeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    recipes = serializers.SerializerMethodField(read_only=True)
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar',
            'recipes', 'recipes_count',
        )
        read_only_fields = (
            'email', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar',
            'recipes', 'recipes_count',
        )

    def get_recipes(self, obj):
        request = self.context['request']
        queruset = obj.recipes.all()
        paginator = AuthorRecipesPagination()
        page = paginator.paginate_queryset(queruset, request)

        if page is not None:
            serializer = RecipeMinInfoSerializer(
                page,
                many=True,
            )
        else:
            serializer = RecipeMinInfoSerializer(
                queruset,
                many=True,
            )
        return serializer.data

    def get_recipes_count(self, obj):
        return obj.recipes.all().count()

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request.user.is_authenticated:
            return request.user.subscription.filter(id=obj.id).exists()
        return False

    def validate(self, data):
        author = get_object_or_404(
            User,
            id=data['id']
        )
        user = self.context['request'].user

        if author == user:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя'
            )

        if user.subscription.filter(id=author.id).exists():
            raise serializers.ValidationError(
                'Подписка на выбранного автора уже создана'
            )

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        author = get_object_or_404(User, id=validated_data['id'])
        user.subscription.add(author)
        return author


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')
        read_only_fields = fields


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')
        read_only_fields = fields


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), source='ingredient',
    )
    amount = serializers.IntegerField(
        required=True,
    )
    name = serializers.CharField(required=False, source='ingredient.name',)
    measurement_unit = serializers.CharField(
        required=False,
        source='ingredient.measurement_unit',
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount',)
        read_only_fields = ('name', 'measurement_unit',)


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(
        required=True,
        many=True,
        source='recipe_ingredient'
    )
    author = UserSerializer(read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        required=True,
        many=True,
    )
    text = serializers.CharField(required=True,)
    image = Base64ImageField(required=True)
    name = serializers.CharField(
        max_length=settings.RECIPE_NAME_MAX,
        required=True,
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'name', 'image', 'text', 'cooking_time',
            'is_favorited', 'is_in_shopping_cart'
        )
        read_only_fields = (
            'id',
            'author',
            'is_favorited',
            'is_in_shopping_cart',
        )

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return Favorite.objects.filter(
                user=user, recipe=obj
            ).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return ShoppingCart.objects.filter(
                user=user, recipe=obj
            ).exists()
        return False

    def validate(self, data):
        required_fields = [
            'tags', 'recipe_ingredient', 'name',
            'image', 'text', 'cooking_time',
        ]

        for field in required_fields:
            if self.context['request'].method == 'PATCH' and field == 'image':
                continue
            if not data.get(field):
                raise serializers.ValidationError(
                    {f'{field}': 'Обязательное поле'}
                )
        return data

    def validate_tags(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                'Нельзя добавить один тег дважды'
            )
        return value

    def validate_ingredients(self, value):
        ingredients = []

        for obj in value:
            if obj['amount'] < settings.MIN_VALUE_FOR_AMOUNT_COOKING_TIME:
                error_message = (
                    f'Мин. значение должно быть равно'
                    f' {settings.MIN_VALUE_FOR_AMOUNT_COOKING_TIME}'
                )
                raise serializers.ValidationError({'amount': error_message})
            ingredients.append(obj['ingredient'])

        if len(ingredients) != len(set(ingredients)):
            raise serializers.ValidationError(
                "Нельзя добавить один ингредиент дважды"
            )

        return value

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredient')
        tags = validated_data.pop('tags')

        recipe = Recipe.objects.create(**validated_data)

        for ingredient_data in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe, **ingredient_data
            )

        recipe.tags.set(tags)

        return recipe

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time',
            instance.cooking_time
        )
        instance.image = validated_data.get('image', instance.image)
        ingredients_data = validated_data.pop('recipe_ingredient')

        current_ingredients = instance.recipe_ingredient.values_list(
            'ingredient__id', flat=True
        )
        for ingredient_data in ingredients_data:
            ingredient = ingredient_data['ingredient']
            if ingredient.id in current_ingredients:
                instance.recipe_ingredient.filter(
                    ingredient_id=ingredient
                ).update(amount=ingredient_data['amount'])
            else:
                RecipeIngredient.objects.create(
                    recipe=instance, **ingredient_data
                )

        tags = validated_data.pop('tags')
        instance.tags.set(tags)

        instance.save()
        return instance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['tags'] = TagSerializer(instance.tags.all(), many=True).data
        return rep


class RecipeActionSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Recipe.objects.all(), source='recipe'
    )

    class Meta:
        model = Favorite
        fields = ('id',)

    def validate(self, data):
        if self.Meta.model.objects.filter(
            recipe=data['recipe'],
            user=self.context['request'].user
        ).exists():
            raise serializers.ValidationError(
                'Нельзя дважды добавить выбранный рецепт'
            )
        return data

    def create(self, validated_data):
        return self.Meta.model.objects.create(
            recipe=validated_data['recipe'],
            user=self.context['request'].user
        )

    def to_representation(self, instance):
        recipe = instance.recipe
        return RecipeMinInfoSerializer(
            recipe,
            context=self.context
        ).to_representation(recipe)


class ShortLinkSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(write_only=True)
    short_url = serializers.CharField(max_length=6)

    class Meta:
        model = ShortLinkForRecipe
        fields = ('id', 'short_url',)

    def create(self, validated_data):
        short_url, created = self.Meta.model.objects.get_or_create(
            recipe_id=validated_data['id'],
            short_url=validated_data['short_url'],
        )
        return short_url.short_url

    def to_representation(self, instance):
        base_url = self.context['request'].build_absolute_uri('/')
        return {
            'short-link': f'{base_url}s/{instance}/'
        }
