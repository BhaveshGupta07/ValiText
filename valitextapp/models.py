from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    employeeid = models.CharField(max_length=32, unique=True, blank=True, null=True)
    fullname = models.CharField(max_length=255, blank=True)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.fullname or self.user.username


class Job(models.Model):
    job_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(max_length=255)
    src_lang = models.CharField(max_length=50)
    tgt_lang = models.CharField(max_length=50)
    # Legacy corpus fields, optional
    src_corpus = models.TextField(blank=True)
    tgt_corpus = models.TextField(blank=True)
    edit_made = models.BooleanField(default=False)
    validated_by_username = models.CharField(max_length=100, blank=True, null=True)
    validated_translation = models.TextField(blank=True, null=True)
    validated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='validated_jobs')
    final_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.src_lang} -> {self.tgt_lang})"


class Sentence(models.Model):
    sentence_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='sentences')
    src_sentence = models.TextField()
    tgt_sentence = models.TextField()
    edit_made = models.BooleanField(default=False)
    validated_translation = models.TextField(blank=True, null=True)
    validated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='validated_sentences')
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'),
        ('edited', 'Edited'),
        ('done', 'Done'),
    ])
    final_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['sentence_id']

    def __str__(self):
        return f"Sentence {self.sentence_id.hex[:8]} ({self.src_sentence[:50]}...)"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(
            user=instance,
            fullname=instance.get_full_name(),
            approved=instance.is_active,
        )


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    profile, _ = UserProfile.objects.get_or_create(user=instance)
    if not profile.fullname:
        profile.fullname = instance.get_full_name()
    profile.save()
