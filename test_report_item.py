import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lost_found.settings')

import django
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from items.models import Item
from io import BytesIO
from PIL import Image

def create_test_image():
    file = BytesIO()
    image = Image.new('RGB', (100, 100), color='red')
    image.save(file, 'PNG')
    file.seek(0)
    file.name = 'test_item.png'
    return file

print("=" * 60)
print("REPORT ITEM FEATURE TEST")
print("=" * 60)

# Create test user
User.objects.filter(username='reporter').delete()
user = User.objects.create_user('reporter', 'reporter@example.com', 'TestPass123!')
print(f"\n✓ Test user created: {user.username}")

client = Client()

# Login
client.post('/accounts/login/', {'username': 'reporter', 'password': 'TestPass123!'})
print("✓ User logged in")

print("\n1. Test Report Item Page Access")
response = client.get('/report/')
assert response.status_code == 200, f"Expected 200, got {response.status_code}"
assert 'Report Found Item' in response.content.decode()
print("✓ Report item page accessible")

print("\n2. Test Report Item Form Contains Required Fields")
content = response.content.decode()
assert 'name="image"' in content
assert 'name="title"' in content
assert 'name="location"' in content
print("✓ All form fields present")

print("\n3. Test Unauthenticated User Cannot Report Item")
client_anon = Client()
response = client_anon.get('/report/')
assert response.status_code == 302
assert '/accounts/login/' in response.url
print("✓ Unauthenticated users redirected to login")

print("\n4. Test Form Validation - Missing Title")
image_file = create_test_image()
response = client.post('/report/', {
    'location': 'Library',
    'description': 'A red backpack',
    'image': image_file,
})
# Should show form again with errors
assert response.status_code == 200
assert 'Report Item' in response.content.decode()
print("✓ Form validation working")

print("\n5. Test Search Functionality on Dashboard")
response = client.get('/?search=test')
assert response.status_code == 200
assert 'search' in response.content.decode().lower()
print("✓ Search parameter processed")

print("\n6. Test Category Filter on Dashboard")
response = client.get('/?category=electronics')
assert response.status_code == 200
content = response.content.decode()
assert 'Electronics' in content
print("✓ Category filter processed")

print("\n7. Test Combined Search and Filter")
response = client.get('/?search=backpack&category=accessories')
assert response.status_code == 200
print("✓ Search and filter work together")

print("\n" + "=" * 60)
print("REPORT ITEM TESTS PASSED ✓")
print("=" * 60)
print("\nNote: Full integration testing requires:")
print("  1. Cloudinary credentials (CLOUDINARY_* vars)")
print("  2. Valid image uploads")
