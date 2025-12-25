import asyncio
import pytest
import pytest_asyncio
from playwright.async_api import async_playwright, Page, Browser
import os
import django
from django.conf import settings


BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lost_found.settings')
django.setup()


@pytest_asyncio.fixture
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest_asyncio.fixture
async def page(browser: Browser) -> Page:
    context = await browser.new_context()
    page = await context.new_page()
    yield page
    await context.close()


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
