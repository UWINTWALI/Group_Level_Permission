from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from .models import SystemConfig, User, Post, Permission
from .forms import PostForm, UserRegistrationForm, UserEditForm, CustomLoginForm
from .utils import send_email

def is_admin(user):
    return user.is_authenticated and user.role == 'admin'

def register(request):
    try:
        config = SystemConfig.objects.first()
        if not config:
            config = SystemConfig.objects.create()
        
        if config.registration_mode == 'disabled':
            messages.error(request, _('Registration is currently disabled.'))
            return redirect('dashboard')
        elif config.registration_mode == 'invitation' and not request.user.is_staff:
            messages.error(request, _('Registration is currently invitation-only. Please contact an administrator.'))
            return redirect('dashboard')
        
        if request.method == 'POST':
            form = UserRegistrationForm(request.POST, request.FILES)
            if form.is_valid():
                user = form.save()
                login(request, user)
                
                # Send welcome email
                email_context = {
                    'user': user,
                    'site_url': settings.SITE_URL
                }
                send_email(
                    subject=_('Welcome to Our Platform!'),
                    template_name='emails/registration.html',
                    context=email_context,
                    recipient_list=[user.email]
                )
                
                messages.success(request, _('Registration successful! A welcome email has been sent to your inbox.'))
                return redirect('dashboard')
        else:
            form = UserRegistrationForm()
        
        return render(request, 'blog/register.html', {
            'form': form,
            'registration_mode': config.registration_mode
        })
    
    except Exception as e:
        messages.error(request, _('An error occurred during registration. Please try again later.'))
        return redirect('dashboard')

@login_required
def dashboard(request):
    # Get posts based on user role
    if request.user.role == 'admin':
        # Admins can see all posts
        posts = Post.objects.all()
        template = 'blog/admin_dashboard.html'
    elif request.user.role == 'publisher':
        # Publishers can see all posts
        posts = Post.objects.all()
        template = 'blog/editor_dashboard.html'
    elif request.user.role == 'editor':
        # Editors can see all published posts and their own unpublished posts
        published_posts = Post.objects.filter(published=True)
        own_posts = Post.objects.filter(author=request.user, published=False)
        posts = published_posts | own_posts
        template = 'blog/editor_dashboard.html'
    elif request.user.role == 'author':
        # Authors can see their own posts
        posts = Post.objects.filter(author=request.user)
        template = 'blog/author_dashboard.html'
    else:
        # Regular users can only see published posts
        posts = Post.objects.filter(published=True)
        template = 'blog/author_dashboard.html'
    
    context = {
        'posts': posts,
        'user_posts_count': Post.objects.filter(author=request.user).count()
    }
    
    return render(request, template, context)

@user_passes_test(is_admin)
def manage_users(request):
    users = User.objects.all()
    permissions = Permission.objects.all()
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        permission_id = request.POST.get('permission_id')
        action = request.POST.get('action')
        
        if user_id and permission_id and action:
            user = get_object_or_404(User, user_id=user_id)
            permission = get_object_or_404(Permission, id=permission_id)
            
            if action == 'add':
                user.user_permissions.add(permission)
                messages.success(request, _('Permission added successfully!'))
            elif action == 'remove':
                user.user_permissions.remove(permission)
                messages.success(request, _('Permission removed successfully!'))
    
    return render(request, 'blog/manage_users.html', {
        'users': users,
        'permissions': permissions,
        'role_choices': User.ROLE_CHOICES
    })

@user_passes_test(is_admin)
def create_user(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            messages.success(request, _('User created successfully!'))
            return redirect('manage_users')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'blog/user_form.html', {
        'form': form,
        'title': _('Create User')
    })

@user_passes_test(is_admin)
def edit_user(request, user_id):
    user = get_object_or_404(User, user_id=user_id)
    if request.method == 'POST':
        form = UserEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, _('User updated successfully!'))
            return redirect('manage_users')
    else:
        form = UserEditForm(instance=user)
    
    return render(request, 'blog/user_form.html', {
        'form': form,
        'title': _('Edit User')
    })

@user_passes_test(is_admin)
def toggle_user_status(request, user_id):
    user = get_object_or_404(User, user_id=user_id)
    if not user.is_superuser:
        user.is_active = not user.is_active
        user.save()
        messages.success(request, _('User status updated successfully!'))
    else:
        messages.error(request, _('Cannot modify superuser status!'))
    return redirect('manage_users')

@user_passes_test(is_admin)
def update_user_permissions(request, user_id):
    user = get_object_or_404(User, user_id=user_id)
    if request.method == 'POST':
        permissions = {}
        if request.POST.get('can_publish'):
            permissions['publish'] = True
        if request.POST.get('can_edit_all'):
            permissions['edit_all'] = True
        user.permissions = permissions
        user.save()
        messages.success(request, _('User permissions updated successfully!'))
    return redirect('manage_users')

@user_passes_test(is_admin)
def update_user_role(request, user_id):
    user = get_object_or_404(User, user_id=user_id)
    
    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in dict(User.ROLE_CHOICES):
            user.role = new_role
            user.save()
            messages.success(request, _('User role updated successfully!'))
        else:
            messages.error(request, _('Invalid role selected!'))
    
    return redirect('manage_users')

@user_passes_test(is_admin)
def delete_user(request, user_id):
    user = get_object_or_404(User, user_id=user_id)
    
    # Don't allow deleting superusers
    if user.is_superuser:
        messages.error(request, _('Cannot delete superuser accounts!'))
        return redirect('manage_users')
    
    # Don't allow deleting yourself
    if user == request.user:
        messages.error(request, _('You cannot delete your own account!'))
        return redirect('manage_users')
    
    if request.method == 'POST':
        user.delete()
        messages.success(request, _('User deleted successfully!'))
        return redirect('manage_users')
    
    return render(request, 'blog/confirm_delete.html', {
        'object': user,
        'title': _('Delete User'),
        'message': _('Are you sure you want to delete this user? This action cannot be undone.'),
        'cancel_url': 'manage_users'
    })

@login_required
def create_post(request):
    # Allow admins and users with appropriate roles to create posts
    if request.user.role not in ['admin', 'author', 'editor', 'publisher'] and not request.user.is_superuser:
        messages.error(request, _("You don't have permission to create posts."))
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            
            # Only admins and publishers can create published posts
            if not request.user.role in ['admin', 'publisher']:
                post.published = False
                
            post.save()
            messages.success(request, _('Post created successfully!'))
            return redirect('dashboard')
    else:
        form = PostForm()
    
    return render(request, 'blog/post_form.html', {
        'form': form,
        'title': _('Create Post')
    })

@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    # Check permissions based on role
    if request.user.role == 'admin':
        # Admins can edit any post
        pass
    elif request.user.role == 'publisher':
        # Publishers can edit any post
        pass
    elif request.user.role == 'editor':
        # Editors can edit published posts and their own unpublished posts
        if not post.published and post.author != request.user:
            messages.error(request, _("You don't have permission to edit this post."))
            return redirect('dashboard')
    elif request.user.role == 'author':
        # Authors cannot edit posts
        messages.error(request, _("Authors cannot edit posts."))
        return redirect('dashboard')
    else:
        messages.error(request, _("You don't have permission to edit this post."))
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            post = form.save()
            
            # Check if this is a publish action
            if request.POST.get('action') == 'publish' and request.user.role in ['admin', 'publisher']:
                post.published = True
                post.save()
                messages.success(request, _('Post published successfully!'))
            else:
                messages.success(request, _('Post updated successfully!'))
            
            return redirect('dashboard')
    else:
        form = PostForm(instance=post)
    
    return render(request, 'blog/post_form.html', {
        'form': form,
        'title': _('Edit Post'),
        'post': post
    })

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    # Check permissions based on role
    if request.user.role == 'admin':
        # Admins can delete any post
        pass
    elif request.user.role == 'publisher':
        # Publishers can delete any post
        pass
    elif request.user.role == 'author':
        # Authors cannot delete posts
        messages.error(request, _("Authors cannot delete posts."))
        return redirect('dashboard')
    else:
        messages.error(request, _("You don't have permission to delete this post."))
        return redirect('dashboard')
    
    if request.method == 'POST':
        post.delete()
        messages.success(request, _('Post deleted successfully!'))
        return redirect('dashboard')
    
    return render(request, 'blog/confirm_delete.html', {
        'object': post,
        'title': _('Delete Post'),
        'message': _('Are you sure you want to delete this post? This action cannot be undone.'),
        'cancel_url': 'dashboard'
    })

def custom_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, email=email, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, _('Welcome back!'))
                    return redirect('dashboard')
                else:
                    messages.error(request, _('Your account is inactive. Please contact the administrator.'))
            else:
                messages.error(request, _('Invalid email or password.'))
    else:
        form = CustomLoginForm()
    
    return render(request, 'blog/login.html', {'form': form})

def custom_logout(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, _('You have been logged out successfully.'))
    return redirect('dashboard')

@login_required
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    # Check permissions based on role
    if request.user.role == 'admin':
        # Admins can view any post
        pass
    elif request.user.role == 'publisher':
        # Publishers can view any post
        pass
    elif request.user.role == 'editor':
        # Editors can view published posts and their own unpublished posts
        if not post.published and post.author != request.user:
            messages.error(request, _("You don't have permission to view this post."))
            return redirect('dashboard')
    elif request.user.role == 'author':
        # Authors can view their own posts
        if post.author != request.user:
            messages.error(request, _("You don't have permission to view this post."))
            return redirect('dashboard')
    elif post.published:
        # Regular users can only view published posts
        pass
    else:
        messages.error(request, _("You don't have permission to view this post."))
        return redirect('dashboard')
    
    return render(request, 'blog/post_detail.html', {
        'post': post
    })

@login_required
def profile(request):
    # Get user's posts
    if request.user.role == 'admin':
        posts = Post.objects.all()
    elif request.user.role == 'publisher':
        posts = Post.objects.all()
    elif request.user.role == 'editor':
        published_posts = Post.objects.filter(published=True)
        own_posts = Post.objects.filter(author=request.user, published=False)
        posts = published_posts | own_posts
    elif request.user.role == 'author':
        posts = Post.objects.filter(author=request.user)
    else:
        posts = Post.objects.filter(published=True)
    
    context = {
        'posts': posts.order_by('-created_at'),
        'user_posts_count': Post.objects.filter(author=request.user).count()
    }
    
    return render(request, 'blog/profile.html', context)

@user_passes_test(is_admin)
def manage_user_permissions(request, user_id):
    user = get_object_or_404(User, user_id=user_id)
    
    # Get all available permissions
    content_type = ContentType.objects.get_for_model(Post)
    all_permissions = Permission.objects.filter(content_type=content_type)
    
    # Get user's current permissions
    user_permissions = user.user_permissions.filter(content_type=content_type)
    
    # Get available permissions (those not assigned to the user)
    available_permissions = all_permissions.exclude(id__in=user_permissions.values_list('id', flat=True))
    
    if request.method == 'POST':
        # Get the selected permissions from the form
        granted_permissions = request.POST.getlist('granted[]')
        
        # Clear existing permissions and add new ones
        user.user_permissions.remove(*all_permissions)
        if granted_permissions:
            user.user_permissions.add(*Permission.objects.filter(id__in=granted_permissions))
        
        # Update user's dashboard permissions
        update_user_dashboard_permissions(user)
        
        messages.success(request, _('Permissions updated successfully!'))
        return redirect('manage_users')
    
    return render(request, 'blog/manage_permissions.html', {
        'user': user,
        'available_permissions': available_permissions,
        'user_permissions': user_permissions,
    })

def update_user_dashboard_permissions(user):
    """Update user's dashboard permissions based on granted permissions"""
    permissions = user.get_all_permissions()
    dashboard_perms = {
        'can_publish': 'blog.can_publish_post' in permissions,
        'can_edit_all': 'blog.can_edit_all_posts' in permissions,
        'can_delete': 'blog.delete_post' in permissions,
        'can_view_stats': 'blog.can_view_stats' in permissions,
    }
    user.permissions = dashboard_perms
    user.save()
