import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, first_name, last_name, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('author', 'Author'),
        ('editor', 'Editor'),
        ('publisher', 'Publisher'),
        ('user', 'Regular User'),
    )
    
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, verbose_name=_('Email Address'))
    first_name = models.CharField(max_length=30, verbose_name=_('First Name'))
    last_name = models.CharField(max_length=30, verbose_name=_('Last Name'))
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    permissions = models.JSONField(default=dict, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_role_permissions(self):
        role_permissions = {
            'admin': ['add', 'view', 'change', 'delete', 'grant_permissions'],
            'publisher': ['add', 'view', 'change', 'delete'],
            'editor': ['add', 'view', 'change'],
            'author': ['add', 'view'],
            'user': ['view']
        }
        return role_permissions.get(self.role, ['view'])

class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class SystemConfig(models.Model):
    REGISTRATION_MODES = (
        ('enabled', 'Public Registration'),
        ('invitation', 'Invitation Only'),
        ('disabled', 'Disabled'),
    )
    
    registration_mode = models.CharField(
        max_length=20,
        choices=REGISTRATION_MODES,
        default='enabled',
        help_text=_('Controls who can register on the site')
    )
    
    class Meta:
        verbose_name = _('System Configuration')
        verbose_name_plural = _('System Configurations')
    
    def __str__(self):
        return f"System Configuration ({self.get_registration_mode_display()})"


