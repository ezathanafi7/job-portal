from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import BaseUserCreationForm
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm

from .models import User


class UserCreationForm(BaseUserCreationForm):
    """The 'Add user' form in the admin panel."""

    class Meta:
        model = User
        fields = ("email", "full_name", "role")


class UserChangeForm(BaseUserChangeForm):
    """The 'Edit user' form in the admin panel."""

    class Meta:
        model = User
        fields = "__all__"
        field_classes: dict = {}


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    # Columns in the user list
    list_display = ("email", "full_name", "role", "is_active", "is_staff", "date_joined")
    # Filters in the right sidebar
    list_filter = ("role", "is_active", "is_staff")
    # Search box searches these fields
    search_fields = ("email", "full_name")
    ordering = ("-date_joined",)
    readonly_fields = ("last_login", "date_joined")

    # Layout of the "edit user" page
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name", "role")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )

    # Layout of the "add user" page
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "role", "password1", "password2"),
            },
        ),
    )