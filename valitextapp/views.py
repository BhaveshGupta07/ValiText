from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import AdminUserForm, JobAssignmentForm, JobCreateForm
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
    assigned_jobs_qs = Job.objects.filter(sentences__assigned_to=request.user).distinct()

    total_jobs = all_jobs.filter(sentences__assigned_to__isnull=True).distinct().count()
    assigned_jobs = assigned_jobs_qs.count()
    completed_jobs = 0

    job_data = []
    for idx, job in enumerate(assigned_jobs_qs, start=1):
        assigned_sentences = job.sentences.filter(assigned_to=request.user)
        total = assigned_sentences.count()
        done = assigned_sentences.filter(status="done").count()

        status = "Completed" if total > 0 and done == total else "Pending"
        if status == "Completed":
            completed_jobs += 1

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
    return render(request, "user/dashboard.html", context)


def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("login")


def assign_job_sentences(job, user, target_count):
    target_count = max(0, target_count)
    assigned_qs = Sentence.objects.filter(job=job, assigned_to=user)
    current_count = assigned_qs.count()
    completed_count = assigned_qs.filter(status="done").count()

    if target_count < completed_count:
        return False, (
            f"{user.username} already completed {completed_count} sentences. "
            "Allocation cannot be reduced below completed work."
        )

    if target_count > current_count:
        needed = target_count - current_count
        available_ids = list(
            Sentence.objects.filter(job=job, assigned_to__isnull=True)
            .order_by("sentence_number", "sentence_id")
            .values_list("sentence_id", flat=True)[:needed]
        )

        if len(available_ids) < needed:
            return False, (
                f"Only {len(available_ids)} unassigned sentences are available for this job."
            )

        Sentence.objects.filter(sentence_id__in=available_ids).update(
            assigned_to=user,
            assigned_at=timezone.now(),
        )
        return True, f"Assigned {needed} more sentences to {user.username}."

    if target_count < current_count:
        remove_count = current_count - target_count
        removable_ids = list(
            assigned_qs.exclude(status="done")
            .order_by("-sentence_number", "sentence_id")
            .values_list("sentence_id", flat=True)[:remove_count]
        )

        if len(removable_ids) < remove_count:
            return False, (
                f"Cannot remove {remove_count} sentences because too much assigned work is already completed."
            )

        Sentence.objects.filter(sentence_id__in=removable_ids).update(
            assigned_to=None,
            assigned_at=None,
        )
        return True, f"Reduced {user.username}'s allocation by {remove_count} sentences."

    return True, f"{user.username} already has {target_count} assigned sentences."


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

    jobs = Job.objects.annotate(
        total_sentences=Count("sentences"),
        assigned_sentences=Count("sentences", filter=Q(sentences__assigned_to__isnull=False)),
        done_sentences=Count("sentences", filter=Q(sentences__status="done")),
    ).order_by("-created_at")
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
            assign_user = form.cleaned_data.get("assign_user")
            assign_count = form.cleaned_data.get("assign_count")
            if assign_user and assign_count:
                with transaction.atomic():
                    success, assignment_message = assign_job_sentences(job, assign_user, assign_count)
                if not success:
                    messages.error(request, assignment_message)
                    return redirect("admin-job-assignments", job_id=job.job_id)
            sentence_count = getattr(job, 'sentence_count', len(job.sentences.all()))
            messages.success(request, f'Job "{job.name}" created successfully with {sentence_count} sentences.')
            if assign_user and assign_count:
                messages.success(request, f"Initial assignment: {assign_count} sentences assigned to {assign_user.username}.")
            return redirect("admin-jobs")
    else:
        form = JobCreateForm()
    
    context = {
        "form": form,
        "display_name": request.user.get_full_name() or request.user.username or "Admin",
    }
    return render(request, "admin_create_job.html", context)


@login_required(login_url="login")
def admin_job_assignments(request: HttpRequest, job_id) -> HttpResponse:
    if not request.user.is_superuser:
        return redirect("user-dashboard")

    job = get_object_or_404(Job, job_id=job_id)

    if request.method == "POST":
        form = JobAssignmentForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                success, message = assign_job_sentences(
                    job,
                    form.cleaned_data["user"],
                    form.cleaned_data["sentence_count"],
                )
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
            return redirect("admin-job-assignments", job_id=job.job_id)
    else:
        form = JobAssignmentForm()

    assignment_rows = []
    assigned_user_ids = (
        Sentence.objects.filter(job=job, assigned_to__isnull=False)
        .values_list("assigned_to_id", flat=True)
        .distinct()
    )

    for user in User.objects.filter(id__in=assigned_user_ids).order_by("username"):
        user_sentences = Sentence.objects.filter(job=job, assigned_to=user)
        assigned_count = user_sentences.count()
        done_count = user_sentences.filter(status="done").count()
        edited_count = user_sentences.filter(status="edited").count()
        pending_count = assigned_count - done_count - edited_count
        progress_percent = round((done_count / assigned_count) * 100) if assigned_count else 0

        assignment_rows.append({
            "user": user,
            "assigned_count": assigned_count,
            "done_count": done_count,
            "edited_count": edited_count,
            "pending_count": pending_count,
            "progress_percent": progress_percent,
        })

    total_sentences = job.sentences.count()
    assigned_sentences = job.sentences.filter(assigned_to__isnull=False).count()
    unassigned_sentences = total_sentences - assigned_sentences

    return render(request, "admin_job_assignments.html", {
        "job": job,
        "form": form,
        "assignment_rows": assignment_rows,
        "total_sentences": total_sentences,
        "assigned_sentences": assigned_sentences,
        "unassigned_sentences": unassigned_sentences,
    })


@login_required(login_url="login")
def admin_settings(request: HttpRequest) -> HttpResponse:
    if not request.user.is_superuser:
        return redirect("user-dashboard")

    return render(request, "admin_settings.html")

@login_required
def user_jobs(request):
    jobs = Job.objects.filter(sentences__assigned_to=request.user).distinct()
    return render(request, "user/jobs.html", {"jobs": jobs})


@login_required
def user_assigned_jobs(request):
    jobs = Job.objects.filter(sentences__assigned_to=request.user).distinct()

    job_rows = []
    for job in jobs:
        assigned_sentences = job.sentences.filter(assigned_to=request.user)
        assigned_count = assigned_sentences.count()
        done_count = assigned_sentences.filter(status="done").count()
        job_rows.append({
            "job": job,
            "assigned_count": assigned_count,
            "done_count": done_count,
            "pending_count": assigned_count - done_count,
            "progress_percent": round((done_count / assigned_count) * 100) if assigned_count else 0,
        })

    return render(request, "user/assigned_jobs.html", {"job_rows": job_rows})


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
    job = get_object_or_404(Job, job_id=job_id)
    sentence_queryset = Sentence.objects.filter(
        job=job,
        assigned_to=request.user,
    ).order_by("sentence_number", "sentence_id")
    if not sentence_queryset.exists():
        raise Http404("No sentences from this job are assigned to you.")

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
            job.sentences.exists()
            and job.sentences.filter(status="done").count() == job.sentences.count()
        )
        job.edit_made = all_done
        job.final_date = timezone.now() if all_done else None
        job.save(update_fields=["edit_made", "final_date"])

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
