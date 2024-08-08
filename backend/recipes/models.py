from core.models import UserRecipeRelation
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

from .validators import validate_for_recipe

User = get_user_model()


class Tag(models.Model):
    name = models.CharField(
        max_length=settings.TAG_FIELD_MAX,
        unique=True,
        verbose_name='Название тега'
    )
    slug = models.SlugField(
        max_length=settings.TAG_FIELD_MAX,
        unique=True,
        verbose_name='Слаг тега'
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(
        max_length=settings.INGREDIENT_NAME_MAX,
        unique=True,
        verbose_name='Название ингредиента'
    )
    measurement_unit = models.CharField(
        max_length=settings.INGREDIENT_MEAS_UNIT_MAX,
        verbose_name='Единица измерения ингредиента'
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор рецепта',
    )
    name = models.CharField(
        max_length=settings.RECIPE_NAME_MAX,
        verbose_name='Название рецепта',
    )
    image = models.ImageField(
        upload_to='recipe/image',
        verbose_name='Изображение рецепта',
    )
    text = models.TextField(verbose_name='Описание рецепта')
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        verbose_name='Ингредиенты рецепта',
    )
    tags = models.ManyToManyField(
        Tag,
        through='TagsRecipe',
        verbose_name='Теги рецепта',
    )
    cooking_time = models.PositiveIntegerField(
        validators=[validate_for_recipe],
        verbose_name='Время приготовления рецепта',
        help_text='Мин. время приготовления 1'
    )
    pub_date = models.DateTimeField(
        'Дата добавления',
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ['-pub_date']
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент',
    )
    amount = models.PositiveIntegerField(
        validators=[validate_for_recipe],
        verbose_name='Количество ингредиента',
        help_text='Мин. кол-во ингредиента равно 1'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredient',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient',
            )
        ]
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'

    def __str__(self) -> str:
        return f'Ингредиент рецепта {self.recipe.name}'


class TagsRecipe(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        verbose_name='Тег'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'tag'],
                name='unique_recipe_tag',
            )
        ]
        verbose_name = 'Тег рецепта'
        verbose_name_plural = 'Теги рецепта'

    def __str__(self) -> str:
        return f'Тег рецепта {self.recipe.name}'


class Favorite(UserRecipeRelation):
    pass

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'


class ShoppingCart(UserRecipeRelation):
    pass

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Список покупок'


class ShortLinkForRecipe(models.Model):
    recipe = models.OneToOneField(Recipe, on_delete=models.CASCADE)
    short_url = models.CharField(max_length=6, unique=True,)
