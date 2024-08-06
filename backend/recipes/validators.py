from django.conf import settings
from django.core.exceptions import ValidationError


def validate_for_recipe(value):
    if value < settings.MIN_VALUE_FOR_AMOUNT_COOKING_TIME:
        raise ValidationError(
            f'Мин. значение должно быть'
            f' равно {settings.MIN_VALUE_FOR_AMOUNT_COOKING_TIME}'
        )
    return value
