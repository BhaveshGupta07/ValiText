from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AdminUserForm
from .models import UserProfile


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect("admin-dashboard")
        return redirect("user-dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.is_superuser:
                return redirect("admin-dashboard")
            return redirect("user-dashboard")

        return render(
            request,
            "login.html",
            {"error": "Invalid username or password. Please try again."},
        )

    return render(request, "login.html")


@login_required(login_url="login")
def admin_dashboard(request: HttpRequest) -> HttpResponse:
    if not request.user.is_superuser:
        return redirect("user-dashboard")

    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = User.objects.filter(is_active=False).count()

    context = {
        "display_name": request.user.get_full_name() or request.user.username or "Admin Lead",
        "role_label": "Administrator",
        "stats": {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": inactive_users,
        },
    }
    return render(request, "admin_dashboard.html", context)


@login_required(login_url="login")
def user_dashboard(request: HttpRequest) -> HttpResponse:
    if request.user.is_superuser:
        return redirect("admin-dashboard")

    context = {
        "display_name": request.user.get_full_name() or request.user.username or "Validator",
        "role_label": "Validation User",
    }
    return render(request, "user_dashboard.html", context)


def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("login")


@login_required(login_url="login")
def admin_user_list(request: HttpRequest) -> HttpResponse:
    if not request.user.is_superuser:
        return redirect("user-dashboard")

    users = User.objects.select_related("profile").order_by("-date_joined")
    for user in users:
        try:
            user.profile
        except User.profile.RelatedObjectDoesNotExist:
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "fullname": user.get_full_name(),
                    "approved": user.is_active,
                },
            )
    users = User.objects.select_related("profile").order_by("-date_joined")
    context = {
        "users": users,
        "display_name": request.user.get_full_name() or request.user.username or "Admin",
        "unapproved_count": users.filter(profile__approved=False).count(),
    }
    return render(request, "admin_user_list.html", context)


@login_required(login_url="login")
def admin_user_create(request: HttpRequest) -> HttpResponse:
    if not request.user.is_superuser:
        return redirect("user-dashboard")

    if request.method == "POST":
        form = AdminUserForm(request.POST, edit_mode=False)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User "{user.username}" created successfully.')
            return redirect("admin-user-list")
    else:
        form = AdminUserForm(edit_mode=False)

    return render(
        request,
        "admin_user_form.html",
        {
            "form": form,
            "edit_mode": False,
            "page_title": "Add User",
        },
    )


@login_required(login_url="login")
def admin_user_edit(request: HttpRequest, user_id: int) -> HttpResponse:
    if not request.user.is_superuser:
        return redirect("user-dashboard")

    target_user = get_object_or_404(User, pk=user_id)

    if request.method == "POST":
        if "discard" in request.POST:
            username = target_user.username
            target_user.delete()
            messages.success(request, f'User "{username}" deleted successfully.')
            return redirect("admin-user-list")

        form = AdminUserForm(request.POST, instance=target_user, edit_mode=True)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User "{user.username}" updated successfully.')
            return redirect("admin-user-list")
    else:
        form = AdminUserForm(instance=target_user, edit_mode=True)

    return render(
        request,
        "admin_user_form.html",
        {
            "form": form,
            "edit_mode": True,
            "page_title": "Edit User",
            "target_user": target_user,
        },
    )


@login_required(login_url="login")
def admin_jobs(request: HttpRequest) -> HttpResponse:
    if not request.user.is_superuser:
        return redirect("user-dashboard")

    return render(
        request,
        "admin_jobs.html",
        {
            "sample_jobs": [
                {"title": "Homepage Strings Review", "pair": "English -> Hindi", "status": "In Review"},
                {"title": "Support FAQ Validation", "pair": "English -> Odia", "status": "Queued"},
                {"title": "Policy Update Check", "pair": "English -> Kashmiri", "status": "Completed"},
            ]
        },
    )


@login_required(login_url="login")
def admin_create_job(request: HttpRequest) -> HttpResponse:
    if not request.user.is_superuser:
        return redirect("user-dashboard")

    return render(request, "admin_create_job.html")


@login_required(login_url="login")
def admin_settings(request: HttpRequest) -> HttpResponse:
    if not request.user.is_superuser:
        return redirect("user-dashboard")

    return render(request, "admin_settings.html")
