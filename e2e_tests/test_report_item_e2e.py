import pytest
from playwright.async_api import Page, expect
import os
import tempfile
from PIL import Image

BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000')


def create_test_image(filename='test.png'):
    img = Image.new('RGB', (100, 100), color='red')
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, filename)
    img.save(filepath)
    return filepath


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_report_item_without_login(page: Page):
    await page.goto(f'{BASE_URL}/items/create/')
    
    await page.wait_for_url(f'{BASE_URL}/accounts/login/', timeout=5000)
    assert 'login' in page.url


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_report_item_with_login(page: Page):
    from django.contrib.auth.models import User
    user = User.objects.create_user(username='testuser', password='testpass123')
    
    await page.goto(f'{BASE_URL}/accounts/login/')
    await page.fill('input[name="username"]', 'testuser')
    await page.fill('input[name="password"]', 'testpass123')
    await page.click('button[type="submit"]')
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    
    await page.click('a:has-text("+ Report Item")')
    await page.wait_for_url(f'{BASE_URL}/items/create/', timeout=5000)
    
    assert 'Report Found Item' in (await page.content())


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_report_item_form_validation(page: Page):
    from django.contrib.auth.models import User
    user = User.objects.create_user(username='testuser', password='testpass123')
    
    await page.goto(f'{BASE_URL}/accounts/login/')
    await page.fill('input[name="username"]', 'testuser')
    await page.fill('input[name="password"]', 'testpass123')
    await page.click('button[type="submit"]')
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    
    await page.click('a:has-text("+ Report Item")')
    await page.wait_for_url(f'{BASE_URL}/items/create/', timeout=5000)
    
    await page.fill('input[name="title"]', 'ab')
    await page.fill('input[name="location"]', 'ab')
    
    test_image = create_test_image('validation_test.png')
    await page.locator('input[name="image"]').set_input_files(test_image)
    
    await page.wait_for_timeout(2000)
    
    await page.click('button[type="submit"]')
    await page.wait_for_timeout(1000)
    
    content = await page.content()
    assert 'at least 3 characters' in content.lower()
    
    os.remove(test_image)


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_report_item_missing_image(page: Page):
    from django.contrib.auth.models import User
    user = User.objects.create_user(username='testuser', password='testpass123')
    
    await page.goto(f'{BASE_URL}/accounts/login/')
    await page.fill('input[name="username"]', 'testuser')
    await page.fill('input[name="password"]', 'testpass123')
    await page.click('button[type="submit"]')
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    
    await page.click('a:has-text("+ Report Item")')
    await page.wait_for_url(f'{BASE_URL}/items/create/', timeout=5000)
    
    await page.fill('input[name="title"]', 'Test Item')
    await page.fill('input[name="location"]', 'Test Location')
    await page.fill('textarea[name="description"]', 'Test description')
    
    await page.click('button[type="submit"]')
    await page.wait_for_timeout(1000)
    
    content = await page.content()
    assert 'image' in content.lower()


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_report_item_invalid_image(page: Page):
    from django.contrib.auth.models import User
    user = User.objects.create_user(username='testuser', password='testpass123')
    
    await page.goto(f'{BASE_URL}/accounts/login/')
    await page.fill('input[name="username"]', 'testuser')
    await page.fill('input[name="password"]', 'testpass123')
    await page.click('button[type="submit"]')
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    
    await page.click('a:has-text("+ Report Item")')
    await page.wait_for_url(f'{BASE_URL}/items/create/', timeout=5000)
    
    temp_dir = tempfile.gettempdir()
    invalid_file = os.path.join(temp_dir, 'invalid.txt')
    with open(invalid_file, 'w') as f:
        f.write('not an image')
    
    await page.locator('input[name="image"]').set_input_files(invalid_file)
    await page.wait_for_timeout(1000)
    
    os.remove(invalid_file)
    
    assert 'valid image' in (await page.content()).lower() or 'error' in (await page.content()).lower()
