from django.contrib import admin

from .models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                     ShoppingCart, Tag)


class IngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 0


class TagInline(admin.TabularInline):
    model = Recipe.tags.through
    extra = 0


class RecipeAdmin(admin.ModelAdmin):
    inlines = (
        IngredientInline,
        TagInline,
    )
    readonly_fields = ('favorites_count',)
    list_display = (
        'name',
        'author',
    )
    search_fields = ('author__email', 'name')
    list_filter = ('tags__slug',)
    date_hierarchy = 'pub_date'

    def favorites_count(self, obj):
        return obj.favorite_recipes.count()

    favorites_count.short_description = 'Добавили в избранное (кол-во раз)'


class UserRecipeAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    list_filter = ('user', 'recipe')
    search_fields = ('user__email', 'recipe__name')


class IngredientAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'measurement_unit'
    )
    search_fields = ('name',)


admin.site.register(Tag)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Favorite, UserRecipeAdmin)
admin.site.register(ShoppingCart, UserRecipeAdmin)
