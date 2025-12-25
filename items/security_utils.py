import bleach
from django.utils.html import escape
import re


ALLOWED_TAGS = []
ALLOWED_ATTRIBUTES = {}


def sanitize_user_input(text, max_length=None, field_type='text'):
    if not text:
        return text
    
    text = escape(text)
    
    if field_type == 'html':
        text = bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)
    
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text


def sanitize_ai_tags(tags_list):
    if not tags_list or not isinstance(tags_list, list):
        return []
    
    sanitized = []
    for tag in tags_list[:10]:
        if isinstance(tag, str):
            tag = sanitize_user_input(tag.strip(), max_length=50)
            if tag and tag.replace(' ', '').replace('-', '').isalnum():
                sanitized.append(tag)
    
    return sanitized


def sanitize_description(description, max_length=2000):
    if not description:
        return description
    
    description = escape(description.strip())
    
    if len(description) > max_length:
        description = description[:max_length]
    
    return description


def sanitize_title(title, max_length=200):
    if not title:
        return title
    
    title = escape(title.strip())
    
    if len(title) > max_length:
        title = title[:max_length]
    
    return title


def sanitize_location(location, max_length=300):
    if not location:
        return location
    
    location = escape(location.strip())
    
    if len(location) > max_length:
        location = location[:max_length]
    
    return location
