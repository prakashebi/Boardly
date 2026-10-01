from django.urls import path
from core import views

urlpatterns = [
    # Auth
    path("auth/register", views.register, name="register"),
    path("auth/login", views.login, name="login"),

    # Users
    path("users/me", views.user_me, name="user_me"),
    path("users", views.user_list, name="user_list"),
    path("users/<uuid:user_id>", views.user_detail, name="user_detail"),

    # Entities
    path("entities", views.entity_list_create, name="entity_list_create"),
    path("entities/<uuid:entity_id>", views.entity_detail, name="entity_detail"),

    # Members
    path("entities/<uuid:entity_id>/members", views.member_list_create, name="member_list_create"),
    path("entities/<uuid:entity_id>/members/<uuid:member_user_id>", views.member_detail, name="member_detail"),

    # Attachments
    path("entities/<uuid:entity_id>/attachments", views.upload_attachment, name="upload_attachment"),
    path("attachments/<uuid:entity_id>/<str:attachment_id>", views.download_attachment, name="download_attachment"),
    path("entities/<uuid:entity_id>/attachments/<str:attachment_id>", views.delete_attachment, name="delete_attachment"),

    # Events
    path("events", views.list_events, name="list_events"),
]
