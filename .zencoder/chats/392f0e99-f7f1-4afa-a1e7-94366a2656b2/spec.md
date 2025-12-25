# Technical Specification: Campus Lost and Found Platform

## Technical Context

**Language/Framework**: Python 3.9+ / Django 4.2+  
**Database**: SQLite (development)  
**AI Service**: Google Gemini 2.0 Flash (via google-genai library)  
**Image Storage**: Cloudinary (free tier)  
**Frontend**: Django templates + Bootstrap 5  
**Authentication**: Django built-in auth system  

**Key Dependencies**:
- django >= 4.2
- google-genai >= 0.4.0
- cloudinary >= 1.35.0
- pillow >= 10.0.0 (image processing)
- python-decouple (environment variables)

---

## Technical Implementation Brief

1. **Image Processing Pipeline**
   - Images uploaded via form → temporarily saved to disk → sent to Gemini API
   - Gemini processes image and returns JSON: `{category, tags: [...]}`
   - User reviews/edits tags before final submission
   - Image uploaded to Cloudinary; local temp file deleted
   - Only Cloudinary URL stored in database (no local storage)

2. **Database Strategy**
   - Single SQLite database for development
   - Models: User (Django built-in), Item, Claim, Notification
   - Item.ai_tags stored as JSONField (Django 3.1+)
   - Claim.created_at indexed for chronological notifications

3. **Frontend Architecture**
   - Base template with navbar (Bootstrap 5)
   - Cards component for item display
   - Modal for claim confirmation
   - Dashboard view with search + filter
   - Simple in-app notification badge/page

4. **API/View Design**
   - POST /items/create → image upload + Gemini processing
   - GET /items → filtered dashboard (search + category)
   - POST /claims/create → claim submission + notification
   - GET /notifications → user's claim notifications
   - POST /notifications/<id>/reveal-contact → reveal claimer email

---

## Source Code Structure

```
lost_found/
├── manage.py
├── requirements.txt
├── .env (to be created with API keys)
├── lost_found/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── items/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   ├── ai_utils.py (Gemini processing)
│   ├── migrations/
│   └── templates/
│       ├── base.html
│       ├── dashboard.html
│       ├── report_item.html
│       ├── claim_modal.html
│       └── notifications.html
└── accounts/
    ├── models.py (extends User if needed)
    ├── views.py (login/signup)
    ├── urls.py
    └── templates/
        ├── login.html
        ├── signup.html
        └── profile.html
```

---

## Contracts

### Data Models

#### **User (Django Built-in)**
```
- id (PK)
- username (unique)
- email (unique)
- password (hashed)
- first_name, last_name
- is_active, is_staff
- date_joined
```

#### **Item**
```
- id (PK)
- user (FK → User)
- title (CharField, max_length=200)
- category (CharField, choices=[Electronics, Clothing, ...])
- description (TextField)
- image_url (URLField, Cloudinary)
- location (CharField, max_length=300)
- ai_tags (JSONField, default=list, e.g., ["backpack", "red", "leather"])
- status (CharField, choices=[Lost, Found, Claimed], default='Found')
- created_at (DateTimeField, auto_now_add=True)
- updated_at (DateTimeField, auto_now=True)

Indexes: (user, created_at), (status, category)
```

#### **Claim**
```
- id (PK)
- item (FK → Item)
- claimer (FK → User)
- message (TextField, optional)
- claimed_at (DateTimeField, auto_now_add=True)
- contact_revealed (BooleanField, default=False)

Indexes: (item, claimed_at), (claimer, claimed_at)
```

#### **Notification**
```
- id (PK)
- recipient (FK → User)
- claim (FK → Claim)
- message (TextField)
- is_read (BooleanField, default=False)
- created_at (DateTimeField, auto_now_add=True)

Indexes: (recipient, is_read, created_at)
```

---

### API Endpoints

| Method | Endpoint | Auth | Input | Output |
|--------|----------|------|-------|--------|
| GET | /items/ | No | search query, category | Items list (HTML) |
| POST | /items/create/ | Yes | image, title, location, description | Redirect to item detail |
| GET | /items/create/ | Yes | None | Form page with upload field |
| POST | /api/items/gemini-process/ | Yes | image (multipart) | JSON: `{category, tags}` |
| POST | /claims/create/ | Yes | item_id, message | Redirect, create Notification |
| GET | /notifications/ | Yes | None | User's notifications (HTML) |
| POST | /notifications/<id>/mark-read/ | Yes | None | JSON: `{status: "ok"}` |
| POST | /notifications/<id>/reveal-contact/ | Yes | None | JSON: `{email: "..."}` |

---

### Gemini Processing Contract

**Function**: `process_image_with_gemini(image_path: str) -> dict`

**Input**:
- `image_path` (str): Local file path to uploaded image

**Output**:
```json
{
  "category": "Electronics",
  "tags": ["laptop", "MacBook", "silver", "sticker"],
  "confidence": 0.92
}
```

**Error Handling**:
- If image unreadable → return `{error: "Invalid image format"}`
- If Gemini API fails → return `{error: "AI processing failed"}`

---

## Delivery Phases

### Phase 1: Project Setup & Core Models
- Initialize Django project
- Create Item, Claim, Notification models
- Configure Cloudinary and Gemini API keys
- Run migrations
- **Deliverable**: Django app with models and SQLite database ready

### Phase 2: User Authentication
- Create signup and login views/forms
- Set up login_required decorators
- Create base template with navbar + user menu
- Create logout view
- **Deliverable**: Users can register, login, logout; session persists

### Phase 3: Report Found Item Form + Gemini Integration
- Create Item creation form (image upload, title, location, description)
- Implement `process_image_with_gemini()` function
- Create AJAX endpoint for image processing (returns tags + category)
- Frontend: show Gemini suggestions, allow tag editing
- **Deliverable**: Users can upload image, see AI-generated tags, edit them, submit

### Phase 4: Dashboard & Search/Filter
- Create dashboard view with all items (paginated)
- Implement search (title + tags) and category filter
- Display items as Bootstrap cards
- Add "Claim" button to each card
- **Deliverable**: Homepage shows all items, searchable/filterable, responsive design

### Phase 5: Claim & Notification System
- Create Claim model, claim creation endpoint
- Create Notification model, notification creation on claim
- Create notifications page with list and "Reveal Contact" button
- Mark notifications as read
- **Deliverable**: Users can claim items, receive notifications, reveal contact info

### Phase 6: Polish & Testing
- Add error handling and user feedback (toast messages, validation)
- Write E2E tests (Playwright or similar)
- Test Gemini API with various images
- Test Cloudinary upload/URL generation
- Verify responsive design (mobile, tablet, desktop)
- **Deliverable**: All features working, tested, production-ready

---

## Verification Strategy

### Phase 1 Verification
**Commands**:
```bash
python manage.py migrate
python manage.py shell
# Verify models:
from items.models import Item, Claim, Notification
Item.objects.all()  # Should work
```
**Manual**: Run `python manage.py runserver` and access `/admin/` to verify models in admin panel.

---

### Phase 2 Verification
**Commands**:
```bash
# Create test user via shell or signup form
python manage.py shell
from django.contrib.auth.models import User
User.objects.create_user('testuser', 'test@example.com', 'testpass123')
```
**Manual**: 
1. Navigate to `/accounts/signup/` and create account
2. Log in and verify navbar shows username
3. Log out and verify redirected to home
4. Try accessing `/items/create/` without login → should redirect to login

---

### Phase 3 Verification
**Prerequisites**: Cloudinary API key and Gemini API key in `.env`

**Manual**:
1. Log in, navigate to `/items/create/`
2. Upload an image (test with electronics, clothing, etc.)
3. Verify Gemini processes image within 5 seconds
4. Verify tags and category display correctly
5. Edit a tag (remove one, add custom)
6. Submit form and verify item appears on dashboard

**Test Image**: Use a sample image (e.g., backpack, laptop, keys). Can be downloaded or provided.

---

### Phase 4 Verification
**Manual**:
1. Create 5+ items via admin or form
2. On dashboard (`/items/`), verify all items display as cards
3. Search for keyword (e.g., "laptop") → should filter results
4. Apply category filter (e.g., "Electronics") → should show only Electronics
5. Resize browser window → verify responsive layout (mobile: 1 column, tablet: 2, desktop: 3+)
6. Verify "Claim" button present on each card

---

### Phase 5 Verification
**Manual**:
1. Log in as User A
2. Create a found item (e.g., "Red Backpack")
3. Log in as User B (different browser/incognito)
4. Claim the item
5. Switch back to User A's browser
6. Navigate to `/notifications/` → should see claim notification
7. Click "Reveal Contact" → should see User B's email
8. Verify claim status on item changes to "Claimed"

---

### Phase 6 Verification
**Test Suite**:
- E2E tests (Playwright) covering: signup → report item → claim → notification
- Unit tests for `process_image_with_gemini()` with mock images
- Form validation tests (missing title, invalid image, etc.)

**Commands**:
```bash
pytest tests/
playwright test tests/e2e/
```

**Sample Test Data**:
- Helper script: `generate_sample_items.py` (creates 10 sample items with varied tags, categories)

---

## Environment Variables Required

```
GEMINI_API_KEY=your_gemini_key
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_key
CLOUDINARY_API_SECRET=your_cloudinary_secret
SECRET_KEY=your_django_secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

---

## Notes

- **Gemini API**: Free tier allows ~1500 requests/month; sufficient for hackathon use
- **Cloudinary**: Free tier allows 25 uploads/month + unlimited storage; upgrade URL transformation free
- **SQLite**: Sufficient for 100s of items; migration to PostgreSQL trivial later
- **No Docker**: Keeping simple for hackathon; can containerize post-launch
