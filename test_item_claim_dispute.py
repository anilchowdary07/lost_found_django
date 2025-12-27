import pytest
from django.contrib.auth.models import User
from items.models import Item, Claim, DisputeResolution
from django.utils import timezone

@pytest.mark.django_db
def test_item_add_claim_and_dispute_resolution():
    # Create users
    reporter = User.objects.create_user(username='reporter', password='pass123')
    claimer = User.objects.create_user(username='claimer', password='pass123')
    admin = User.objects.create_user(username='admin', password='adminpass', is_staff=True)

    # Add item
    item = Item.objects.create(
        user=reporter,
        title='Test Wallet',
        category='accessories',
        description='A black leather wallet',
        location='Cafeteria',
        status='found',
        item_type='found',
        created_at=timezone.now()
    )
    assert Item.objects.filter(title='Test Wallet').exists()

    # Claim item
    claim = Claim.objects.create(
        item=item,
        claimer=claimer,
        message='This is my wallet',
        status='pending',
        claimed_at=timezone.now()
    )
    assert Claim.objects.filter(item=item, claimer=claimer).exists()

    # Simulate dispute
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
