from django.urls import path

from .views import (
    admin_dashboard,
    admin_create_job,
    admin_jobs,
    admin_settings,
    admin_user_create,
    admin_user_edit,
    admin_user_list,
    login_view,
    logout_view,
    user_dashboard,
)


urlpatterns = [
    path("", login_view, name="login"),
    path("admin-panel/", admin_dashboard, name="admin-dashboard"),
    path("admin-panel/users/", admin_user_list, name="admin-user-list"),
    path("admin-panel/users/new/", admin_user_create, name="admin-user-create"),
    path("admin-panel/users/<int:user_id>/edit/", admin_user_edit, name="admin-user-edit"),
    path("admin-panel/jobs/", admin_jobs, name="admin-jobs"),
    path("admin-panel/jobs/new/", admin_create_job, name="admin-create-job"),
    path("admin-panel/settings/", admin_settings, name="admin-settings"),
    path("workspace/", user_dashboard, name="user-dashboard"),
    path("logout/", logout_view, name="logout"),
]
