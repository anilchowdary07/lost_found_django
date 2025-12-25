import pytest
from playwright.async_api import Page, expect
import os

BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000')


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_dashboard_no_items(page: Page):
    await page.goto(f'{BASE_URL}/')
    
    content = await page.content()
    assert 'Campus Lost & Found' in content
    assert 'No items found' in content


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_dashboard_with_items(page: Page):
    from items.models import Item
    from django.contrib.auth.models import User
    
    user = User.objects.create_user(username='testuser', password='testpass')
    Item.objects.create(
        user=user,
        title='Test Laptop',
        category='electronics',
        description='A test laptop',
        image_url='https://via.placeholder.com/200',
        location='Library',
        ai_tags=['laptop', 'electronics'],
        status='found'
    )
    
    await page.goto(f'{BASE_URL}/')
    
    content = await page.content()
    assert 'Test Laptop' in content
    assert 'Electronics' in content


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_dashboard_search(page: Page):
    from items.models import Item
    from django.contrib.auth.models import User
    
    user = User.objects.create_user(username='testuser', password='testpass')
    Item.objects.create(
        user=user,
        title='Red Backpack',
        category='accessories',
        description='A red colored backpack',
        image_url='https://via.placeholder.com/200',
        location='Student Center',
        ai_tags=['red', 'backpack', 'nylon'],
        status='found'
    )
    Item.objects.create(
        user=user,
        title='Blue Notebook',
        category='books',
        description='A blue notebook',
        image_url='https://via.placeholder.com/200',
        location='Cafeteria',
        ai_tags=['blue', 'notebook', 'paper'],
        status='found'
    )
    
    await page.goto(f'{BASE_URL}/')
    
    await page.fill('input[name="search"]', 'backpack')
    await page.click('button:has-text("Search")')
    
    await page.wait_for_timeout(1000)
    
    content = await page.content()
    assert 'Red Backpack' in content
    assert 'Blue Notebook' not in content


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_dashboard_filter_by_category(page: Page):
    from items.models import Item
    from django.contrib.auth.models import User
    
    user = User.objects.create_user(username='testuser', password='testpass')
    Item.objects.create(
        user=user,
        title='Laptop',
        category='electronics',
        description='An electronics item',
        image_url='https://via.placeholder.com/200',
        location='Lab',
        ai_tags=['laptop', 'electronics'],
        status='found'
    )
    Item.objects.create(
        user=user,
        title='T-Shirt',
        category='clothing',
        description='A clothing item',
        image_url='https://via.placeholder.com/200',
        location='Gym',
        ai_tags=['tshirt', 'clothing'],
        status='found'
    )
    
    await page.goto(f'{BASE_URL}/')
    
    await page.select_option('select[name="category"]', 'electronics')
    await page.click('button:has-text("Search")')
    
    await page.wait_for_timeout(1000)
    
    content = await page.content()
    assert 'Laptop' in content
    assert 'T-Shirt' not in content


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_dashboard_search_and_filter(page: Page):
    from items.models import Item
    from django.contrib.auth.models import User
    
    user = User.objects.create_user(username='testuser', password='testpass')
    Item.objects.create(
        user=user,
        title='Red Jacket',
        category='clothing',
        description='A red jacket',
        image_url='https://via.placeholder.com/200',
        location='Hallway',
        ai_tags=['red', 'jacket'],
        status='found'
    )
    Item.objects.create(
        user=user,
        title='Red Laptop',
        category='electronics',
        description='A red laptop',
        image_url='https://via.placeholder.com/200',
        location='Desk',
        ai_tags=['red', 'laptop'],
        status='found'
    )
    
    await page.goto(f'{BASE_URL}/')
    
    await page.fill('input[name="search"]', 'red')
    await page.select_option('select[name="category"]', 'clothing')
    await page.click('button:has-text("Search")')
    
    await page.wait_for_timeout(1000)
    
    content = await page.content()
    assert 'Red Jacket' in content
    assert 'Red Laptop' not in content


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_dashboard_no_search_results(page: Page):
    from items.models import Item
    from django.contrib.auth.models import User
    
    user = User.objects.create_user(username='testuser', password='testpass')
    Item.objects.create(
        user=user,
        title='Test Item',
        category='other',
        description='Test',
        image_url='https://via.placeholder.com/200',
        location='Test',
        ai_tags=['test'],
        status='found'
    )
    
    await page.goto(f'{BASE_URL}/')
    
    await page.fill('input[name="search"]', 'nonexistent')
    await page.click('button:has-text("Search")')
    
    await page.wait_for_timeout(1000)
    
    content = await page.content()
    assert 'No items found' in content
