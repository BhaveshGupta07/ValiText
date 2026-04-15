from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AdminUserForm, JobCreateForm
from .models import UserProfile, Job, Sentence


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
def user_dashboard(request):
    jobs = Job.objects.filter(validated_by=request.user)

    job_data = []
    for idx, job in enumerate(jobs, start=1):
        total = job.sentences.count()
        done = job.sentences.filter(edit_made=True).count()

        status = "Completed" if done == total and total > 0 else "Pending"

        job_data.append({
            "no": idx,
            "job_id": job.job_id,
            "name": job.name,
            "total": total,
            "done": done,
            "status": status
        })

    # pagination (5 per page)
    paginator = Paginator(job_data, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj
    }

    return render(request, "user/dashboard.html", context)


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

    jobs = Job.objects.all().order_by("-created_at")
    context = {
        "jobs": jobs,
        "display_name": request.user.get_full_name() or request.user.username or "Admin",
    }
    return render(request, "admin_jobs.html", context)


@login_required(login_url="login")
def admin_create_job(request: HttpRequest) -> HttpResponse:
    if not request.user.is_superuser:
        return redirect("user-dashboard")

    if request.method == "POST":
        form = JobCreateForm(request.POST, request.FILES)
        if form.is_valid():
            job = form.save()
            sentence_count = getattr(job, 'sentence_count', len(job.sentences.all()))
            messages.success(request, f'Job "{job.name}" created successfully with {sentence_count} sentences.')
            return redirect("admin-jobs")
    else:
        form = JobCreateForm()
    
    context = {
        "form": form,
        "display_name": request.user.get_full_name() or request.user.username or "Admin",
    }
    return render(request, "admin_create_job.html", context)


@login_required(login_url="login")
def admin_settings(request: HttpRequest) -> HttpResponse:
    if not request.user.is_superuser:
        return redirect("user-dashboard")

    return render(request, "admin_settings.html")

@login_required
def user_dashboard(request):
    return render(request, "user/dashboard.html")


@login_required
def user_jobs(request):
    if request.method == "POST":
        job_id = request.POST.get("job_id")
        job = get_object_or_404(Job, job_id=job_id)

        job.validated_by = request.user
        job.save()

        return redirect("user-assigned-jobs")

    jobs = Job.objects.filter(validated_by__isnull=True)

    return render(request, "user/jobs.html", {"jobs": jobs})


@login_required
def user_assigned_jobs(request):
    jobs = Job.objects.filter(validated_by=request.user)

    return render(request, "user/assigned_jobs.html", {"jobs": jobs})


@login_required
def user_job_detail(request, job_id):
    job = get_object_or_404(Job, job_id=job_id, validated_by=request.user)
    sentences = job.sentences.all()

    if request.method == "POST":
        for s in sentences:
            edited = request.POST.get(str(s.sentence_id))
            if edited:
                s.validated_translation = edited
                s.edit_made = (edited != s.tgt_sentence)
                s.validated_by = request.user
                s.save()

        job.edit_made = True
        job.save()

        return redirect("user-assigned-jobs")

    return render(request, "user/assigned_job_detail.html", {
        "job": job,
        "sentences": sentences
    })