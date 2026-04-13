from django import forms
from django.contrib.auth.models import User

from .models import UserProfile, Job


class AdminUserForm(forms.ModelForm):
    employeeid = forms.CharField(
        max_length=32,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "Enter employee ID",
            }
        ),
        help_text="Unique employee identifier for this user.",
    )
    fullname = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "Enter full name",
            }
        ),
        label="Full Name",
    )
    password1 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
                "placeholder": "Enter password",
            }
        ),
        label="Password",
    )
    password2 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
                "placeholder": "Confirm password",
            }
        ),
        label="Confirm Password",
    )
    approved = forms.BooleanField(
        required=False,
        label="Approve user",
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    active = forms.BooleanField(
        required=False,
        label="Active user",
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )

    class Meta:
        model = User
        fields = ["username", "email", "is_active"]
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Enter username"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-input", "placeholder": "Enter email"}
            ),
        }
        labels = {
            "username": "Username",
            "email": "Email",
            "is_active": "Active",
        }

    def __init__(self, *args, edit_mode=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.edit_mode = edit_mode
        approved_initial = False
        active_initial = True
        if self.instance and self.instance.pk:
            profile, _ = UserProfile.objects.get_or_create(user=self.instance)
            self.fields["employeeid"].initial = profile.employeeid
            self.fields["fullname"].initial = profile.fullname or self.instance.get_full_name()
            approved_initial = profile.approved
            active_initial = self.instance.is_active
        self.fields["approved"].initial = approved_initial
        self.fields["active"].initial = active_initial
        self.fields["is_active"].widget = forms.HiddenInput()
        self.fields["is_active"].required = False

    def clean(self):
        cleaned_data = super().clean()
        employeeid = cleaned_data.get("employeeid", "").strip()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if employeeid:
            qs = UserProfile.objects.filter(employeeid=employeeid)
            if self.instance and self.instance.pk:
                qs = qs.exclude(user=self.instance)
            if qs.exists():
                self.add_error("employeeid", "Employee ID already exists.")

        if self.edit_mode:
            if password1 or password2:
                if password1 != password2:
                    self.add_error("password2", "Passwords do not match.")
        else:
            if not password1:
                self.add_error("password1", "Password is required.")
            if not password2:
                self.add_error("password2", "Please confirm the password.")
            if password1 and password2 and password1 != password2:
                self.add_error("password2", "Passwords do not match.")

        cleaned_data["is_active"] = cleaned_data.get("active", False)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        fullname = self.cleaned_data.get("fullname", "").strip()
        name_parts = fullname.split(maxsplit=1)
        user.first_name = name_parts[0] if name_parts else ""
        user.last_name = name_parts[1] if len(name_parts) > 1 else ""
        user.is_active = self.cleaned_data.get("active", False)
        password = self.cleaned_data.get("password1")
        if password:
            user.set_password(password)
        if commit:
            user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.employeeid = self.cleaned_data.get("employeeid", "").strip() or None
            profile.fullname = fullname
            profile.approved = self.cleaned_data.get("approved", False)
            profile.save()
        return user


class JobCreateForm(forms.ModelForm):
    src_file = forms.FileField(
        label="Source Corpus (TXT)",
        help_text="One sentence per line, UTF-8 encoded"
    )
    tgt_file = forms.FileField(
        label="Target Corpus (TXT)",
        help_text="One sentence per line, UTF-8 encoded, same number as source"
    )

    class Meta:
        model = Job
        fields = ['name', 'src_lang', 'tgt_lang']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': 'Enter job name'
            }),
            'src_lang': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': 'e.g. English'
            }),
            'tgt_lang': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': 'e.g. Hindi'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        src_file = cleaned_data.get('src_file')
        tgt_file = cleaned_data.get('tgt_file')
        if src_file and tgt_file:
            try:
                src_content = src_file.read().decode('utf-8')
                tgt_content = tgt_file.read().decode('utf-8')
                src_lines = src_content.splitlines()
                tgt_lines = tgt_content.splitlines()
                src_lines = [line.strip() for line in src_lines if line.strip()]
                tgt_lines = [line.strip() for line in tgt_lines if line.strip()]
                if len(src_lines) != len(tgt_lines):
                    raise forms.ValidationError(
                        f'Sentence count mismatch: Source has {len(src_lines)}, Target has {len(tgt_lines)}. They must match.'
                    )
                cleaned_data['src_lines'] = src_lines
                cleaned_data['tgt_lines'] = tgt_lines
                cleaned_data['sentence_count'] = len(src_lines)
            except UnicodeDecodeError:
                raise forms.ValidationError('Files must be valid UTF-8 TXT files.')
            except Exception as e:
                raise forms.ValidationError(f'Error processing files: {str(e)}')
        elif not src_file or not tgt_file:
            raise forms.ValidationError('Both source and target files are required.')
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Don't save corpus to Job, sentences created in view
        src_lines = self.cleaned_data['src_lines']
        tgt_lines = self.cleaned_data['tgt_lines']
        if commit:
            instance.save()
            from .models import Sentence
            sentences = []
            for src, tgt in zip(src_lines, tgt_lines):
                sentences.append(Sentence(
                    job=instance,
                    src_sentence=src,
                    tgt_sentence=tgt
                ))
            Sentence.objects.bulk_create(sentences)
            self.instance.sentence_count = len(sentences)  # for message
        self.save_m2m()
        return instance
