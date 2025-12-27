import pytest
from django.contrib.auth.models import User
from items.models import Item, Claim, DisputeResolution
from django.utils import timezone

@pytest.mark.django_db
def test_dispute_creation_and_resolution():
    # Create users
    reporter = User.objects.create_user(username='reporter_dispute', password='pass123')
    claimer = User.objects.create_user(username='claimer_dispute', password='pass123')
    admin = User.objects.create_user(username='admin_dispute', password='adminpass', is_staff=True)
    # Add item and claim
    item = Item.objects.create(
        user=reporter,
        title='Dispute Item',
        category='books',
        description='A book with dispute',
        location='Library',
        status='found',
        item_type='found',
        created_at=timezone.now()
    )
    claim = Claim.objects.create(
        item=item,
        claimer=claimer,
        message='I want to claim this',
        status='pending',
        claimed_at=timezone.now()
    )
    # Create dispute
    dispute = DisputeResolution.objects.create(
        claim=claim,
        reporter=reporter,
        claimer=claimer,
        reason='Ownership conflict',
        status='open',
        assigned_to=admin
    )
    assert DisputeResolution.objects.filter(claim=claim, status='open').exists()
    # Resolve dispute
    dispute.status = 'resolved'
    dispute.resolution = 'approved'
    dispute.resolved_at = timezone.now()
    dispute.save()
    resolved = DisputeResolution.objects.get(pk=dispute.pk)
    assert resolved.status == 'resolved'
    assert resolved.resolution == 'approved'
    assert resolved.resolved_at is not None
