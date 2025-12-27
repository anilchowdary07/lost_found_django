import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lost_found.settings')

import django
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from items.models import Item, Claim, Notification

print("=" * 60)
print("CLAIMS & NOTIFICATIONS PHASE 5 TESTS")
print("=" * 60)

# Clean up
User.objects.filter(username__in=['owner', 'claimer', 'other']).delete()
Item.objects.all().delete()
Claim.objects.all().delete()
Notification.objects.all().delete()

# Create test users
owner = User.objects.create_user('owner', 'owner@example.com', 'Pass123!')
claimer = User.objects.create_user('claimer', 'claimer@example.com', 'Pass123!')
other_user = User.objects.create_user('other', 'other@example.com', 'Pass123!')

# Create test item
item = Item.objects.create(
    user=owner,
    title='Lost Keys',
    category='keys',
    description='Silver keys with blue keychain',
    image_url='https://via.placeholder.com/300',
    location='Library',
    ai_tags=['keys', 'silver', 'lost'],
    status='reported'
)

print(f"\n✓ Test data created (owner: {owner.username}, claimer: {claimer.username})")

client = Client()

print("\n1. Test Claim Item View Requires Authentication")
response = client.post('/api/claim/', {'item_id': item.id})
assert response.status_code == 302
assert '/accounts/login/' in response.url
print("✓ Unauthenticated users redirected to login")

print("\n2. Test Claim Item - Owner Cannot Claim Own Item")
client_owner = Client()
client_owner.post('/accounts/login/', {'username': 'owner', 'password': 'Pass123!'})
response = client_owner.post('/api/claim/', {'item_id': item.id})
data = response.json()
assert 'error' in data
assert 'own item' in data['error'].lower()
print("✓ Owner cannot claim their own item")

print("\n3. Test Successful Claim Creation")
client_claimer = Client()
client_claimer.post('/accounts/login/', {'username': 'claimer', 'password': 'Pass123!'})
response = client_claimer.post('/api/claim/', {
    'item_id': item.id,
    'message': 'I found these keys! Blue keychain with initials JD'
})
assert response.status_code == 200
data = response.json()
assert data['success'] == True
print("✓ Claim created successfully")

print("\n4. Test Item Status Remains Reported After Claim")
item.refresh_from_db()
assert item.status == 'reported', f"Expected status 'reported', got '{item.status}'"
print("✓ Item status remains 'reported' after claim (pending owner action)")

print("\n5. Test Notification Created for Owner")
notifications = Notification.objects.filter(recipient=owner)
assert notifications.count() == 1
notification = notifications.first()
assert 'Lost Keys' in notification.message
print("✓ Notification created for item owner")

print("\n6. Test Claim Record Created")
claim = Claim.objects.get(item=item)
assert claim.claimer == claimer
assert 'Blue keychain' in claim.message
assert claim.contact_revealed == False
print("✓ Claim record created with correct data")

print("\n7. Test Cannot Claim Already Claimed Item")
response = client_claimer.post('/api/claim/', {'item_id': item.id})
data = response.json()
assert 'error' in data
err = data['error'].lower()
assert (
    'already claimed' in err or 'already been claimed' in err
), f"Unexpected error message: {data['error']}"
print("✓ Cannot claim already claimed items")

print("\n8. Test Notifications Page Access Requires Auth")
response = client.get('/notifications/')
assert response.status_code == 302
assert '/accounts/login/' in response.url
print("✓ Notifications page requires authentication")

print("\n9. Test Notifications Page Displays Claim")
response = client_owner.get('/notifications/')
assert response.status_code == 200
content = response.content.decode()
assert 'Lost Keys' in content
assert 'claimer' in content.lower()
assert 'New' in content
print("✓ Notifications page shows claim details")

print("\n10. Test Unread Count Displayed")
response = client_owner.get('/notifications/')
content = response.content.decode()
assert 'unread' in content.lower()
print("✓ Unread count displayed on notifications page")

print("\n11. Test Reveal Contact Requires Authentication")
response = client.post(f'/api/notifications/{notification.id}/reveal-contact/')
assert response.status_code == 302
print("✓ Reveal contact requires authentication")

print("\n12. Test Reveal Contact - Wrong User Cannot Access")
response = client_claimer.post(f'/api/notifications/{notification.id}/reveal-contact/')
data = response.json()
assert response.status_code == 400
assert 'error' in data
print("✓ Only notification recipient can reveal contact")

print("\n13. Test Reveal Contact - Owner Can Access")
response = client_owner.post(f'/api/notifications/{notification.id}/reveal-contact/')
assert response.status_code == 200
data = response.json()
assert data['claimer_email'] == claimer.email
assert data['claimer_username'] == claimer.username
print("✓ Notification owner can reveal contact")

print("\n14. Test Contact Revealed Flag Updated")
claim.refresh_from_db()
assert claim.contact_revealed == True
print("✓ Contact revealed flag set to True")

print("\n15. Test Mark Notification as Read")
response = client_owner.post(f'/api/notifications/{notification.id}/mark-read/')
assert response.status_code == 200
notification.refresh_from_db()
assert notification.is_read == True
print("✓ Notification marked as read")

print("\n16. Test Mark Read - Wrong User Cannot Access")
response = client_claimer.post(f'/api/notifications/{notification.id}/mark-read/')
data = response.json()
assert response.status_code == 400
print("✓ Only recipient can mark as read")

print("\n17. Test Claim Modal in Dashboard")
response = client_claimer.get('/')
content = response.content.decode()
assert 'claimModal' in content
assert 'Claim Item' in content
print("✓ Claim modal present in dashboard")

print("\n18. Test Claim Button Data Attributes")
# Create an unclaimed item for this test
item3 = Item.objects.create(
    user=owner,
    title='Test Item',
    category='other',
    description='Test',
    image_url='https://via.placeholder.com/300',
    location='Test',
    ai_tags=['test'],
    status='found'
)
response = client_claimer.get('/')
content = response.content.decode()
assert 'data-item-id' in content
assert 'data-item-title' in content
print("✓ Claim button has required data attributes")

print("\n19. Test Notifications Link in Navbar")
response = client_owner.get('/')
content = response.content.decode()
assert 'Notifications' in content
assert '/notifications/' in content
print("✓ Notifications link visible in authenticated navbar")

print("\n20. Test Multiple Claims (Only One Per Item)")
item2 = Item.objects.create(
    user=owner,
    title='Lost Wallet',
    category='accessories',
    description='Brown leather wallet',
    image_url='https://via.placeholder.com/300',
    location='Classroom',
    ai_tags=['wallet', 'leather'],
    status='found'
)
client_other = Client()
client_other.post('/accounts/login/', {'username': 'other', 'password': 'Pass123!'})
response = client_other.post('/api/claim/', {'item_id': item2.id})
assert response.status_code == 200
item2.refresh_from_db()
assert item2.status == 'claimed'
print("✓ New item can be claimed independently")

print("\n" + "=" * 60)
print("PHASE 5: CLAIM & NOTIFICATION SYSTEM")
print("ALL 20 TESTS PASSED ✓")
print("=" * 60)
print("\nFeatures Verified:")
print("  ✓ Claim creation with validation")
print("  ✓ Item status update on claim")
print("  ✓ Automatic notification creation")
print("  ✓ Notification retrieval")
print("  ✓ Contact reveal functionality")
print("  ✓ Mark as read functionality")
print("  ✓ Authorization checks")
print("  ✓ Claim modal in dashboard")
print("  ✓ Notifications navbar link")
print("  ✓ Multiple claims handling")
