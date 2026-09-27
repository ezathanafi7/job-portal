from typing import Any, ClassVar

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class Role(models.TextChoices):
    """The 3 types of user in the system.

    The first value is what's stored in the database, the second is the label shown to humans.
    """

    JOB_SEEKER = "job_seeker", "Job seeker"
    EMPLOYER = "employer", "Employer"
    ADMIN = "admin", "Admin"


class UserManager(BaseUserManager["User"]):
    """Controls how users are created (User.objects.create_user / create_superuser)."""

    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email: str | None) -> str:
        # Make the whole email lowercase, so "Ali@Gmail.com" and "ali@gmail.com"
        # are treated as the same account.
        return (email or "").strip().lower()

    def create_user(self, email: str, password: str | None = None, **extra: Any) -> "User":
        if not email:
            raise ValueError("Users must have an email address.")
        extra.setdefault("role", Role.JOB_SEEKER)
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)  # hashes the password with Argon2, never stores it in plain text
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra: Any) -> "User":
        # Superusers are always admins and can use the Django admin panel.
        extra.update(role=Role.ADMIN, is_staff=True, is_superuser=True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Our custom user: logs in with email and has exactly one role."""

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.JOB_SEEKER,
        db_index=True,  # we'll often filter users by role, so index it for speed
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(
        default=False, help_text="Can log in to the Django admin panel."
    )
    date_joined = models.DateTimeField(default=timezone.now)

    objects: ClassVar[UserManager] = UserManager()

    USERNAME_FIELD = "email"          # log in with email instead of username
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]   # asked for by `createsuperuser` (besides email + password)

    class Meta:
        ordering = ["-date_joined"]   # newest users first

    def __str__(self) -> str:
        return self.email

    def clean(self) -> None:
        super().clean()
        self.email = UserManager.normalize_email(self.email)

    # Handy shortcuts, e.g. `if request.user.is_employer:`
    @property
    def is_job_seeker(self) -> bool:
        return self.role == Role.JOB_SEEKER

    @property
    def is_employer(self) -> bool:
        return self.role == Role.EMPLOYER

    @property
    def is_portal_admin(self) -> bool:
        return self.role == Role.ADMIN

class RefreshSession(models.Model):
    """One row for every refresh token we issue (one per login / device).

    Lets us:
      * log a user out (mark the row revoked),
      * replace the token every time it's used ("rotation"),
      * detect a stolen token being used a second time.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refresh_sessions")
    jti = models.CharField(max_length=64, unique=True)  # matches the token's "jti" claim
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)  # set on logout / rotation
    user_agent = models.CharField(max_length=255, blank=True)  # which browser/device
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "revoked_at"], name="refresh_user_revoked_idx")]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.jti}"

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > timezone.now()