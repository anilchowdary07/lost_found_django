import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lost_found.settings')

import django
django.setup()

from django.test import Client
from django.contrib.auth.models import User

client = Client()

print("=" * 60)
print("AUTH FLOW TEST")
print("=" * 60)

print("\n1. Test Signup Page Access")
response = client.get('/accounts/signup/')
assert response.status_code == 200, f"Expected 200, got {response.status_code}"
print("✓ Signup page accessible (GET)")

print("\n2. Test Signup Form Submission")
signup_data = {
    'username': 'testuser',
    'email': 'test@example.com',
    'first_name': 'Test',
    'last_name': 'User',
    'password1': 'TestPass123!',
    'password2': 'TestPass123!',
}
response = client.post('/accounts/signup/', data=signup_data)
assert response.status_code == 302, f"Expected redirect (302), got {response.status_code}"
print("✓ User registered successfully")

print("\n3. Verify User in Database")
user = User.objects.get(username='testuser')
assert user.email == 'test@example.com'
print(f"✓ User created: {user.username} ({user.email})")

print("\n4. Test Authenticated User Redirect from Login Page")
response = client.get('/accounts/login/')
assert response.status_code == 302, f"Expected redirect (302), got {response.status_code}"
assert '/items/' in response.url
print("✓ Authenticated user redirected from login page")

print("\n5. Test Unauthenticated User Can Access Login Page")
client_anon = Client()
response = client_anon.get('/accounts/login/')
assert response.status_code == 200
print("✓ Unauthenticated user can access login page")

print("\n6. Test Protected Page Access (Profile)")
response = client.get('/accounts/profile/')
assert response.status_code == 200, f"Expected 200, got {response.status_code}"
assert 'testuser' in response.content.decode()
print("✓ Profile page accessible when authenticated")

print("\n7. Test Dashboard Access When Authenticated")
response = client.get('/')
assert response.status_code == 200
content = response.content.decode()
assert 'testuser' in content or 'Logout' in content
print("✓ Dashboard shows authenticated user")

print("\n8. Test Logout")
response = client.get('/accounts/logout/', follow=True)
assert response.status_code == 200
print("✓ Logout successful")

print("\n9. Test Navbar Shows Login/Signup After Logout")
response = client.get('/')
content = response.content.decode()
assert 'Sign Up' in content
assert 'Login' in content
print("✓ Navbar shows login/signup after logout")

print("\n10. Test Unauthenticated Profile Redirect")
client_new = Client()
response = client_new.get('/accounts/profile/')
assert response.status_code == 302, f"Expected redirect (302), got {response.status_code}"
assert '/accounts/login/' in response.url
print("✓ Unauthenticated users redirected to login")

print("\n11. Test Login with Correct Credentials")
login_data = {
    'username': 'testuser',
    'password': 'TestPass123!',
}
response = client_anon.post('/accounts/login/', data=login_data)
assert response.status_code == 302
print("✓ Login successful with correct credentials")

print("\n12. Test Login with Incorrect Credentials")
client_bad = Client()
login_data = {
    'username': 'testuser',
    'password': 'WrongPassword',
}
response = client_bad.post('/accounts/login/', data=login_data)
assert response.status_code == 200
assert 'Invalid username or password' in response.content.decode()
print("✓ Invalid login credentials rejected")

print("\n" + "=" * 60)
print("ALL TESTS PASSED ✓")
print("=" * 60)
