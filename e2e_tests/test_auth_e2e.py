import pytest
from playwright.async_api import Page, expect
import os

BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000')


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_signup_flow(page: Page):
    await page.goto(f'{BASE_URL}/accounts/signup/')
    
    await page.fill('input[name="username"]', 'testuser')
    await page.fill('input[name="email"]', 'test@example.com')
    await page.fill('input[name="password1"]', 'securepassword123')
    await page.fill('input[name="password2"]', 'securepassword123')
    
    await page.click('button[type="submit"]')
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    
    assert page.url == f'{BASE_URL}/'


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_signup_duplicate_email(page: Page):
    from django.contrib.auth.models import User
    User.objects.create_user(username='existinguser', email='existing@example.com', password='pass123')
    
    await page.goto(f'{BASE_URL}/accounts/signup/')
    
    await page.fill('input[name="username"]', 'newuser')
    await page.fill('input[name="email"]', 'existing@example.com')
    await page.fill('input[name="password1"]', 'securepassword123')
    await page.fill('input[name="password2"]', 'securepassword123')
    
    await page.click('button[type="submit"]')
    await page.wait_for_timeout(1000)
    
    assert 'already registered' in (await page.content()).lower()


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_login_flow(page: Page):
    from django.contrib.auth.models import User
    User.objects.create_user(username='testuser', password='testpass123')
    
    await page.goto(f'{BASE_URL}/accounts/login/')
    
    await page.fill('input[name="username"]', 'testuser')
    await page.fill('input[name="password"]', 'testpass123')
    
    await page.click('button[type="submit"]')
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    
    assert page.url == f'{BASE_URL}/'
    assert 'testuser' in (await page.content())


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_login_invalid_credentials(page: Page):
    await page.goto(f'{BASE_URL}/accounts/login/')
    
    await page.fill('input[name="username"]', 'invaliduser')
    await page.fill('input[name="password"]', 'wrongpassword')
    
    await page.click('button[type="submit"]')
    await page.wait_for_timeout(1000)
    
    assert 'invalid' in (await page.content()).lower()


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_logout_flow(page: Page):
    from django.contrib.auth.models import User
    user = User.objects.create_user(username='testuser', password='testpass123')
    
    await page.goto(f'{BASE_URL}/accounts/login/')
    await page.fill('input[name="username"]', 'testuser')
    await page.fill('input[name="password"]', 'testpass123')
    await page.click('button[type="submit"]')
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    
    logout_link = page.locator('a:has-text("Logout")')
    await logout_link.click()
    
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    await page.wait_for_timeout(500)
    
    assert 'login' in (await page.content()).lower()
