from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from .models import Post

@receiver(post_migrate)
def setup_groups(sender, **kwargs):
    # Create groups if they don't exist
    author_group, created = Group.objects.get_or_create(name='author')
    editor_group, created = Group.objects.get_or_create(name='editor')
    publisher_group, created = Group.objects.get_or_create(name='publisher')

    # Get content type for Post model
    content_type = ContentType.objects.get_for_model(Post)

    # Get all permissions for Post model
    post_permissions = Permission.objects.filter(content_type=content_type)

    # Assign permissions to groups
    # Author: can add + view posts only
    author_permissions = post_permissions.filter(codename__in=['add_post', 'view_post'])
    author_group.permissions.set(author_permissions)

    # Editor: can add + view + change posts
    editor_permissions = post_permissions.filter(codename__in=['add_post', 'view_post', 'change_post'])
    editor_group.permissions.set(editor_permissions)

    # Publisher: can add + view + change + delete posts
    publisher_permissions = post_permissions.filter(codename__in=['add_post', 'view_post', 'change_post', 'delete_post'])
    publisher_group.permissions.set(publisher_permissions)