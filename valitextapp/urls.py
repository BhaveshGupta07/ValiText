from django.urls import path

from .views import admin_dashboard, login_view, logout_view, user_dashboard


urlpatterns = [
    path("", login_view, name="login"),
    path("admin-panel/", admin_dashboard, name="admin-dashboard"),
    path("workspace/", user_dashboard, name="user-dashboard"),
    path("logout/", logout_view, name="logout"),
]
