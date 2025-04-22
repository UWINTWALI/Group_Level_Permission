from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    
    # User management
    path('users/', views.manage_users, name='manage_users'),
    path('users/create/', views.create_user, name='create_user'),
    path('users/<uuid:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<uuid:user_id>/toggle/', views.toggle_user_status, name='toggle_user_status'),
    path('users/<uuid:user_id>/permissions/', views.manage_user_permissions, name='manage_user_permissions'),
    path('users/<uuid:user_id>/role/', views.update_user_role, name='update_user_role'),
    path('users/<uuid:user_id>/delete/', views.delete_user, name='delete_user'),
    
    # Post management
    path('posts/create/', views.create_post, name='create_post'),
    path('posts/<int:post_id>/edit/', views.edit_post, name='edit_post'),
    path('posts/<int:post_id>/delete/', views.delete_post, name='delete_post'),
    path('posts/<int:post_id>/', views.post_detail, name='post_detail'),
]
