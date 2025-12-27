import pytest
from django.contrib.auth.models import User
from items.models import Item, Claim, DisputeResolution
from django.utils import timezone
from django.urls import reverse

@pytest.mark.django_db
def test_add_multiple_items(client):
    user = User.objects.create_user(username='multiuser', password='pass123')
    client.login(username='multiuser', password='pass123')
    for i in range(3):
        item = Item.objects.create(
            user=user,
            title=f'Item {i}',
            category='books',
            description=f'Description {i}',
            location='Library',
            status='found',
            item_type='found',
            created_at=timezone.now()
        )
        assert Item.objects.filter(title=f'Item {i}').exists()

@pytest.mark.django_db
def test_claim_and_resolve_dispute(client):
    reporter = User.objects.create_user(username='reporter2', password='pass123')
    claimer = User.objects.create_user(username='claimer2', password='pass123')
    admin = User.objects.create_user(username='admin2', password='adminpass', is_staff=True)
    item = Item.objects.create(
        user=reporter,
        title='Test Book',
        category='books',
        description='A lost book',
        location='Library',
        status='found',
        item_type='found',
        created_at=timezone.now()
    )
    claim = Claim.objects.create(
        item=item,
        claimer=claimer,
        message='My book',
        status='pending',
        claimed_at=timezone.now()
    )
    dispute = DisputeResolution.objects.create(
        claim=claim,
        reporter=reporter,
        claimer=claimer,
        reason='Ownership conflict',
        status='open',
        assigned_to=admin
    )
    dispute.status = 'resolved'
    dispute.resolution = 'approved'
    dispute.resolved_at = timezone.now()
    dispute.save()
    assert DisputeResolution.objects.filter(status='resolved').count() > 0

@pytest.mark.django_db
def test_website_homepage(client):
    response = client.get(reverse('items:dashboard'))
    assert response.status_code == 200
    assert b'Campus Lost & Found' in response.content

@pytest.mark.django_db
def test_found_items_gallery_page(client):
    response = client.get(reverse('items:found_items_gallery'))
    assert response.status_code == 200
    assert b'Found Items' in response.content

@pytest.mark.django_db
def test_lost_items_gallery_page(client):
    response = client.get(reverse('items:lost_items_gallery'))
    assert response.status_code == 200
    assert b'Lost Items' in response.content
