from django.shortcuts import get_object_or_404, redirect

from .models import ShortLinkForRecipe


def redirect_to_recipe(request, short_url):
    obj_url = get_object_or_404(ShortLinkForRecipe, short_url=short_url)
    pk = obj_url.recipe.id
    return redirect(f'http://127.0.0.1:8000/api/recipes/{pk}/')
