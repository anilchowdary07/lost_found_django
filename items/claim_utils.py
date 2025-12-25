from .models import Item, Claim, Notification, ItemTimeline
from django.core.mail import send_mail
from django.conf import settings


def create_claim(item_id, claimer_user, message=''):
    try:
        item = Item.objects.get(id=item_id)
        
        if item.status == 'claimed':
            return {'error': 'Item already claimed'}
        
        if item.user == claimer_user:
            return {'error': 'You cannot claim your own item'}
        
        # Check if claim already exists for this item
        if hasattr(item, 'claim') and item.claim:
            return {'error': 'This item has already been claimed by someone else'}
        
        # Use get_or_create to handle race conditions
        try:
            claim, created = Claim.objects.get_or_create(
                item=item,
                defaults={
                    'claimer': claimer_user,
                    'message': message
                }
            )
            
            if not created:
                return {'error': 'This item has already been claimed by someone else'}
        except Exception as e:
            # Handle any database constraint errors
            if 'UNIQUE constraint failed' in str(e) or 'duplicate' in str(e).lower():
                return {'error': 'This item has already been claimed by someone else'}
            else:
                return {'error': f'Failed to create claim: {str(e)}'}
        
        notification_message = (
            f"{claimer_user.username} has claimed your item: \"{item.title}\". "
            f"Click 'Reveal Contact' to see their email and arrange a handoff."
        )
        
        notification = Notification.objects.create(
            recipient=item.user,
            claim=claim,
            message=notification_message
        )
        
        # Don't change item status yet - wait for owner acceptance
        # item.status = 'claimed'
        # item.save()
        
        ItemTimeline.objects.create(
            item=item,
            status='reported',  # Keep as reported until accepted
            changed_by=claimer_user,
            notes=f'New claim submitted by {claimer_user.username}'
        )
        
        # Send email notification
        try:
            subject = f'Your item has been claimed - {item.title}'
            body = f"""
Hello {item.user.username},

Your reported item "{item.title}" has been claimed by {claimer_user.username}.

Claim message: {message if message else 'No message provided'}

Please log in to your account to reveal the claimer's contact information and arrange the handoff.

Best regards,
Campus Lost & Found Team
            """
            send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [item.user.email],
                fail_silently=True
            )
        except Exception as e:
            # Email sending failed, but don't fail the claim
            pass
        
        return {
            'success': True,
            'claim_id': claim.id,
            'notification_id': notification.id
        }
    
    except Item.DoesNotExist:
        return {'error': 'Item not found'}
    except Exception as e:
        return {'error': f'Failed to create claim: {str(e)}'}


def reveal_contact(notification_id, viewer_user):
    try:
        notification = Notification.objects.get(id=notification_id)
        
        if notification.recipient != viewer_user:
            return {'error': 'Not authorized to view this contact'}
        
        claim = notification.claim
        claim.contact_revealed = True
        claim.save()
        
        return {
            'success': True,
            'claimer_email': claim.claimer.email,
            'claimer_username': claim.claimer.username,
            'claimer_name': f"{claim.claimer.first_name} {claim.claimer.last_name}".strip() or claim.claimer.username
        }
    
    except Notification.DoesNotExist:
        return {'error': 'Notification not found'}
    except Exception as e:
        return {'error': f'Failed to reveal contact: {str(e)}'}


def mark_notification_read(notification_id, viewer_user):
    try:
        notification = Notification.objects.get(id=notification_id)
        
        if notification.recipient != viewer_user:
            return {'error': 'Not authorized'}
        
        notification.is_read = True
        notification.save()
        
        return {'success': True}
    
    except Notification.DoesNotExist:
        return {'error': 'Notification not found'}
    except Exception as e:
        return {'error': f'Failed to mark as read: {str(e)}'}
