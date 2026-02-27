import requests
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import check_password
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash

from authenticationapp.models import User
from authenticationapp.forms import Registrationform, PasswordResetRequestForm
from authenticationapp.utils import send_activation_email_threaded, send_password_reset_email_threaded

# Is default_token_generator Secure?
# Yes, it is secure because:
# Cryptographically signed (uses Django SECRET_KEY)
# Time-sensitive (token expires automatically)
# User-state dependent (invalidates after activation/password change)
# Cannot be guessed (hash-based)
# It internally hashes:
# User PK
# Password hash
# Last login
# Timestamp
# SECRET_KEY
# So if any of these change → token becomes invalid automatically.

import pyotp
import qrcode
import base64
import io

def verify_2fa_otp(user,otp):
    totp=pyotp.TOTP(user.mfa_secret)
    if totp.verify(otp):
        user.mfa_enabled=True
        user.save()
        return True
    return False

@login_required
def mfa_view(request):
    user = request.user
    if not user.mfa_secret:
        user.mfa_secret=pyotp.random_base32()
        user.save()

    otp_url=pyotp.totp.TOTP(user.mfa_secret).provisioning_uri(
        name=user.email,
        issuer_name="abcd"
    )
    qr = qrcode.make(otp_url)
    buffer=io.BytesIO()
    qr.save(buffer,format='PNG')
    buffer.seek(0)
    qr_code=base64.b64encode(buffer.getvalue()).decode("utf-8")
    qr_code_data_uri=f'data:image/png;base64,{qr_code}'
    return render(request, "account/MFA.html", {'qrcode':qr_code_data_uri})

def verify_mfa(request):
    if request.method=='POST':

        otp=request.POST.get('otp_code')
        user_id=request.POST.get('user_id')

        if not user_id:
            messages.error(request, 'invalid user id, plese try again')
            return render(request, 'account/otp_verify.html', {'user_id':user_id})
        
        user=User.objects.get(id=user_id)

        if verify_2fa_otp(user,otp):
            if request.user.is_authenticated:
                messages.success(request,'2fa enable successfully')
                return redirect('mfa')
            login(request,user)
            messages.success(request,'login success')
            return redirect('home')
        
        else:
            if request.user.is_authenticated:
                messages.error(request,'invalid otp code')
                return redirect('mfa')
            messages.error(request,'invalid otp code')
            return render(request,'account/otp_verify.html',{'user_id':user_id})

    return render(request,'account/otp_verify.html',{'user_id':user_id})

@login_required
def disable_mfa(request):
    user = request.user
    if user.mfa_enabled:
        user.mfa_enabled = False
        user.save()
        messages.success(request, "Two-Factor Authentication has been disabled.")
        return redirect('mfa')
    else:
        messages.info(request, "2FA is already disabled.")
    return redirect('mfa')

# ------------------------------cloudflare captcha---------------------------------------------

def verify_turnstile(token, remote_ip):
    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

    data = {
        "secret": settings.TURNSTILE_SECRET_KEY,
        "response": token,
        "remoteip": remote_ip,
    }

    try:
        r = requests.post(url, data=data, timeout=5)
        result = r.json()
        return result.get("success", False)
    except Exception:
        return False  # Fail secure

# --------------------------------login------------------------------------------------------------

@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        # --------------------------------------------------------------------------
        captcha_token = request.POST.get("cf-turnstile-response")
        if not captcha_token:
            messages.error(request, "Captcha verification failed.")
            return render(request, "account/login.html", {"TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY})
        if not verify_turnstile(captcha_token, request.META.get("REMOTE_ADDR")):
            messages.error(request, "Bot verification failed. Try again.")
            return render(request, "account/login.html", {"TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY})
        # -------------------------------------------------------------------------------

        if not email or not password:
            messages.error(request, "Both fields are required.")
            return render(request, "account/login.html", {"TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY})

        # Step 1: Try Django authenticate (secure backend)
        user = authenticate(request, email=email, password=password)

        # CASE 1: Active user + correct password
        if user is not None:
            if user.mfa_enabled:
                return render(request,'account/otp_verify.html', {'user_id': user.id})
            login(request, user)
            # 🔐 Session Hardening (VERY IMPORTANT)
            request.session.cycle_key()      # Prevent session fixation
            # request.session.set_expiry(3600) # 1 hour session timeout (optional)
            messages.success(request, "Login successful.")
            return redirect("home")

        # Step 2: If authenticate returned None,
        # check manually for inactive user with correct password
        user_obj = User.objects.filter(email=email).first()

        # Generic error (prevents email enumeration)
        if not user_obj or not check_password(password, user_obj.password):
            messages.error(request, "Invalid email or password.")
            return render(request, "account/login.html", {"TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY})

        # CASE 2: Correct password but inactive account
        if not user_obj.is_active:
            # resend_activation_email(user_obj)  # optional
            uidb64=urlsafe_base64_encode(force_bytes(user_obj.pk))
            token=default_token_generator.make_token(user_obj)
            activation_link=reverse('activate',kwargs={'uidb64':uidb64,'token':token})
            activation_url=f'{settings.SITE_DOMAIN}{activation_link}'
            send_activation_email_threaded(user_obj.email,activation_url)
            messages.warning(
                request,
                "Your account is not activated. A new activation link has been sent to your email."
            )
            return render(request, "account/login.html", {"TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY})

        # Fallback (rare edge case)
        messages.error(request, "Login failed. Please try again.")
        return render(request, "account/login.html", {"TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY})

    return render(request, "account/login.html",{"TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY})

# --------------------------------logout-------------------------------------------------

@login_required
@require_http_methods(["POST"])
def logout_view(request):
    """
    Secure logout:
    - POST only (prevents CSRF via GET links)
    - Requires authenticated user
    - Clears session safely
    """
    logout(request)  # Django securely flushes session
    # Extra protection against session fixation (already handled by logout)
    request.session.flush()
    messages.success(request, "You have been logged out successfully.")
    return redirect("login")

# ---------------------------------register-----------------------------------

@require_http_methods(["GET"])  # Blocks POST/PUT/DELETE/PATCH attacks
def activate_account(request, uidb64, token):
    try:
        # Decode user id
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)

        # If already activated
        if user.is_active:
            messages.info(request, "Account already activated. Please login.")
            return redirect("login")

        # Validate token
        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            messages.success(request, "Account has been activated successfully.")
            return redirect("login")
        else:
            messages.error(request, "Invalid or expired activation link.")
            return redirect("login")

    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        messages.error(request, "Invalid activation link.")
        return redirect("login")

@require_http_methods(["GET", "POST"])  # Blocks PUT/DELETE/PATCH attacks
def register_view(request):
    # Block logged-in users from re-registering
    if request.user.is_authenticated:
        messages.info(request, "You are already logged in.")
        return redirect("home")

    if request.method == "POST":
        form = Registrationform(request.POST)

        # -----------------------------------------------------------------------------------
        captcha_token = request.POST.get("cf-turnstile-response")
        if not captcha_token:
            messages.error(request, "Captcha verification failed.")
            return render(request, "account/register.html", {"form": form, "TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY})
        if not verify_turnstile(captcha_token, request.META.get("REMOTE_ADDR")):
            messages.error(request, "Bot verification failed. Try again.")
            return render(request, "account/register.html", {"form": form, "TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY})
        # -------------------------------------------------------------------------------------

        if form.is_valid():
            user = form.save(commit=False)

            # CRITICAL SECURITY: Never trust frontend data
            user.is_superuser = False
            user.is_staff = False
            user.is_active = False  # Email verification required

            # Secure password hashing
            user.set_password(form.cleaned_data["password"])
            user.save()

            uidb64=urlsafe_base64_encode(force_bytes(user.pk))
            token=default_token_generator.make_token(user)
            activation_link=reverse('activate',kwargs={'uidb64':uidb64,'token':token})
            activation_url=f'{settings.SITE_DOMAIN}{activation_link}'
            send_activation_email_threaded(user.email,activation_url)

            messages.success(request,"Account created successfully. Please verify your email before login.")
            return redirect("login")

        # If invalid → show errors safely
        return render(request, "account/register.html", {"form": form, "TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY})

    # GET request
    form = Registrationform()
    return render(request, "account/register.html", {"form": form, "TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY})

# --------------------------------password reset-----------------------------------------------------

@require_http_methods(["GET", "POST"])
def password_reset_view(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email=email)

            # Optional: send a reset email (example, you can customize)
            uidb64=urlsafe_base64_encode(force_bytes(user.pk))
            token=default_token_generator.make_token(user)
            reset_link=reverse('password-reset-confirm',kwargs={'uidb64':uidb64,'token':token})
            reset_url=f'{settings.SITE_DOMAIN}{reset_link}'
            send_password_reset_email_threaded(user.email,reset_url)

            messages.success(request, "Password reset instructions have been sent to your email.")
            return redirect('login')  # Redirect after success
        else:
            # Form is invalid, errors are automatically attached
            return render(request, 'account/password_reset.html', {'form': form})
    else:
        form = PasswordResetRequestForm()
    return render(request, 'account/password_reset.html', {'form': form})

@require_http_methods(["GET", "POST"])  # Allow GET to show form, POST to submit
def password_reset_confirm_view(request, uidb64, token):
    try:
        # Decode user id
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)

    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        messages.error(request, "Invalid password reset link.")
        return redirect("login")

    # Check if the token is valid
    if not default_token_generator.check_token(user, token):
        messages.error(request, "Invalid or expired password reset link.")
        return redirect("login")

    # POST: process new password
    if request.method == "POST":
        form = SetPasswordForm(user=user, data=request.POST)
        if form.is_valid():
            form.save()  # Save new password
            messages.success(request, "Your password has been reset successfully. You can now login.")
            return redirect("login")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # GET: show empty form
        form = SetPasswordForm(user=user)

    return render(request, "account/password_reset_confirm.html", {"form": form})

# ---------------------------------change password----------------------------------------------------

@login_required
@require_http_methods(["GET", "POST"])
def change_password_view(request):

    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('change-password')
    else:
        form = PasswordChangeForm(user=request.user)

    # 🔥 Add Bootstrap styling to all fields
    for field in form.fields.values():
        field.widget.attrs.update({
            'class': 'form-control form-control-lg rounded-3 shadow-sm'
        })

    return render(request, 'account/change_password.html', {'form': form})













@login_required
@require_http_methods(["GET"])
def account_setting(request):
    return render(request, "account/account_setting.html")


