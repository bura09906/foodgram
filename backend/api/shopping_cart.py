from core.utils import ShoppingCartPdfGenerator


def shopping_cart_pdf_generator(user):
    user_shopping_cart = user.shoppingcart_user.select_related(
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
        pdf_file = ShoppingCartPdfGenerator(shopping_cart)
        return pdf_file.return_pdf()
