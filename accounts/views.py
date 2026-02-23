
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.db.models import Q

# Import Profile model
from .models import Profile

# Login view with email verification check
def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        # Find user by email
        user_obj = User.objects.filter(email__iexact=email).first()

        if not user_obj:
            messages.error(request, 'Invalid email or password.')
            return redirect('login')

        user = authenticate(request, username=user_obj.username, password=password)

        if user:
            # Optional: block unverified accounts
            try:
                if hasattr(user, 'profile') and not user.profile.email_verified:
                    messages.error(request, 'Please verify your email address before logging in.')
                    return redirect('login')
            except Profile.DoesNotExist:
                Profile.objects.create(user=user, email_verified=False)
                messages.error(request, 'Please verify your email address before logging in.')
                return redirect('login')

            login(request, user)
            next_url = request.GET.get('next', '/dashboard')
            return redirect(next_url)

        messages.error(request, 'Invalid email or password.')

    return render(request, 'accounts/login.html')


# Signup view with email verification
# Signup view with email verification
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm_password', '')

        # Validation
        errors = []
        if password != confirm:
            errors.append('Passwords do not match.')
        if User.objects.filter(username=username).exists():
            errors.append('Username already taken.')
        if User.objects.filter(email=email).exists():
            errors.append('Email already registered.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if not username:
            errors.append('Username is required.')
        if not email:
            errors.append('Email is required.')

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            try:
                # Create the user but set is_active to False until email verification
                user = User.objects.create_user(
                    username=username, 
                    email=email, 
                    password=password,
                    is_active=False  # User cannot log in until email verified
                )
                
                # Profile will be created automatically by signal
                # But we need to ensure email_verified is False
                profile = user.profile
                profile.email_verified = False
                profile.save()
                
                # Send verification email
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                # Build verification link
                verification_link = request.build_absolute_uri(
                    f'/accounts/verify-email/{uid}/{token}/'
                )
                
                # Send HTML email
                subject = "Verify Your Email - ClauseGuard"
                
                html_message = render_to_string('accounts/verification_email.html', {
                    'user': user,
                    'verification_link': verification_link,
                    'site_name': 'ClauseGuard',
                })
                text_message = strip_tags(html_message)

                email_msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_message,  # plain text fallback
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email],
                )
                email_msg.attach_alternative(html_message, "text/html")
                
                try:
                    email_msg.send(fail_silently=False)
                    messages.success(request, f'Account created! Please check your email to verify your account.')
                    return redirect('verification_sent')
                except Exception as e:
                    # If email fails, delete the user to prevent orphaned accounts
                    user.delete()
                    messages.error(request, 'There was an error sending the verification email. Please try again.')
                    print(f"Email error: {str(e)}")
                    
            except Exception as e:
                messages.error(request, f'An error occurred during account creation. Please try again.')
                print(f"Signup error: {str(e)}")
                
    return render(request, 'accounts/signup.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('/accounts/login/')


# Email verification view
def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        # Activate the user
        user.is_active = True
        user.save()
        
        # Update profile verification status
        profile, created = Profile.objects.get_or_create(user=user)
        profile.email_verified = True
        profile.save()
        
        messages.success(request, 'Your email has been verified! You can now log in.')
        return redirect('verification_success')
    else:
        messages.error(request, 'The verification link is invalid or has expired.')
        return render(request, 'accounts/verification_invalid.html')


def verification_sent(request):
    if request.user.is_authenticated:
        return redirect('index')
    return render(request, 'accounts/verification_sent.html')


def verification_success(request):
    if request.user.is_authenticated:
        return redirect('index')
    return render(request, 'accounts/verification_success.html')


# Resend verification email functionality
def resend_verification_email(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        try:
            user = User.objects.get(email=email, is_active=False)
            
            # Check if profile exists and email not verified
            profile, created = Profile.objects.get_or_create(user=user)
            
            if not profile.email_verified:
                # Generate new token
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                # Build verification link
                verification_link = request.build_absolute_uri(
                    f'/accounts/verify-email/{uid}/{token}/'
                )
                
                # Send email
                subject = "Verify Your Email - ClauseGuard"

                html_message = render_to_string('accounts/verification_email.html', {
                    'user': user,
                    'verification_link': verification_link,
                    'site_name': 'ClauseGuard',
                })
                text_message = strip_tags(html_message)

                email_msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email],
                )
                email_msg.attach_alternative(html_message, "text/html")
                email_msg.send(fail_silently=False)

                messages.success(request, 'Verification email has been resent. Please check your inbox.')
                return redirect('verification_sent')
            else:
                messages.error(request, 'This email is already verified.')
                return redirect('login')
        except Exception as e:
            messages.error(request, 'There was an error sending the email. Please try again.')
            print(f"Email error: {str(e)}")
        except User.DoesNotExist:
            # Don't reveal if user exists or not
            pass
        
        messages.success(request, 'If an unverified account exists with that email, a new verification link will be sent.')
        return redirect('verification_sent')
    
    return render(request, 'accounts/resend_verification.html')


def password_reset_request(request):
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if email:
            try:
                user = User.objects.get(email=email)
                
                # Generate reset token
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                # Build reset link
                reset_link = request.build_absolute_uri(
                    f'/accounts/password-reset/{uid}/{token}/'
                )
                
                subject = "Reset Your Password - ClauseGuard"

                html_message = render_to_string('accounts/password_reset_email.html', {
                    'user': user,
                    'reset_link': reset_link,
                    'site_name': 'ClauseGuard',
                })
                text_message = strip_tags(html_message)

                email_msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_message,  # plain text fallback
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email],
                )
                email_msg.attach_alternative(html_message, "text/html")
                email_msg.send(fail_silently=False)

                messages.success(request, 'Password reset instructions have been sent to your email.')
                return redirect('password_reset_done')

            except Exception as e:
                messages.error(request, 'There was an error sending the email. Please try again.')
                print(f"Email error: {str(e)}")
    
    return render(request, 'accounts/password_reset_request.html')


def password_reset_confirm(request, uidb64, token):
    if request.user.is_authenticated:
        return redirect('index')
    
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            password = request.POST.get('password', '')
            confirm_password = request.POST.get('confirm_password', '')
            
            errors = []
            if password != confirm_password:
                errors.append('Passwords do not match.')
            if len(password) < 8:
                errors.append('Password must be at least 8 characters.')
            
            if errors:
                for error in errors:
                    messages.error(request, error)
            else:
                user.set_password(password)
                user.save()
                messages.success(request, 'Your password has been reset successfully. You can now login.')
                return redirect('password_reset_complete')
        
        return render(request, 'accounts/password_reset_confirm.html', {'validlink': True, 'email': user.email})
    else:
        messages.error(request, 'The password reset link is invalid or has expired.')
        return render(request, 'accounts/password_reset_confirm.html', {'validlink': False})


def password_reset_done(request):
    if request.user.is_authenticated:
        return redirect('index')
    return render(request, 'accounts/password_reset_done.html')


def password_reset_complete(request):
    if request.user.is_authenticated:
        return redirect('index')
    return render(request, 'accounts/password_reset_complete.html')