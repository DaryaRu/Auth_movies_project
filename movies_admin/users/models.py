import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _

from users.managers import CustomUserManager

class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("email"), max_length=255, blank=True)
    phone = models.CharField(_("email"), max_length=20, blank=True)
    hashed_password = models.CharField(_("password"), max_length=255, blank=True)
    is_active = models.BooleanField(_("is active"), default=True)
    is_superuser = models.BooleanField(_("is superuser"), default=False)
    is_staff = models.BooleanField(_("is staff"), default=False)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    modified = models.DateTimeField(_('modified'), auto_now=True)
    last_login = None
    password = None
    
    
    USERNAME_FIELD = 'email'
    
    objects = CustomUserManager()
    
    class Meta:
        db_table = "users"

        constraints = [
            models.UniqueConstraint(
                fields=["email"],
                condition=models.Q(email__isnull=False),
                name="ix_users_email_unique",
            ),
            models.UniqueConstraint(
                fields=["phone"],
                condition=models.Q(phone__isnull=False),
                name="ix_users_phone_unique",
            ),
        ]
        
    def __str__(self):
        return f'{self.email or self.phone}'
    
    def has_perm(self, perm, obj=None):
        if self.is_active and self.is_superuser:
            return True
        return False
    
    def has_module_perms(self, app_label):
        if self.is_active and self.is_superuser:
            return True
        return False
