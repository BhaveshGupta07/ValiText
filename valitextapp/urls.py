from django.urls import path

from .views import (
    admin_dashboard,
    admin_create_job,
    admin_job_assignments,
    admin_assignment_download,
    admin_job_delete,
    admin_jobs,
    admin_settings,
    admin_user_create,
    admin_user_edit,
    admin_user_list,
    login_view,
    logout_view,
    user_dashboard,
    user_assigned_jobs, 
    user_job_detail,
    user_sentence_save
)


urlpatterns = [
    path("", login_view, name="login"),
    path("admin-panel/", admin_dashboard, name="admin-dashboard"),
    path("admin-panel/users/", admin_user_list, name="admin-user-list"),
    path("admin-panel/users/new/", admin_user_create, name="admin-user-create"),
    path("admin-panel/users/<int:user_id>/edit/", admin_user_edit, name="admin-user-edit"),
    path("admin-panel/jobs/", admin_jobs, name="admin-jobs"),
    path("admin-panel/jobs/new/", admin_create_job, name="admin-create-job"),
    path("admin-panel/jobs/<uuid:job_id>/delete/", admin_job_delete, name="admin-job-delete"),
    path("admin-panel/jobs/<uuid:job_id>/assignments/", admin_job_assignments, name="admin-job-assignments"),
    path("admin-panel/jobs/<uuid:job_id>/assignments/<int:user_id>/<str:status>/download/", admin_assignment_download, name="admin-assignment-download"),
    path("admin-panel/settings/", admin_settings, name="admin-settings"),
    path("workspace/", user_dashboard, name="user-dashboard"),
    path("logout/", logout_view, name="logout"),
    path("workspace/assigned/", user_assigned_jobs, name="user-assigned-jobs"),
    path("workspace/job/<uuid:job_id>/", user_job_detail, name="user-job-detail"),
    path("workspace/job/<uuid:job_id>/sentence/<uuid:sentence_id>/save/", user_sentence_save, name="user-sentence-save"),
    path("login/", login_view, name="login"),
]
