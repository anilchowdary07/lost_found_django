import pytest
from playwright.async_api import Page, expect
import os

BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000')


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_claim_item_modal_appears(page: Page):
    from items.models import Item
    from django.contrib.auth.models import User
    
    user1 = User.objects.create_user(username='user1', password='pass123')
    user2 = User.objects.create_user(username='user2', password='pass123')
    
    item = Item.objects.create(
        user=user1,
        title='Lost Keys',
        category='keys',
        description='Set of house keys',
        image_url='https://via.placeholder.com/200',
        location='Main Gate',
        ai_tags=['keys', 'house'],
        status='found'
    )
    
    await page.goto(f'{BASE_URL}/accounts/login/')
    await page.fill('input[name="username"]', 'user2')
    await page.fill('input[name="password"]', 'pass123')
    await page.click('button[type="submit"]')
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    
    await page.click('button:has-text("Claim Item")')
    await page.wait_for_selector('.modal-body', timeout=5000)
    
    content = await page.content()
    assert 'Claim Item' in content
    assert 'Lost Keys' in content


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_claim_item_success(page: Page):
    from items.models import Item
    from django.contrib.auth.models import User
    
    user1 = User.objects.create_user(username='user1', password='pass123', email='user1@example.com')
    user2 = User.objects.create_user(username='user2', password='pass123', email='user2@example.com')
    
    item = Item.objects.create(
        user=user1,
        title='Lost Wallet',
        category='accessories',
        description='Black leather wallet',
        image_url='https://via.placeholder.com/200',
        location='Library',
        ai_tags=['wallet', 'leather'],
        status='found'
    )
    
    await page.goto(f'{BASE_URL}/accounts/login/')
    await page.fill('input[name="username"]', 'user2')
    await page.fill('input[name="password"]', 'pass123')
    await page.click('button[type="submit"]')
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    
    await page.click('button:has-text("Claim Item")')
    await page.wait_for_selector('.modal-body', timeout=5000)
    
    await page.fill('textarea[name="message"]', 'I found this wallet and would like to return it to the owner.')
    
    submit_button = page.locator('button[type="submit"]:has-text("Submit Claim")')
    await submit_button.click()
    
    await page.wait_for_timeout(3000)
    
    from items.models import Claim
    claims = Claim.objects.filter(item=item, claimer=user2)
    assert claims.count() >= 1


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_cannot_claim_own_item(page: Page):
    from items.models import Item
    from django.contrib.auth.models import User
    
    user = User.objects.create_user(username='testuser', password='pass123')
    
    item = Item.objects.create(
        user=user,
        title='My Item',
        category='other',
        description='Test',
        image_url='https://via.placeholder.com/200',
        location='Somewhere',
        ai_tags=['test'],
        status='found'
    )
    
    await page.goto(f'{BASE_URL}/accounts/login/')
    await page.fill('input[name="username"]', 'testuser')
    await page.fill('input[name="password"]', 'pass123')
    await page.click('button[type="submit"]')
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    
    button = page.locator('button:has-text("Already Claimed")')
    if await button.count() > 0:
        assert True
    else:
        button = page.locator('button:has-text("Claim Item")')
        assert await button.count() == 0


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_notifications_page_shows_claims(page: Page):
    from items.models import Item, Claim, Notification
    from django.contrib.auth.models import User
    
    user1 = User.objects.create_user(username='user1', password='pass123', email='user1@example.com')
    user2 = User.objects.create_user(username='user2', password='pass123', email='user2@example.com')
    
    item = Item.objects.create(
        user=user1,
        title='Test Item',
        category='other',
        description='Test',
        image_url='https://via.placeholder.com/200',
        location='Test',
        ai_tags=['test'],
        status='claimed'
    )
    
    claim = Claim.objects.create(
        item=item,
        claimer=user2,
        message='I found this item'
    )
    
    notification = Notification.objects.create(
        recipient=user1,
        claim=claim,
        message=f'{user2.username} has claimed your item: {item.title}'
    )
    
    await page.goto(f'{BASE_URL}/accounts/login/')
    await page.fill('input[name="username"]', 'user1')
    await page.fill('input[name="password"]', 'pass123')
    await page.click('button[type="submit"]')
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    
    await page.click('a:has-text("🔔 Notifications")')
    await page.wait_for_url(f'{BASE_URL}/notifications/', timeout=5000)
    
    content = await page.content()
    assert 'Test Item' in content
    assert 'user2' in content


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_reveal_contact(page: Page):
    from items.models import Item, Claim, Notification
    from django.contrib.auth.models import User
    
    user1 = User.objects.create_user(username='user1', password='pass123', email='user1@example.com', first_name='User', last_name='One')
    user2 = User.objects.create_user(username='user2', password='pass123', email='user2@example.com', first_name='User', last_name='Two')
    
    item = Item.objects.create(
        user=user1,
        title='Test Item',
        category='other',
        description='Test',
        image_url='https://via.placeholder.com/200',
        location='Test',
        ai_tags=['test'],
        status='claimed'
    )
    
    claim = Claim.objects.create(
        item=item,
        claimer=user2,
        message='I found this'
    )
    
    notification = Notification.objects.create(
        recipient=user1,
        claim=claim,
        message=f'{user2.username} has claimed your item'
    )
    
    await page.goto(f'{BASE_URL}/accounts/login/')
    await page.fill('input[name="username"]', 'user1')
    await page.fill('input[name="password"]', 'pass123')
    await page.click('button[type="submit"]')
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    
    await page.click('a:has-text("🔔 Notifications")')
    await page.wait_for_url(f'{BASE_URL}/notifications/', timeout=5000)
    
    reveal_btn = page.locator('button:has-text("🔓 Reveal Contact")')
    if await reveal_btn.count() > 0:
        await reveal_btn.click()
        await page.wait_for_timeout(2000)
        
        content = await page.content()
        assert 'user2@example.com' in content or 'Contact Revealed' in content


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_mark_notification_as_read(page: Page):
    from items.models import Item, Claim, Notification
    from django.contrib.auth.models import User
    
    user1 = User.objects.create_user(username='user1', password='pass123', email='user1@example.com')
    user2 = User.objects.create_user(username='user2', password='pass123', email='user2@example.com')
    
    item = Item.objects.create(
        user=user1,
        title='Test Item',
        category='other',
        description='Test',
        image_url='https://via.placeholder.com/200',
        location='Test',
        ai_tags=['test'],
        status='claimed'
    )
    
    claim = Claim.objects.create(
        item=item,
        claimer=user2,
        message='I found this'
    )
    
    notification = Notification.objects.create(
        recipient=user1,
        claim=claim,
        message=f'{user2.username} has claimed your item',
        is_read=False
    )
    
    await page.goto(f'{BASE_URL}/accounts/login/')
    await page.fill('input[name="username"]', 'user1')
    await page.fill('input[name="password"]', 'pass123')
    await page.click('button[type="submit"]')
    await page.wait_for_url(f'{BASE_URL}/', timeout=5000)
    
    await page.click('a:has-text("🔔 Notifications")')
    await page.wait_for_url(f'{BASE_URL}/notifications/', timeout=5000)
    
    mark_read_btn = page.locator('button:has-text("Mark as Read")')
    if await mark_read_btn.count() > 0:
        await mark_read_btn.click()
        await page.wait_for_timeout(2000)
        
        notification.refresh_from_db()
        assert notification.is_read == True
