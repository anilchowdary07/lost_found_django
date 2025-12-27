import pytest
from django.contrib.auth.models import User
from items.models import Item, Claim
from django.utils import timezone
from django.urls import reverse

@pytest.mark.django_db
def test_item_claim_workflow(client):
    # Create reporter and claimer
    reporter = User.objects.create_user(username='reporter_claim', password='pass123')
    claimer = User.objects.create_user(username='claimer_claim', password='pass123')
    # Reporter adds an item
    item = Item.objects.create(
        user=reporter,
        title='Claimable Item',
        category='books',
        description='A book to be claimed',
        location='Library',
        status='found',
        item_type='found',
        created_at=timezone.now()
    )
    # Claimer logs in and claims the item (simulate claim form POST)
    client.login(username='claimer_claim', password='pass123')
    claim_url = reverse('items:claim_item')
    response = client.post(claim_url, {
        'item_id': item.id,
        'message': 'This is my book!'
    })
    # Accept both redirect and JSON response
    assert response.status_code in (200, 302)
    # Check claim exists in DB
    assert Claim.objects.filter(item=item, claimer=claimer).exists()
    claim = Claim.objects.get(item=item, claimer=claimer)
    assert claim.message == 'This is my book!'
    assert claim.status == 'pending'
