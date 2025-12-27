import pytest
from django.contrib.auth.models import User
from items.models import Item, Claim, DisputeResolution
from django.utils import timezone
from django.urls import reverse

@pytest.mark.django_db
def test_signup_and_login(client):
    response = client.post(reverse('accounts:signup'), {
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password1': 'Testpass123!',
        'password2': 'Testpass123!'
    })
    assert response.status_code in (302, 200)
    user = User.objects.get(username='newuser')
    assert user.email == 'newuser@example.com'
    login = client.login(username='newuser', password='Testpass123!')
    assert login

@pytest.mark.django_db
def test_report_item_view(client):
    user = User.objects.create_user(username='reporter3', password='pass123')
    client.login(username='reporter3', password='pass123')
    response = client.get(reverse('items:report_item'))
    assert response.status_code == 200
    assert b'Report Item' in response.content or b'Report Found Item' in response.content

@pytest.mark.django_db
def test_dashboard_stats(client):
    user = User.objects.create_user(username='statuser', password='pass123')
    Item.objects.create(user=user, title='Stat Item', category='books', description='desc', location='loc', status='found', item_type='found')
    client.login(username='statuser', password='pass123')
    response = client.get(reverse('items:dashboard'))
    assert response.status_code == 200
    assert b'Items Reported' in response.content

@pytest.mark.django_db
def test_notifications_page(client):
    user = User.objects.create_user(username='notify', password='pass123')
    client.login(username='notify', password='pass123')
    response = client.get(reverse('items:notifications'))
    assert response.status_code == 200
    assert b'Notification' in response.content or b'Notifications' in response.content

@pytest.mark.django_db
def test_leaderboard_page(client):
    response = client.get(reverse('items:leaderboard'))
    assert response.status_code == 200
    assert b'Leaderboard' in response.content

@pytest.mark.django_db
def test_admin_heatmap_page(client):
    user = User.objects.create_superuser(username='adminheat', password='adminpass', email='admin@heat.com')
    client.login(username='adminheat', password='adminpass')
    response = client.get(reverse('items:admin_heatmap'))
    assert response.status_code == 200
    assert b'Heatmap' in response.content or b'heatmap' in response.content

@pytest.mark.django_db
def test_disputes_dashboard_page(client):
    user = User.objects.create_superuser(username='admindispute', password='adminpass', email='admin@dispute.com')
    client.login(username='admindispute', password='adminpass')
    response = client.get(reverse('items:disputes_dashboard'))
    assert response.status_code == 200
    assert b'Dispute' in response.content or b'dispute' in response.content

@pytest.mark.django_db
def test_edit_item_permission(client):
    user1 = User.objects.create_user(username='owner1', password='pass123')
    user2 = User.objects.create_user(username='owner2', password='pass123')
    item = Item.objects.create(user=user1, title='EditTest', category='books', description='desc', location='loc', status='found', item_type='found')
    client.login(username='owner2', password='pass123')
    response = client.get(reverse('items:edit_item', args=[item.id]))
    assert response.status_code == 302 or b'You can only edit your own items' in response.content
