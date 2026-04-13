from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render


def login_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        role = request.POST.get("role", "user")

        request.session["display_name"] = username or "Translation Specialist"
        request.session["role"] = role

        if role == "admin":
            return redirect("admin-dashboard")
        return redirect("user-dashboard")

    existing_role = request.session.get("role")
    if existing_role == "admin":
        return redirect("admin-dashboard")
    if existing_role == "user":
        return redirect("user-dashboard")

    return render(request, "login.html")


def admin_dashboard(request: HttpRequest) -> HttpResponse:
    if request.session.get("role") != "admin":
        return redirect("login")

    context = {
        "display_name": request.session.get("display_name", "Admin Lead"),
        "role_label": "Administrator",
    }
    return render(request, "admin_dashboard.html", context)


def user_dashboard(request: HttpRequest) -> HttpResponse:
    if request.session.get("role") != "user":
        return redirect("login")

    context = {
        "display_name": request.session.get("display_name", "Validator"),
        "role_label": "Validation User",
    }
    return render(request, "user_dashboard.html", context)


def logout_view(request: HttpRequest) -> HttpResponse:
    request.session.flush()
    return redirect("login")
