from django import forms
from authenticationapp.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

class Registrationform(forms.ModelForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your email'
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your password'
        })
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Confirm your password'
        })
    )

    class Meta:
        model = User
        fields = ['email', 'password', 'confirm_password']

    # Email validation
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already registered.")
        return email

    # Strong password validation (uses Django validators)
    def clean_password(self):
        password = self.cleaned_data.get('password')
        try:
            validate_password(password)
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
        return password

    # Password match validation
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Password and Confirm Password do not match')

        return cleaned_data

class PasswordResetRequestForm(forms.Form):
    email=forms.EmailField(
        max_length=255,
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder':'example@gmail.com'
            })
    )

    def clean(self):
        email=self.cleaned_data.get('email')

        # check if a user with this email exists
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                ('No account is associated with this email address')
            )
        return self.cleaned_data
