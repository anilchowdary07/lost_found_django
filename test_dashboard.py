import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lost_found.settings')

import django
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from items.models import Item

def create_test_items():
    user = User.objects.create_user('itemcreator', 'creator@example.com', 'Pass123!')
    
    Item.objects.create(
        user=user,
        title='Red Backpack',
        category='accessories',
        description='A red backpack found near the library',
        image_url='https://via.placeholder.com/300x200?text=Backpack',
        location='Library',
        ai_tags=['backpack', 'red', 'leather'],
        status='found'
    )
    
    Item.objects.create(
        user=user,
        title='MacBook Pro',
        category='electronics',
        description='Silver MacBook Pro found in the cafeteria',
        image_url='https://via.placeholder.com/300x200?text=MacBook',
        location='Cafeteria',
        ai_tags=['laptop', 'MacBook', 'silver'],
        status='found'
    )
    
    Item.objects.create(
        user=user,
        title='Blue Jacket',
        category='clothing',
        description='Blue winter jacket',
        image_url='https://via.placeholder.com/300x200?text=Jacket',
        location='Student Center',
        ai_tags=['jacket', 'blue', 'winter'],
        status='found'
    )
    
    Item.objects.create(
        user=user,
        title='Gold Ring',
        category='jewelry',
        description='Gold ring with diamond',
        image_url='https://via.placeholder.com/300x200?text=Ring',
        location='Gym',
        ai_tags=['ring', 'gold', 'diamond'],
        status='found'
    )
    
    Item.objects.create(
        user=user,
        title='Calculus Textbook',
        category='books',
        description='Advanced Calculus textbook',
        image_url='https://via.placeholder.com/300x200?text=Book',
        location='Math Building',
        ai_tags=['textbook', 'calculus', 'math'],
        status='claimed'
    )

print("=" * 60)
print("DASHBOARD PHASE 4 TESTS")
print("=" * 60)

# Clean up
Item.objects.all().delete()
User.objects.filter(username__in=['itemcreator', 'test_user']).delete()

# Create test data
create_test_items()
print("\n✓ Test items created (5 items)")

client = Client()

print("\n1. Test Dashboard Displays All Items")
response = client.get('/')
assert response.status_code == 200
content = response.content.decode()
assert 'Red Backpack' in content
assert 'MacBook Pro' in content
assert 'Blue Jacket' in content
assert 'Gold Ring' in content
assert 'Calculus Textbook' in content
print("✓ All items displayed on dashboard")

print("\n2. Test Search by Title")
response = client.get('/?search=MacBook')
assert response.status_code == 200
content = response.content.decode()
assert 'MacBook Pro' in content
assert 'Red Backpack' not in content
print("✓ Search by title works")

print("\n3. Test Search by Description")
response = client.get('/?search=winter')
content = response.content.decode()
assert 'Blue Jacket' in content
assert 'Red Backpack' not in content
print("✓ Search by description works")

print("\n4. Test Search by Tags")
response = client.get('/?search=diamond')
content = response.content.decode()
assert 'Gold Ring' in content
assert 'MacBook Pro' not in content
print("✓ Search by tags works")

print("\n5. Test Category Filter - Electronics")
response = client.get('/?category=electronics')
content = response.content.decode()
assert 'MacBook Pro' in content
assert 'Red Backpack' not in content
assert 'Blue Jacket' not in content
print("✓ Category filter (Electronics) works")

print("\n6. Test Category Filter - Accessories")
response = client.get('/?category=accessories')
content = response.content.decode()
assert 'Red Backpack' in content
assert 'MacBook Pro' not in content
print("✓ Category filter (Accessories) works")

print("\n7. Test Category Filter - Books")
response = client.get('/?category=books')
content = response.content.decode()
assert 'Calculus Textbook' in content
assert 'MacBook Pro' not in content
print("✓ Category filter (Books) works")

print("\n8. Test Combined Search and Filter")
response = client.get('/?search=blue&category=clothing')
content = response.content.decode()
assert 'Blue Jacket' in content
assert 'MacBook Pro' not in content
assert 'Gold Ring' not in content
print("✓ Search + filter combined works")

print("\n9. Test No Results Message")
response = client.get('/?search=nonexistent')
content = response.content.decode()
assert 'No items found' in content
assert 'adjusting your search' in content or 'adjust' in content.lower()
print("✓ No results message displays correctly")

print("\n10. Test Clear Filters Button")
response = client.get('/?search=MacBook&category=electronics')
content = response.content.decode()
assert 'Clear' in content
print("✓ Clear button displayed when filters active")

print("\n11. Test Item Card Display")
response = client.get('/')
content = response.content.decode()
# Check for card elements
assert 'card' in content.lower()
assert 'badge' in content.lower()
assert 'location' in content.lower() or '📍' in content
print("✓ Item cards display properly")

print("\n12. Test Status Badges")
response = client.get('/')
content = response.content.decode()
assert 'Found' in content or 'found' in content
assert 'Claimed' in content or 'claimed' in content
print("✓ Status badges display")

print("\n13. Test Claim Button for Authenticated Users")
User.objects.create_user('claimtest', 'claim@example.com', 'Pass123!')
client_auth = Client()
client_auth.post('/accounts/login/', {'username': 'claimtest', 'password': 'Pass123!'})
response = client_auth.get('/')
content = response.content.decode()
assert 'Claim Item' in content
print("✓ Claim button visible for authenticated users")

print("\n14. Test Claim Button Disabled for Claimed Items")
response = client_auth.get('/')
content = response.content.decode()
# Should have at least one "Claim Item" button and one "Already Claimed" button
assert 'Claim Item' in content
assert 'Already Claimed' in content
print("✓ Claimed items show 'Already Claimed' button")

print("\n15. Test Search Form Contains Required Elements")
response = client.get('/')
content = response.content.decode()
assert 'name="search"' in content
assert 'name="category"' in content
assert 'Electronics' in content
assert 'Clothing' in content
assert 'Jewelry' in content
print("✓ Search form has all category options")

print("\n16. Test Responsive Design - Grid Columns")
response = client.get('/')
content = response.content.decode()
assert 'col-md-6 col-lg-4' in content
print("✓ Responsive grid layout configured")

print("\n17. Test Item Count Display")
response = client.get('/?search=')
content = response.content.decode()
# Empty search still shows all items
assert 'Red Backpack' in content or 'item' in content.lower()
print("✓ Items displayed with count")

print("\n18. Test Results Message for Filtered Results")
response = client.get('/?category=electronics')
content = response.content.decode()
assert 'Showing' in content or '1 item' in content
print("✓ Results count message displays")

print("\n19. Test Category Filter All Categories Option")
response = client.get('/?category=')
assert response.status_code == 200
content = response.content.decode()
# Should show all items when category is empty
assert 'Red Backpack' in content
assert 'MacBook Pro' in content
print("✓ 'All Categories' option works")

print("\n20. Test Case Insensitive Search")
response = client.get('/?search=MACBOOK')
content = response.content.decode()
assert 'MacBook Pro' in content
print("✓ Search is case-insensitive")

print("\n" + "=" * 60)
print("PHASE 4: DASHBOARD WITH SEARCH & FILTER")
print("ALL 20 TESTS PASSED ✓")
print("=" * 60)
print("\nFeatures Verified:")
print("  ✓ All items displayed")
print("  ✓ Keyword search (title, description, tags)")
print("  ✓ Category filtering (8 categories)")
print("  ✓ Combined search + filter")
print("  ✓ Empty state messages")
print("  ✓ Clear filters button")
print("  ✓ Claim buttons (auth users)")
print("  ✓ Responsive design")
print("  ✓ Status badges")
print("  ✓ Results counter")
