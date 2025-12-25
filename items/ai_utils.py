import json
import base64
from pathlib import Path
from django.conf import settings

try:
    import google.generativeai as genai
except ImportError:
    genai = None


def process_image_with_gemini(image_path: str) -> dict:
    if not genai:
        return {
            'error': 'Google Generative AI library not installed. Install with: pip install google-generativeai'
        }

    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == '':
        return {
            'error': 'GEMINI_API_KEY not set in environment variables'
        }

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')

        image_path_obj = Path(image_path)
        if not image_path_obj.exists():
            return {'error': f'Image file not found: {image_path}'}

        with open(image_path, 'rb') as f:
            image_data = base64.standard_b64encode(f.read()).decode('utf-8')

        file_ext = image_path_obj.suffix.lower()
        mime_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
        }
        mime_type = mime_type_map.get(file_ext, 'image/jpeg')

        image_part = {
            'mime_type': mime_type,
            'data': image_data,
        }

        prompt = """Analyze this image and provide:
1. A primary category (choose ONE from: Electronics, Clothing, Accessories, Books, Jewelry, Documents, Keys, Other)
2. 3-5 specific tags describing the item (e.g., color, brand, type, distinctive features)

Return as JSON:
{
    "category": "category_name",
    "tags": ["tag1", "tag2", "tag3"]
}

Only return valid JSON, no other text."""

        response = model.generate_content([image_part, prompt])
        response_text = response.text.strip()

        # Try to parse as JSON
        try:
            # Look for JSON block in the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
            else:
                data = json.loads(response_text)

            category = data.get('category', 'Other').lower()
            tags = data.get('tags', [])

            if not isinstance(tags, list):
                tags = [str(tags)]

            tags = [str(tag).strip() for tag in tags if tag]

            valid_categories = [
                'electronics', 'clothing', 'accessories', 'books',
                'jewelry', 'documents', 'keys', 'other'
            ]
            if category not in valid_categories:
                category = 'other'

            return {
                'category': category,
                'tags': tags[:5],
                'confidence': 0.95
            }

        except json.JSONDecodeError:
            return {
                'error': 'Could not parse Gemini response as JSON',
                'raw_response': response_text[:500]
            }

    except Exception as e:
        return {
            'error': f'Gemini API error: {str(e)}'
        }
