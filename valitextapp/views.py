from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render


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

    context = {
        "display_name": request.user.get_full_name() or request.user.username or "Admin Lead",
        "role_label": "Administrator",
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
