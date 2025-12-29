import json
import os
import tempfile
from pathlib import Path
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse

@login_required(login_url='accounts:login')
@require_http_methods(["POST"])
def notify_owner(request):
    item_id = request.POST.get('item_id')
    message = request.POST.get('message', '').strip()
    if not item_id or not message:
        return JsonResponse({'error': 'Item ID and message are required.'}, status=400)
    try:
        item = Item.objects.get(id=item_id)
        if item.item_type != 'lost':
            return JsonResponse({'error': 'Notify Owner is only for lost items.'}, status=400)
        if item.user == request.user:
            return JsonResponse({'error': 'You cannot notify yourself.'}, status=400)
        # Only send email, do not create Notification (claim is required)
        from django.core.mail import send_mail
        from django.conf import settings
        subject = f"Someone found your lost item: {item.title}"
        body = f"Hello {item.user.username},\n\n{request.user.username} has notified you about your lost item '{item.title}'.\n\nMessage: {message}\n\nYou can reply to {request.user.email} to arrange pickup.\n\nCampus Lost & Found Team"
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [item.user.email], fail_silently=True)
        return JsonResponse({'success': True})
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Item not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Failed to notify owner: {str(e)}'}, status=500)
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.db.models import Count, Q, Sum
from django.contrib.auth.models import User
from django.conf import settings

if not settings.DEBUG:
    from django_ratelimit.decorators import ratelimit
else:
    def ratelimit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

import cloudinary
import cloudinary.uploader

from .models import Item, Notification, Claim, ItemTimeline, LocationHistory, QRCode, ContentModeration, DisputeResolution
from .forms import ItemForm
from .claim_utils import create_claim, reveal_contact, mark_notification_read
from .karma_utils import award_karma_points, get_leaderboard, get_user_karma, get_user_rank
from .qr_utils import generate_qr_code, validate_qr_code
from .security_utils import sanitize_title, sanitize_description, sanitize_location, sanitize_ai_tags
from .location_utils import get_nearby_items
from accounts.models import UserProfile


def dashboard(request):
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    items_list = Item.objects.all()
    
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    tags_filter = request.GET.get('tags', '')
    sort_by = request.GET.get('sort', '-created_at')
    quick_filter = request.GET.get('quick', '')
    
    if search_query:
        from django.db.models import Q
        items_list = items_list.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(ai_tags__icontains=search_query)
        )
    
    if category_filter:
        items_list = items_list.filter(category=category_filter)
    if status_filter:
        items_list = items_list.filter(status=status_filter)
    if date_from:
        items_list = items_list.filter(created_at__date__gte=date_from)
    if date_to:
        items_list = items_list.filter(created_at__date__lte=date_to)
    if tags_filter:
        tags_list = [tag.strip().lower() for tag in tags_filter.split(',') if tag.strip()]
        if tags_list:
            from django.db.models import Q
            tag_queries = Q()
            for tag in tags_list:
                tag_queries |= Q(ai_tags__icontains=tag)
            items_list = items_list.filter(tag_queries)
    
    # Sorting
    if sort_by == 'title':
        items_list = items_list.order_by('title')
    elif sort_by == 'location':
        items_list = items_list.order_by('location')
    elif sort_by == 'category':
        items_list = items_list.order_by('category')
    elif sort_by == 'oldest':
        items_list = items_list.order_by('created_at')
    else:
        items_list = items_list.order_by('-created_at')

    # Only show the 9 most recent items after all filters and ordering
    items_list = items_list[:9]

    # Quick filters
    if quick_filter == 'my_items' and request.user.is_authenticated:
        items_list = items_list.filter(user=request.user)
    elif quick_filter == 'my_claims' and request.user.is_authenticated:
        from items.models import Claim
        claimed_item_ids = Claim.objects.filter(user=request.user).values_list('item_id', flat=True)
        items_list = items_list.filter(id__in=claimed_item_ids)

    # Only show the 9 most recent items, no pagination
    items = items_list
    # Stats for hero section
    total_items = Item.objects.count()
    returned_items = Item.objects.filter(status='returned').count()
    active_users = User.objects.filter(is_active=True).count()
    context = {
        'items': items,
        'search_query': search_query,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'tags_filter': tags_filter,
        'sort_by': sort_by,
        'quick_filter': quick_filter,
        'total_items': total_items,
        'returned_items': returned_items,
        'active_users': active_users,
    }
    
    if request.user.is_authenticated:
        context['unread_notifications'] = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
    
    return render(request, 'items/dashboard.html', context)


@login_required(login_url='accounts:login')
@ratelimit(key='user', rate='30/d', method='POST')
@csrf_protect
def report_item(request):
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            image_file = request.FILES.get('image')
            if not image_file:
                messages.error(request, 'Please upload an image.', extra_tags='error')
                return render(request, 'items/report_item.html', {'form': form})

            # Create item instance early so it's always defined
            item = form.save(commit=False)
            item.item_type = form.cleaned_data['item_type']
            item.user = request.user

            temp_image_path = None
            try:
                temp_image_path = save_temp_image(image_file)

                category = form.cleaned_data.get('category') or 'other'
                manual_tags = form.cleaned_data.get('manual_tags', '')
                ai_tags = [tag.strip() for tag in manual_tags.split(',') if tag.strip()] if manual_tags else []

                # Upload image
                try:
                    cloudinary_result = cloudinary.uploader.upload(temp_image_path)
                    image_url = cloudinary_result.get('secure_url')
                    if not image_url:
                        # Cloudinary failed, save locally
                        import uuid
                        from django.conf import settings
                        from pathlib import Path

                        media_dir = Path(settings.MEDIA_ROOT) / 'items'
                        media_dir.mkdir(parents=True, exist_ok=True)
                        file_extension = Path(temp_image_path).suffix
                        unique_filename = f"{uuid.uuid4()}{file_extension}"
                        local_path = media_dir / unique_filename

                        import shutil
                        shutil.copy2(temp_image_path, local_path)
                        image_url = f"{settings.MEDIA_URL}items/{unique_filename}"

                        messages.warning(request, 'Image upload to cloud failed. Image saved locally.', extra_tags='warning')
                except Exception as e:
                    # Cloudinary failed, save locally
                    import uuid
                    from django.conf import settings
                    from pathlib import Path

                    media_dir = Path(settings.MEDIA_ROOT) / 'items'
                    media_dir.mkdir(parents=True, exist_ok=True)
                    file_extension = Path(temp_image_path).suffix
                    unique_filename = f"{uuid.uuid4()}{file_extension}"
                    local_path = media_dir / unique_filename

                    import shutil
                    shutil.copy2(temp_image_path, local_path)
                    image_url = f"{settings.MEDIA_URL}items/{unique_filename}"

                    messages.warning(request, 'Image upload to cloud failed. Image saved locally.', extra_tags='warning')

                item.image_url = image_url
                item.category = category
                item.title = sanitize_title(item.title)
                item.description = sanitize_description(item.description)
                item.location = sanitize_location(item.location)
                item.ai_tags = sanitize_ai_tags(ai_tags)
                item.save()
                
                messages.success(request, 'Item reported successfully!', extra_tags='success')
                # Redirect to correct gallery based on item_type
                if item.item_type == 'lost':
                    return redirect('items:lost_items_gallery')
                else:
                    return redirect('items:found_items_gallery')
            
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {str(e)}', extra_tags='error')
                return render(request, 'items/report_item.html', {'form': form})
            
            finally:
                if temp_image_path and os.path.exists(temp_image_path):
                    try:
                        os.remove(temp_image_path)
                    except:
                        pass
        else:
            # Log form errors for debugging
            try:
                print('Report form invalid. request.POST keys:', list(request.POST.keys()))
                print('request.FILES keys:', list(request.FILES.keys()))
                print('Form errors:', form.errors.as_json())
            except Exception as _e:
                print('Error printing form errors:', str(_e))

            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}', extra_tags='error')
    else:
        form = ItemForm()
    
    return render(request, 'items/report_item.html', {'form': form})


def save_temp_image(image_file):
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, image_file.name)
    
    with open(temp_path, 'wb') as f:
        for chunk in image_file.chunks():
            f.write(chunk)
    
    return temp_path


@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
@ratelimit(key='user', rate='10/h', method='POST')
@csrf_protect
def claim_item(request):
    try:
        item_id = request.POST.get('item_id')
        message = request.POST.get('message', '').strip()
        
        if not item_id:
            return JsonResponse({'error': 'Item ID required'}, status=400)
        
        if len(message) > 1000:
            return JsonResponse({'error': 'Message cannot exceed 1000 characters'}, status=400)
        
        message = sanitize_description(message, max_length=1000)
        
        result = create_claim(int(item_id), request.user, message)
        
        if 'error' in result:
            return JsonResponse(result, status=400)
        
        messages.success(request, f'Item claimed successfully! The owner will be notified.', extra_tags='success')
        return JsonResponse({'success': True, 'redirect': '/'})
    
    except ValueError:
        return JsonResponse({'error': 'Invalid item ID'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)


@login_required(login_url='accounts:login')
def notifications(request):
    user_notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    
    unread_count = user_notifications.filter(is_read=False).count()
    
    return render(request, 'items/notifications.html', {
        'notifications': user_notifications,
        'unread_count': unread_count,
    })


@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
@ratelimit(key='user', rate='20/h', method='POST')
@csrf_protect
def reveal_contact_view(request, notification_id):
    try:
        result = reveal_contact(notification_id, request.user)
        
        if 'error' in result:
            return JsonResponse(result, status=400)
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({'error': f'Failed to reveal contact: {str(e)}'}, status=500)


@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
@ratelimit(key='user', rate='30/h', method='POST')
@csrf_protect
def accept_claim(request, claim_id):
    try:
        claim = get_object_or_404(Claim, id=claim_id)
        
        if claim.item.user != request.user:
            return JsonResponse({'error': 'Not authorized'}, status=403)
        
        if claim.status != 'pending':
            return JsonResponse({'error': 'Claim already processed'}, status=400)
        
        claim.status = 'accepted'
        claim.accepted_at = datetime.now()
        claim.save()
        
        # Update item status to claimed
        claim.item.status = 'claimed'
        claim.item.save()
        
        # Create notification for claimer
        notification_message = (
            f"Great news! Your claim on \"{claim.item.title}\" has been accepted. "
            f"The owner has revealed their contact information. Please arrange pickup soon."
        )
        
        Notification.objects.create(
            recipient=claim.claimer,
            claim=claim,
            message=notification_message
        )
        
        # Send email to claimer
        try:
            subject = f'Your claim has been accepted - {claim.item.title}'
            body = f"""
Hello {claim.claimer.username},

Great news! Your claim on "{claim.item.title}" has been accepted by the owner.

Owner Contact Information:
Email: {claim.item.user.email}
Name: {claim.item.user.first_name} {claim.item.user.last_name or claim.item.user.username}

Please contact the owner to arrange pickup of your item.

Best regards,
Campus Lost & Found Team
            """
            send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [claim.claimer.email],
                fail_silently=True
            )
        except Exception as e:
            pass
        
        ItemTimeline.objects.create(
            item=claim.item,
            status='claimed',
            changed_by=request.user,
            notes=f'Claim accepted by owner {request.user.username}'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Claim accepted! The claimer has been notified.'
        })
    
    except Exception as e:
        return JsonResponse({'error': f'Failed to accept claim: {str(e)}'}, status=500)


@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
@ratelimit(key='user', rate='30/h', method='POST')
@csrf_protect
def reject_claim(request, claim_id):
    try:
        claim = get_object_or_404(Claim, id=claim_id)
        
        if claim.item.user != request.user:
            return JsonResponse({'error': 'Not authorized'}, status=403)
        
        if claim.status != 'pending':
            return JsonResponse({'error': 'Claim already processed'}, status=400)
        
        claim.status = 'rejected'
        claim.rejected_at = datetime.now()
        claim.save()
        
        # Reset item status to reported so others can claim
        claim.item.status = 'reported'
        claim.item.save()
        
        # Create notification for claimer
        notification_message = (
            f"We're sorry, but your claim on \"{claim.item.title}\" was not accepted by the owner. "
            f"You may try claiming other items or contact support if you believe this was an error."
        )
        
        Notification.objects.create(
            recipient=claim.claimer,
            claim=claim,
            message=notification_message
        )
        
        ItemTimeline.objects.create(
            item=claim.item,
            status='reported',
            changed_by=request.user,
            notes=f'Claim rejected by owner {request.user.username}'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Claim rejected. The item is now available for other claims.'
        })
    
    except Exception as e:
        return JsonResponse({'error': f'Failed to reject claim: {str(e)}'}, status=500)


@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
def mark_notification_read_view(request, notification_id):
    try:
        result = mark_notification_read(notification_id, request.user)
        
        if 'error' in result:
            return JsonResponse(result, status=400)
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({'error': f'Failed to update notification: {str(e)}'}, status=500)


def leaderboard(request):
    leaderboard_users = get_leaderboard(limit=20)

    context = {
        'leaderboard': leaderboard_users,
        'total_participants': UserProfile.objects.filter(karma_points__gt=0).count(),
        'total_items_returned': UserProfile.objects.aggregate(total=Sum('total_items_returned'))['total'] or 0,
        'total_karma_points': UserProfile.objects.aggregate(total=Sum('karma_points'))['total'] or 0,
    }

    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            context['user_karma'] = user_profile.karma_points
            context['user_rank'] = get_user_rank(request.user)
            context['user_items_returned'] = user_profile.total_items_returned
        except UserProfile.DoesNotExist:
            context['user_karma'] = 0
            context['user_rank'] = '-'
            context['user_items_returned'] = 0

    return render(request, 'items/leaderboard.html', context)


def item_detail(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    timeline = item.timeline.all()
    claim = None
    claims_history = []

    from items.models import Claim
    claims_history = Claim.objects.filter(item=item).order_by('-claimed_at')
    if hasattr(item, 'claim'):
        claim = item.claim

    context = {
        'item': item,
        'timeline': timeline,
        'claim': claim,
        'claims_history': claims_history,
        'can_edit': request.user.is_authenticated and request.user == item.user,
        # Only allow claim for found items
        'can_claim': request.user.is_authenticated and request.user != item.user and item.status == 'reported' and item.item_type == 'found',
        # Allow notify for lost items
        'can_notify': request.user.is_authenticated and request.user != item.user and item.status == 'reported' and item.item_type == 'lost',
    }

    return render(request, 'items/item_detail.html', context)


@login_required(login_url='accounts:login')
def generate_qr_code_view(request, claim_id):
    try:
        claim = get_object_or_404(Claim, id=claim_id)
        
        if claim.item.user != request.user:
            return JsonResponse({'error': 'Not authorized'}, status=403)
        
        qr_code, created = QRCode.objects.get_or_create(claim=claim)
        
        if created or not qr_code.qr_image_url:
            base64_img = generate_qr_code(claim)
            qr_code.qr_image_url = f'data:image/png;base64,{base64_img}'
            qr_code.save()
        
        return JsonResponse({
            'success': True,
            'qr_code': qr_code.qr_image_url,
            'qr_id': qr_code.code
        })
    
    except Exception as e:
        return JsonResponse({'error': f'Failed to generate QR code: {str(e)}'}, status=500)


@require_http_methods(['POST'])
@ratelimit(key='ip', rate='20/h', method='POST')
@csrf_protect
def verify_qr_code(request):
    try:
        data = json.loads(request.body)
        qr_code_id = data.get('qr_code')
        
        if not qr_code_id:
            return JsonResponse({'error': 'QR code required'}, status=400)
        
        qr_code = validate_qr_code(qr_code_id)
        
        if not qr_code:
            return JsonResponse({'error': 'Invalid QR code'}, status=400)
        
        if qr_code.scanned:
            return JsonResponse({'error': 'QR code already scanned'}, status=400)
        
        claim = qr_code.claim
        item = claim.item
        
        qr_code.scanned = True
        qr_code.scanned_at = datetime.now()
        qr_code.save()
        
        item.status = 'returned'
        item.save()
        
        claim.verified_at = datetime.now()
        claim.save()
        
        ItemTimeline.objects.create(
            item=item,
            status='returned',
            changed_by=claim.claimer,
            notes='Item returned - QR code scanned'
        )
        
        award_karma_points(claim.claimer)
        
        return JsonResponse({
            'success': True,
            'message': 'Item marked as returned!',
            'item_title': item.title
        })
    
    except Exception as e:
        return JsonResponse({'error': f'Failed to verify QR code: {str(e)}'}, status=500)


@require_http_methods(['POST'])
@ratelimit(key='ip', rate='30/h', method='POST')
@csrf_protect
def search_nearby_items(request):
    try:
        data = json.loads(request.body)
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        radius = data.get('radius', 5)
        
        if not latitude or not longitude:
            return JsonResponse({'error': 'Latitude and longitude required'}, status=400)
        
        try:
            latitude = float(latitude)
            longitude = float(longitude)
            radius = float(radius)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid coordinates'}, status=400)
        
        if radius < 0.1 or radius > 50:
            radius = 5
        
        nearby = get_nearby_items(latitude, longitude, radius)
        
        items_data = [{
            'id': item_obj['item'].id,
            'title': item_obj['item'].title,
            'category': item_obj['item'].category,
            'location': item_obj['item'].location,
            'distance': item_obj['distance'],
            'image_url': item_obj['item'].image_url,
            'status': item_obj['item'].status,
            'item_type': item_obj['item'].item_type,
        } for item_obj in nearby]
        
        return JsonResponse({
            'success': True,
            'count': len(items_data),
            'radius': radius,
            'items': items_data
        })
    
    except Exception as e:
        return JsonResponse({'error': f'Search failed: {str(e)}'}, status=500)


@login_required(login_url='accounts:login')
def mark_item_returned(request, item_id):
    try:
        item = get_object_or_404(Item, id=item_id)
        
        if item.user != request.user:
            return JsonResponse({'error': 'Not authorized'}, status=403)
        
        if not hasattr(item, 'claim'):
            return JsonResponse({'error': 'Item has no claim'}, status=400)
        
        claim = item.claim
        item.status = 'returned'
        item.save()
        
        claim.verified_at = datetime.now()
        claim.save()
        
        ItemTimeline.objects.create(
            item=item,
            status='returned',
            changed_by=request.user,
            notes='Item marked as returned by owner'
        )
        
        award_karma_points(claim.claimer)
        
        return JsonResponse({
            'success': True,
            'message': 'Item marked as returned and karma awarded!'
        })
    
    except Exception as e:
        return JsonResponse({'error': f'Failed to mark item as returned: {str(e)}'}, status=500)


@staff_member_required
def admin_heatmap(request):
    location_data = LocationHistory.objects.values('location_name', 'latitude', 'longitude').annotate(
        count=Count('id')
    ).order_by('-count')
    
    heatmap_data = [{
        'location': loc['location_name'],
        'lat': loc['latitude'],
        'lng': loc['longitude'],
        'count': loc['count']
    } for loc in location_data]
    
    context = {
        'heatmap_data': json.dumps(heatmap_data),
        'locations': location_data,
    }
    
    return render(request, 'items/admin_heatmap.html', context)


def found_items_gallery(request):
    total_items = Item.objects.filter(item_type='found').count()
    available_items = Item.objects.filter(item_type='found', status='reported').count()
    claimed_items = Item.objects.filter(item_type='found', status='claimed').count()
    items = Item.objects.filter(item_type='found').exclude(status='returned').order_by('-created_at')
    
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if search_query:
        items = items.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(ai_tags__icontains=search_query)
        )

    if category_filter:
        items = items.filter(category=category_filter)

    if date_from:
        items = items.filter(created_at__date__gte=date_from)
    if date_to:
        items = items.filter(created_at__date__lte=date_to)
    
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator = Paginator(items, 12)  # 12 items per page
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        'items': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'gallery_type': 'found',
        'gallery_title': 'Found Items',
        'gallery_description': 'Browse items that have been found and are waiting to be claimed',
        'search_query': search_query,
        'category_filter': category_filter,
        'date_from': date_from,
        'date_to': date_to,
        'total_items': total_items,
        'available_items': available_items,
        'claimed_items': claimed_items,
    }
    return render(request, 'items/items_gallery.html', context)


def lost_items_gallery(request):
    total_items = Item.objects.filter(item_type='lost').count()
    available_items = Item.objects.filter(item_type='lost', status='reported').count()
    claimed_items = Item.objects.filter(item_type='lost', status='claimed').count()
    items = Item.objects.filter(item_type='lost').exclude(status='returned').order_by('-created_at')
    
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if search_query:
        items = items.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(ai_tags__icontains=search_query)
        )

    if category_filter:
        items = items.filter(category=category_filter)

    if date_from:
        items = items.filter(created_at__date__gte=date_from)
    if date_to:
        items = items.filter(created_at__date__lte=date_to)
    
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator = Paginator(items, 12)  # 12 items per page
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        'items': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'gallery_type': 'lost',
        'gallery_title': 'Lost Items',
        'gallery_description': 'Browse items that have been found and are waiting to be claimed',
        'search_query': search_query,
        'category_filter': category_filter,
        'date_from': date_from,
        'date_to': date_to,
        'total_items': total_items,
        'available_items': available_items,
        'claimed_items': claimed_items,
    }
    if request.user.is_authenticated:
        context['unread_notifications'] = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
    return render(request, 'items/items_gallery.html', context)


@login_required(login_url='accounts:login')
def edit_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    
    # Only allow the item owner to edit
    if request.user != item.user:
        messages.error(request, 'You can only edit your own items.', extra_tags='error')
        return redirect('items:item_detail', item_id=item.id)
    
    # Don't allow editing if item is already returned
    if item.status == 'returned':
        messages.error(request, 'Cannot edit items that have been returned.', extra_tags='error')
        return redirect('items:item_detail', item_id=item.id)
    
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            # Handle image update if provided
            image_file = request.FILES.get('image')
            if image_file:
                temp_image_path = None
                try:
                    temp_image_path = save_temp_image(image_file)
                    
                    # Try uploading to Cloudinary first
                    try:
                        cloudinary_result = cloudinary.uploader.upload(temp_image_path)
                        image_url = cloudinary_result.get('secure_url')
                        if not image_url:
                            raise Exception("Cloudinary upload failed")
                        item.image_url = image_url
                    except Exception as e:
                        # Fallback to local storage
                        import uuid
                        from django.conf import settings
                        from pathlib import Path
                        
                        media_dir = Path(settings.MEDIA_ROOT) / 'items'
                        media_dir.mkdir(parents=True, exist_ok=True)
                        file_extension = Path(temp_image_path).suffix
                        unique_filename = f"{uuid.uuid4()}{file_extension}"
                        local_path = media_dir / unique_filename
                        
                        import shutil
                        shutil.copy2(temp_image_path, local_path)
                        item.image_url = f"{settings.MEDIA_URL}items/{unique_filename}"
                        
                        messages.warning(request, 'Image upload to cloud failed. Image saved locally.', extra_tags='warning')
                
                finally:
                    if temp_image_path and os.path.exists(temp_image_path):
                        try:
                            os.remove(temp_image_path)
                        except:
                            pass
            
            item.title = sanitize_title(form.cleaned_data.get('title'))
            item.description = sanitize_description(form.cleaned_data.get('description'))
            item.location = sanitize_location(form.cleaned_data.get('location'))
            item.category = form.cleaned_data.get('category')
            item.item_type = form.cleaned_data.get('item_type')
            
            manual_tags = form.cleaned_data.get('manual_tags')
            if manual_tags:
                manual_tags_list = [tag.strip() for tag in manual_tags.split(',') if tag.strip()]
                existing_ai_tags = item.ai_tags if item.ai_tags else []
                item.ai_tags = sanitize_ai_tags(list(set(existing_ai_tags + manual_tags_list)))
            
            item.save()
            
            # Create timeline entry
            ItemTimeline.objects.create(
                item=item,
                status=item.status,
                changed_by=request.user,
                notes=f'Item details updated by {request.user.username}'
            )
            
            messages.success(request, 'Item updated successfully!', extra_tags='success')
            return redirect('items:item_detail', item_id=item.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}', extra_tags='error')
    else:
        # Pre-populate form with existing data
        initial_data = {
            'title': item.title,
            'description': item.description,
            'location': item.location,
            'category': item.category,
            'item_type': item.item_type,
            'manual_tags': ', '.join(item.ai_tags) if item.ai_tags else ''
        }
        form = ItemForm(instance=item, initial=initial_data)
    
    return render(request, 'items/edit_item.html', {'form': form, 'item': item})


@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
@csrf_protect
def get_updates(request):
    try:
        last_update_time = request.POST.get('last_update_time', '')
        
        updates = {
            'new_claims': 0,
            'claim_updates': [],
            'new_notifications': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        user_items = Item.objects.filter(user=request.user)
        new_claims = Claim.objects.filter(
            item__in=user_items,
            status='pending'
        ).select_related('claimer', 'item')
        
        updates['new_claims'] = new_claims.count()
        
        for claim in new_claims[:5]:
            updates['claim_updates'].append({
                'id': claim.id,
                'item_title': claim.item.title,
                'claimer': claim.claimer.username,
                'claimed_at': claim.claimed_at.isoformat(),
                'status': claim.status
            })
        
        new_notifications = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        updates['new_notifications'] = new_notifications
        
        return JsonResponse(updates)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
def admin_moderation(request):
    pending_flags = ContentModeration.objects.filter(
        status='pending'
    ).select_related('item', 'claim', 'flagged_by').order_by('-created_at')
    
    approved_flags = ContentModeration.objects.filter(
        status='approved'
    ).select_related('item', 'claim').order_by('-reviewed_at')[:10]
    
    rejected_flags = ContentModeration.objects.filter(
        status='rejected'
    ).select_related('item', 'claim').order_by('-reviewed_at')[:10]
    
    stats = {
        'total_pending': pending_flags.count(),
        'total_approved': ContentModeration.objects.filter(status='approved').count(),
        'total_rejected': ContentModeration.objects.filter(status='rejected').count(),
        'total_removed': ContentModeration.objects.filter(status='removed').count(),
    }
    
    context = {
        'pending_flags': pending_flags[:20],
        'approved_flags': approved_flags,
        'rejected_flags': rejected_flags,
        'stats': stats
    }
    
    return render(request, 'items/admin_moderation.html', context)


@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
@ratelimit(key='user', rate='5/h', method='POST')
@csrf_protect
def flag_content(request):
    try:
        item_id = request.POST.get('item_id')
        claim_id = request.POST.get('claim_id')
        reason = request.POST.get('reason', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not reason or not description:
            return JsonResponse({'error': 'Reason and description required'}, status=400)
        
        if not item_id and not claim_id:
            return JsonResponse({'error': 'Item or claim ID required'}, status=400)
        
        item = None
        claim = None
        
        if item_id:
            try:
                item = Item.objects.get(id=item_id)
            except Item.DoesNotExist:
                return JsonResponse({'error': 'Item not found'}, status=404)
        
        if claim_id:
            try:
                claim = Claim.objects.get(id=claim_id)
            except Claim.DoesNotExist:
                return JsonResponse({'error': 'Claim not found'}, status=404)
        
        existing_flag = ContentModeration.objects.filter(
            item=item,
            claim=claim,
            flagged_by=request.user,
            status='pending'
        ).exists()
        
        if existing_flag:
            return JsonResponse({'error': 'You have already flagged this content'}, status=400)
        
        flag = ContentModeration.objects.create(
            item=item,
            claim=claim,
            flagged_by=request.user,
            reason=reason,
            description=description
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Content flagged for review',
            'flag_id': flag.id
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
@require_http_methods(['POST'])
@csrf_protect
def handle_moderation(request):
    try:
        flag_id = request.POST.get('flag_id')
        action = request.POST.get('action')
        notes = request.POST.get('notes', '').strip()
        
        flag = ContentModeration.objects.get(id=flag_id)
        
        if action == 'approve':
            flag.status = 'approved'
            if flag.item:
                flag.item.status = 'reported'
                flag.item.save()
        elif action == 'reject':
            flag.status = 'rejected'
        elif action == 'remove':
            flag.status = 'removed'
            if flag.item:
                flag.item.delete()
            elif flag.claim:
                flag.claim.delete()
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        flag.reviewed_by = request.user
        flag.review_notes = notes
        flag.reviewed_at = datetime.now()
        flag.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Flag {action}d successfully'
        })
    except ContentModeration.DoesNotExist:
        return JsonResponse({'error': 'Flag not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
def disputes_dashboard(request):
    open_disputes = DisputeResolution.objects.filter(
        status='open'
    ).select_related('claim', 'reporter', 'claimer').order_by('-created_at')
    
    in_progress = DisputeResolution.objects.filter(
        status='in_progress'
    ).select_related('claim', 'reporter', 'claimer').order_by('-created_at')[:10]
    
    resolved = DisputeResolution.objects.filter(
        status='resolved'
    ).select_related('claim', 'reporter', 'claimer').order_by('-resolved_at')[:10]
    
    stats = {
        'total_open': open_disputes.count(),
        'total_in_progress': DisputeResolution.objects.filter(status='in_progress').count(),
        'total_resolved': DisputeResolution.objects.filter(status='resolved').count(),
    }
    
    context = {
        'open_disputes': open_disputes[:20],
        'in_progress_disputes': in_progress,
        'resolved_disputes': resolved,
        'stats': stats
    }
    
    return render(request, 'items/disputes_dashboard.html', context)


@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
@ratelimit(key='user', rate='2/d', method='POST')
@csrf_protect
def create_dispute(request):
    try:
        claim_id = request.POST.get('claim_id')
        reason = request.POST.get('reason', '').strip()
        
        if not claim_id or not reason:
            return JsonResponse({'error': 'Claim ID and reason required'}, status=400)
        
        claim = Claim.objects.get(id=claim_id)
        
        if claim.status not in ['pending', 'accepted']:
            return JsonResponse({'error': 'Cannot create dispute for this claim'}, status=400)
        
        existing_dispute = DisputeResolution.objects.filter(
            claim=claim,
            status__in=['open', 'in_progress']
        ).exists()
        
        if existing_dispute:
            return JsonResponse({'error': 'A dispute already exists for this claim'}, status=400)
        
        dispute = DisputeResolution.objects.create(
            claim=claim,
            reporter=claim.item.user,
            claimer=claim.claimer,
            reason=reason
        )
        
        messages.success(request, 'Dispute created. Admin will review it shortly.', extra_tags='success')
        
        return JsonResponse({
            'success': True,
            'message': 'Dispute created successfully',
            'dispute_id': dispute.id
        })
    except Claim.DoesNotExist:
        return JsonResponse({'error': 'Claim not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
@require_http_methods(['POST'])
@csrf_protect
def resolve_dispute(request):
    try:
        dispute_id = request.POST.get('dispute_id')
        resolution = request.POST.get('resolution')
        admin_notes = request.POST.get('admin_notes', '').strip()
        
        dispute = DisputeResolution.objects.get(id=dispute_id)
        
        valid_resolutions = ['favor_claimer', 'favor_reporter', 'mutual_agreement', 'no_resolution']
        if resolution not in valid_resolutions:
            return JsonResponse({'error': 'Invalid resolution'}, status=400)
        
        dispute.status = 'resolved'
        dispute.resolution = resolution
        dispute.admin_notes = admin_notes
        dispute.resolved_at = datetime.now()
        dispute.save()
        
        if resolution == 'favor_claimer':
            claim = dispute.claim
            claim.status = 'accepted'
            claim.save()
            ItemTimeline.objects.create(
                item=claim.item,
                status='claimed',
                changed_by=request.user,
                notes=f'Dispute resolved in favor of claimer {claim.claimer.username}'
            )
        elif resolution == 'favor_reporter':
            claim = dispute.claim
            claim.status = 'rejected'
            claim.save()
            ItemTimeline.objects.create(
                item=claim.item,
                status='reported',
                changed_by=request.user,
                notes=f'Dispute resolved in favor of reporter'
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Dispute resolved successfully'
        })
    except DisputeResolution.DoesNotExist:
        return JsonResponse({'error': 'Dispute not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def delete_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    if item.user != request.user:
        return JsonResponse({"error": "Not authorized to delete this item."}, status=403)
    item.delete()
    messages.success(request, "Item deleted successfully.")
    # Redirect to the correct gallery
    if item.item_type == "lost":
        return JsonResponse({"success": True, "redirect": "/items/lost/"})
    else:
        return JsonResponse({"success": True, "redirect": "/items/gallery/"})
def welcome(request):
    return render(request, 'welcome.html')
