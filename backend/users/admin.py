from django.contrib import admin
from django.contrib.auth import get_user_model

User = get_user_model()


class UserAdmin(admin.ModelAdmin):

    fieldsets = [
        ('Данные пользователя', {'fields': [
            'email',
            'username',
            'first_name',
            'last_name',
            'avatar',
            'password',
            'date_joined',
        ]}),
        ('Права доступа и статус', {'fields': [
            'is_staff',
            'is_active',
        ]}),
    ]
    list_display = (
        'email',
        'username',
    )
    search_fields = ('email', 'username')
    list_filter = ('is_staff',)


admin.site.register(User, UserAdmin)
