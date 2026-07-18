from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User


class BootstrapFormMixin:
    """
    Automatically adds Bootstrap classes to form fields and
    applies the 'is-invalid' class to fields with validation errors.
    """

    default_class = "form-control"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            widget = field.widget

            classes = widget.attrs.get("class", "").split()

            if self.default_class not in classes:
                classes.append(self.default_class)

            if self.is_bound and name in self.errors:
                classes.append("is-invalid")

            widget.attrs["class"] = " ".join(classes)


class LoginForm(BootstrapFormMixin, forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Enter your email",
                "autocomplete": "email",
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter your password",
                "autocomplete": "current-password",
            }
        ),
    )


class BaseUserRegistrationForm(BootstrapFormMixin, forms.ModelForm):
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Create a password",
                "autocomplete": "new-password",
            }
        ),
    )

    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirm your password",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = User

        fields = (
            "email",
            "first_name",
            "last_name",
            "phone",
        )

        widgets = {
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "Email address",
                    "autocomplete": "email",
                }
            ),
            "first_name": forms.TextInput(
                attrs={
                    "placeholder": "First name",
                    "autocomplete": "given-name",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "placeholder": "Last name",
                    "autocomplete": "family-name",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "placeholder": "Phone number",
                    "autocomplete": "tel",
                }
            ),
        }

    def clean_password(self):
        password = self.cleaned_data.get("password")

        try:
            validate_password(password)
        except ValidationError as exc:
            raise forms.ValidationError(exc.messages)

        return password

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error(
                "confirm_password",
                "Passwords do not match.",
            )

        return cleaned_data

    def _create_user(self, role, commit=True):
        user = User(
            email=self.cleaned_data.get("email"),
            first_name=self.cleaned_data.get("first_name"),
            last_name=self.cleaned_data.get("last_name"),
            phone=self.cleaned_data.get("phone"),
            role=role,
        )

        user.set_password(self.cleaned_data.get("password"))

        if commit:
            user.save()

        return user

    def save(self, commit=True):
        """
        Subclasses must implement save() to create
        the appropriate profile model.
        """
        raise NotImplementedError(
            "Subclasses of BaseUserRegistrationForm must implement save()."
        )
