from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import cloudinary.uploader
import tempfile
import os
from .forms import SignUpForm, LoginForm, EditProfileForm, EmailLoginForm


def signup(request):
    if request.user.is_authenticated:
        return redirect('items:dashboard')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.is_active = False  # Mark inactive until email verified
                user.save()
                # Create verification token
                from .models import EmailVerificationToken
                token_obj, _ = EmailVerificationToken.objects.get_or_create(user=user)
                # Send verification email
                from django.core.mail import send_mail
                from django.conf import settings
                verify_url = request.build_absolute_uri(f"/accounts/verify-email/{token_obj.token}/")
                subject = "Verify your email for Campus Lost & Found"
                message = f"Hello {user.username},\n\nPlease verify your email by clicking the link below:\n{verify_url}\n\nIf you did not sign up, ignore this email."
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
                return render(request, 'accounts/verify_notice.html', {'email': user.email})
            except Exception as e:
                messages.error(request, f'An error occurred during signup: {str(e)}', extra_tags='error')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}', extra_tags='error')
    else:
        form = SignUpForm()

    return render(request, 'accounts/signup.html', {'form': form})

# Email verification view
from django.http import HttpResponse
def verify_email(request, token):
    from .models import EmailVerificationToken
    from django.contrib.auth.models import User
    try:
        token_obj = EmailVerificationToken.objects.get(token=token, is_used=False)
        user = token_obj.user
        user.is_active = True
        user.save()
        token_obj.is_used = True
        token_obj.save()
        return HttpResponse("<h2>Email verified! You can now <a href='/accounts/login/'>login</a>.</h2>")
    except EmailVerificationToken.DoesNotExist:
        return HttpResponse("<h2>Invalid or expired verification link.</h2>")


def login_view(request):
    if request.user.is_authenticated:
        return redirect('items:dashboard')

    if request.method == 'POST':
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()
            password = form.cleaned_data['password']
            try:
                from django.contrib.auth.models import User
                user = User.objects.filter(email=email).first()
                if user is not None:
                    user_auth = authenticate(request, username=user.username, password=password)
                    if user_auth is not None:
                        login(request, user_auth)
                        messages.success(request, f'Welcome back, {user_auth.username}!', extra_tags='success')
                        return redirect('items:dashboard')
                messages.error(request, 'Invalid email or password.', extra_tags='error')
            except Exception as e:
                messages.error(request, f'An error occurred during login: {str(e)}', extra_tags='error')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}', extra_tags='error')
    else:
        form = EmailLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    try:
        logout(request)
        messages.success(request, 'You have been logged out.', extra_tags='success')
    except Exception as e:
        messages.error(request, f'An error occurred during logout: {str(e)}', extra_tags='error')
    return redirect('items:dashboard')


@login_required(login_url='accounts:login')
def profile(request):
    from items.models import Item, Claim
    from items.karma_utils import get_user_karma, get_user_rank
    from django.db.models import Q

    # Get user statistics
    user_items = Item.objects.filter(user=request.user)
    reported_items = user_items.count()
    claimed_items = Claim.objects.filter(claimer=request.user).count()

    # Get recent activity
    recent_items = user_items.order_by('-created_at')[:5]
    recent_claims = Claim.objects.filter(claimer=request.user).order_by('-claimed_at')[:5]

    # Get karma info
    karma_points = get_user_karma(request.user)
    user_rank = get_user_rank(request.user)
    points_to_next_level = max(0, 1000 - karma_points)
    progress_percentage = min(100, (karma_points / 10)) if karma_points > 0 else 0
    progress_percentage = min(100, (karma_points / 1000) * 100) if karma_points > 0 else 0

    context = {
        'reported_items': reported_items,
        'claimed_items': claimed_items,
        'karma_points': karma_points,
        'user_rank': user_rank,
        'recent_items': recent_items,
        'recent_claims': recent_claims,
        'points_to_next_level': points_to_next_level,
        'progress_percentage': progress_percentage,
    }

    return render(request, 'accounts/profile.html', context)


@login_required(login_url='accounts:login')
def edit_profile(request):
    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            from .models import UserProfile
            
            profile_photo = request.FILES.get('profile_photo')
            
            try:
                profile = request.user.profile
            except UserProfile.DoesNotExist:
                profile = UserProfile.objects.create(user=request.user)
            
            request.user.profile = profile
            
            photo_uploaded = False
            if profile_photo:
                temp_path = None
                try:
                    from django.conf import settings
                    from pathlib import Path
                    import shutil
                    import uuid
                    
                    temp_dir = tempfile.gettempdir()
                    temp_path = os.path.join(temp_dir, profile_photo.name)
                    
                    with open(temp_path, 'wb') as f:
                        for chunk in profile_photo.chunks():
                            f.write(chunk)
                    
                    photo_url = None
                    
                    try:
                        cloudinary_config = cloudinary.config()
                        if cloudinary_config.cloud_name and cloudinary_config.cloud_name != 'your_cloud_name':
                            cloudinary_result = cloudinary.uploader.upload(temp_path)
                            photo_url = cloudinary_result.get('secure_url')
                    except Exception as cloud_err:
                        pass
                    
                    if not photo_url:
                        media_dir = Path(settings.MEDIA_ROOT) / 'profile_photos'
                        media_dir.mkdir(parents=True, exist_ok=True)
                        file_extension = Path(temp_path).suffix
                        unique_filename = f"{uuid.uuid4()}{file_extension}"
                        local_path = media_dir / unique_filename
                        
                        shutil.copy2(temp_path, local_path)
                        photo_url = f"{settings.MEDIA_URL}profile_photos/{unique_filename}"
                    
                    profile.profile_photo = photo_url
                    profile.save()
                    photo_uploaded = True
                    messages.success(request, 'Profile photo updated successfully!', extra_tags='success')
                
                except Exception as e:
                    messages.warning(request, f'Profile photo upload failed: {str(e)}', extra_tags='warning')
                
                finally:
                    if temp_path and os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except:
                            pass
            
            form.save(request.user)
            if not photo_uploaded and not profile_photo:
                messages.success(request, 'Profile updated successfully!', extra_tags='success')
            return redirect('accounts:profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}', extra_tags='error')
    else:
        form = EditProfileForm(user=request.user)

    return render(request, 'accounts/edit_profile.html', {'form': form})
