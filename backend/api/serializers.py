from django.conf import settings
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import transaction
from django.shortcuts import get_object_or_404
from djoser.serializers import UserSerializer as DjoserUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import (Ingredient, Recipe, RecipeIngredient,
                            ShortLinkForRecipe, Tag, User)

from .pagination import AuthorRecipesPagination


class UserSerializer(DjoserUserSerializer):
    username = serializers.CharField(
        validators=(UnicodeUsernameValidator,),
    )
    avatar = Base64ImageField()
    is_subscribed = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = DjoserUserSerializer.Meta.model
        fields = DjoserUserSerializer.Meta.fields + (
            'is_subscribed', 'avatar',
        )
        read_only_fields = fields


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=False)

    class Meta:
        model = User
        fields = ('avatar',)

    def validate(self, attrs):
        avatar = attrs.get('avatar', None)
        if avatar is None:
            raise serializers.ValidationError(
                {'avatar': 'Необходимо передать изображение для аватара.'}
            )
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        new_avatar = validated_data.get('avatar', None)
        if new_avatar:
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


class BaseRecipeSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(
        required=True,
        many=True,
        source='recipe_ingredient'
    )
    author = UserSerializer(read_only=True)
    text = serializers.CharField(required=True,)
    image = Base64ImageField(required=True)
    name = serializers.CharField(
        max_length=settings.RECIPE_NAME_MAX,
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients',
            'name', 'image', 'text', 'cooking_time',
        )
        read_only_fields = ('id',)


class RecipeWriteSerializer(BaseRecipeSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )

    class Meta:
        model = Recipe
        fields = BaseRecipeSerializer.Meta.fields + (
            'tags',
        )
        read_only_fields = BaseRecipeSerializer.Meta.read_only_fields

    def validate(self, data):
        if 'recipe_ingredient' not in data:
            raise serializers.ValidationError(
                'Поле ингредиенты обязательно'
            )
        if 'tags' not in data:
            raise serializers.ValidationError(
                'Поле теги обязательно'
            )
        return data

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError(
                {'image': 'Необходимо передать изображение рецепта.'}
            )
        return value

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError(
                {'tags': 'Необходимо добавить хоть один тег'}
            )
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                'Нельзя добавить один тег дважды'
            )
        return value

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                {'ingradients': 'Необходимо добавить хоть один ингредиент'}
            )

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

    @transaction.atomic
    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredient')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)

        ingredients_for_recipe = []
        ingredients_for_recipe = [
            RecipeIngredient(recipe=recipe, **ingredient_data)
            for ingredient_data in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(ingredients_for_recipe)

        recipe.tags.set(tags)

        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredient')
        tags = validated_data.pop('tags')
        current_recipe = super().update(instance, validated_data)

        current_recipe.recipe_ingredient.all().delete()

        new_ingredients = [
            RecipeIngredient(recipe=current_recipe, **ingredient_data)
            for ingredient_data in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(new_ingredients)

        instance.tags.set(tags)

        instance.save()
        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(
            self.context
        ).to_representation(instance)


class RecipeReadSerializer(BaseRecipeSerializer):
    tags = TagSerializer(many=True)
    is_favorited = serializers.BooleanField(required=False, default=False)
    is_in_shopping_cart = serializers.BooleanField(
        required=False,
        default=False
    )

    class Meta:
        model = Recipe
        fields = BaseRecipeSerializer.Meta.fields + (
            'tags', 'is_favorited', 'is_in_shopping_cart'
        )
        read_only_fields = fields


class RecipeActionSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Recipe.objects.all(), source='recipe'
    )

    class Meta:
        model = None
        fields = ('id',)

    def validate(self, data):
        user = self.context['request'].user
        if self.Meta.model.objects.filter(
            recipe=data['recipe'],
            user=user
        ).exists():
            raise serializers.ValidationError(
                'Нельзя дважды добавить выбранный рецепт'
            )
        data['user'] = user
        return data

    def create(self, validated_data):
        return self.Meta.model.objects.create(**validated_data)

    def to_representation(self, instance):
        return RecipeMinInfoSerializer(
            context=self.context
        ).to_representation(instance.recipe)


class ShortLinkSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(write_only=True)
    short_url = serializers.CharField(max_length=6)

    class Meta:
        model = ShortLinkForRecipe
        fields = ('id', 'short_url',)

    def create(self, validated_data):
        odj_short_link, created = self.Meta.model.objects.get_or_create(
            recipe_id=validated_data['id'],
            short_url=validated_data['short_url'],
        )
        return odj_short_link.short_url

    def to_representation(self, instance):
        base_url = self.context['request'].build_absolute_uri('/')
        return {
            'short-link': f'{base_url}s/{instance}/'
        }
