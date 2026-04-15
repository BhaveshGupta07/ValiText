from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

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
    all_jobs = Job.objects.all()
    assigned_jobs_qs = Job.objects.filter(validated_by_id=request.user.id)

    total_jobs = all_jobs.filter(validated_by__isnull=True).count()
    assigned_jobs = assigned_jobs_qs.count()
    completed_jobs = assigned_jobs_qs.filter(edit_made=True).count()

    job_data = []
    for idx, job in enumerate(assigned_jobs_qs, start=1):
        total = job.sentences.count()
        done = job.sentences.filter(edit_made=True).count()

        status = "Completed" if total > 0 and done == total else "Pending"

        job_data.append({
            "no": idx,
            "job_id": job.job_id,
            "name": job.name,
            "total": total,
            "done": done,
            "status": status
        })

    paginator = Paginator(job_data, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "stats": {
            "total_jobs": total_jobs,
            "assigned_jobs": assigned_jobs,
            "completed_jobs": completed_jobs,
        },
        "page_obj": page_obj
    }
    print("Assigned jobs:", assigned_jobs_qs)
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
        job = Job.objects.get(job_id=job_id)

        job.validated_by = request.user   # ✅ THIS IS REQUIRED
        job.save()

    jobs = Job.objects.filter(validated_by__isnull=True)

    return render(request, "user/jobs.html", {"jobs": jobs})


@login_required
def user_assigned_jobs(request):
    jobs = Job.objects.filter(validated_by=request.user)

    return render(request, "user/assigned_jobs.html", {"jobs": jobs})


def build_page_items(page_obj):
    total = page_obj.paginator.num_pages
    current = page_obj.number

    if total <= 7:
        return list(range(1, total + 1))

    if current <= 4:
        return [1, 2, 3, "...", total]

    if current >= total - 3:
        return [1, "...", total - 2, total - 1, total]

    return [1, "...", current - 1, current, current + 1, "...", total]


@login_required
def user_job_detail(request, job_id):
    job = get_object_or_404(Job, job_id=job_id, validated_by=request.user)
    sentence_queryset = Sentence.objects.filter(job=job).order_by("sentence_id")

    paginator = Paginator(sentence_queryset, 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    if request.method == "POST":
        post_page_number = request.POST.get("page", page_number)
        page_obj = paginator.get_page(post_page_number)
        action = request.POST.get("action", "draft")
        mark_page_done = action == "submit_page"

        for s in page_obj.object_list:
            edited = request.POST.get(str(s.sentence_id))
            status = request.POST.get(f"status_{s.sentence_id}")

            if edited is not None:
                edit_made = (edited.strip() != s.tgt_sentence.strip())
                next_status = "done" if mark_page_done else (status or "pending")

                if next_status != "done":
                    next_status = "edited" if edit_made else "pending"

                s.validated_translation = edited
                s.edit_made = edit_made
                s.status = next_status
                s.validated_by = request.user
                s.final_date = timezone.now() if next_status == "done" else None
                s.save()

        all_done = (
            sentence_queryset.exists()
            and sentence_queryset.filter(status="done").count() == sentence_queryset.count()
        )
        job.edit_made = all_done
        job.validated_by = request.user
        job.final_date = timezone.now() if all_done else None
        job.save(update_fields=["edit_made", "validated_by", "final_date"])

        return redirect(f"{request.path}?page={page_obj.number}")

    remaining_count = sentence_queryset.exclude(status="done").count()
    done_count = sentence_queryset.filter(status="done").count()
    edited_count = sentence_queryset.filter(edit_made=True).count()
    total_count = sentence_queryset.count()
    progress_percent = round((done_count / total_count) * 100) if total_count else 0

    return render(request, "user/assigned_job_detail.html", {
        "job": job,
        "sentences": page_obj.object_list,
        "page_obj": page_obj,
        "page_items": build_page_items(page_obj),
        "remaining_count": remaining_count,
        "done_count": done_count,
        "edited_count": edited_count,
        "progress_percent": progress_percent,
    })
