# lost_found_django

A Django-based lost and found application for reporting and claiming lost items.

## Features

- User registration and authentication
- Report lost or found items
- Claim notifications
- Item search and filtering
- QR code generation for items
- AI-powered item descriptions (Gemini API)
- Cloudinary image storage
- Rate limiting for production

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your configuration
4. Run migrations: `python manage.py migrate`
5. Create superuser: `python manage.py createsuperuser`
6. Run development server: `python manage.py runserver`

## Deployment

This project is configured for deployment on Render. See `.env.example` for required environment variables.
