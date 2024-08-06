from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserProfile(AbstractUser):
    email = models.EmailField(
        unique=True,
        max_length=settings.USER_PROFILE_EMAIL_MAX,
        help_text='Электронная почта пользователя',
    )
    first_name = models.CharField(max_length=settings.USER_PROFILE_NAME_MAX,)
    last_name = models.CharField(max_length=settings.USER_PROFILE_NAME_MAX,)
    subscription = models.ManyToManyField(
        'self', blank=True, symmetrical=False,
        help_text='Подписка пользователя на других пользователей',
    )
    avatar = models.ImageField(
        upload_to='users/images/',
        null=True,
        default=None,
        blank=True
    )

    USERNAME_FIELD = 'email'

    REQUIRED_FIELDS = (
        'username',
        'first_name',
        'last_name',
    )
