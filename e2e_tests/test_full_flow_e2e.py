import pytest
from playwright.async_api import Page
import os
import tempfile
from PIL import Image

BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000')


def create_test_image(filename='test.png', color='red'):
    img = Image.new('RGB', (200, 200), color=color)
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, filename)
    img.save(filepath)
    return filepath


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_full_user_flow_signup_to_notification(page: Page):
    test_image = create_test_image('full_flow_test.png', 'blue')
    
    await page.goto(f'{BASE_URL}/')
    assert 'Campus Lost & Found' in (await page.content())
    
    await page.click('a:has-text("Sign Up")')
    await page.wait_for_url(f'{BASE_URL}/accounts/signup/', timeout=5000)
    
    await page.fill('input[name="username"]', 'testuser')
    await page.fill('input[name="email"]', 'test@example.com')
    await page.fill('input[name="password1"]', 'securepass123')
    await page.fill('input[name="password2"]', 'securepass123')
    await page.click('button[type="submit"]')
    
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    assert 'testuser' in (await page.content())
    
    await page.click('a:has-text("+ Report Item")')
    await page.wait_for_url(f'{BASE_URL}/items/create/', timeout=5000)
    
    await page.locator('input[name="image"]').set_input_files(test_image)
    await page.wait_for_timeout(3000)
    
    await page.fill('input[name="title"]', 'Found Backpack')
    await page.fill('input[name="location"]', 'Library Main Entrance')
    await page.fill('textarea[name="description"]', 'Blue backpack found at library entrance, appears to be a school backpack')
    
    await page.click('button[type="submit"]')
    await page.wait_for_timeout(3000)
    
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    
    content = await page.content()
    assert 'Found Backpack' in content or 'success' in content.lower()
    
    await page.click('a:has-text("Logout")')
    await page.wait_for_timeout(1000)
    
    await page.click('a:has-text("Login")')
    await page.wait_for_url(f'{BASE_URL}/accounts/login/', timeout=5000)
    
    await page.fill('input[name="username"]', 'testuser')
    await page.fill('input[name="password"]', 'securepass123')
    await page.click('button[type="submit"]')
    
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    
    os.remove(test_image)


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_full_claim_workflow(page: Page):
    from items.models import Item
    from django.contrib.auth.models import User
    
    user1 = User.objects.create_user(
        username='finder',
        password='pass123',
        email='finder@example.com',
        first_name='John',
        last_name='Finder'
    )
    user2 = User.objects.create_user(
        username='owner',
        password='pass123',
        email='owner@example.com',
        first_name='Jane',
        last_name='Owner'
    )
    
    item = Item.objects.create(
        user=user1,
        title='Lost Smartphone',
        category='electronics',
        description='iPhone 12 with blue case',
        image_url='https://via.placeholder.com/200',
        location='Coffee Shop',
        ai_tags=['smartphone', 'iPhone', 'electronics'],
        status='found'
    )
    
    await page.goto(f'{BASE_URL}/accounts/login/')
    await page.fill('input[name="username"]', 'owner')
    await page.fill('input[name="password"]', 'pass123')
    await page.click('button[type="submit"]')
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    
    assert 'owner' in (await page.content()).lower()
    
    await page.click('button:has-text("Claim Item")')
    await page.wait_for_selector('.modal-body', timeout=5000)
    
    await page.fill('textarea[name="message"]', 'This is my iPhone! I lost it last week. The SIM is mine.')
    
    submit_btn = page.locator('button[type="submit"]:has-text("Submit Claim")')
    await submit_btn.click()
    
    await page.wait_for_timeout(3000)
    
    await page.click('a:has-text("Logout")')
    await page.wait_for_timeout(1000)
    
    await page.click('a:has-text("Login")')
    await page.wait_for_url(f'{BASE_URL}/accounts/login/', timeout=5000)
    
    await page.fill('input[name="username"]', 'finder')
    await page.fill('input[name="password"]', 'pass123')
    await page.click('button[type="submit"]')
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    
    await page.click('a:has-text("🔔 Notifications")')
    await page.wait_for_url(f'{BASE_URL}/notifications/', timeout=5000)
    
    content = await page.content()
    assert 'Lost Smartphone' in content
    assert 'owner' in content.lower()


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_validation_and_error_handling(page: Page):
    from django.contrib.auth.models import User
    
    user = User.objects.create_user(username='testuser', password='pass123')
    
    await page.goto(f'{BASE_URL}/accounts/login/')
    await page.fill('input[name="username"]', 'testuser')
    await page.fill('input[name="password"]', 'pass123')
    await page.click('button[type="submit"]')
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    
    await page.click('a:has-text("+ Report Item")')
    await page.wait_for_url(f'{BASE_URL}/items/create/', timeout=5000)
    
    await page.fill('input[name="title"]', 'a')
    await page.fill('input[name="location"]', 'b')
    
    temp_dir = tempfile.gettempdir()
    invalid_file = os.path.join(temp_dir, 'invalid.txt')
    with open(invalid_file, 'w') as f:
        f.write('not an image')
    
    try:
        await page.locator('input[name="image"]').set_input_files(invalid_file)
    except:
        pass
    
    await page.click('button[type="submit"]')
    await page.wait_for_timeout(1000)
    
    content = await page.content()
    assert 'error' in content.lower() or '3 characters' in content.lower() or 'valid' in content.lower()
    
    os.remove(invalid_file)
