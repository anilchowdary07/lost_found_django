# Feature Specification: Campus Lost and Found Platform

## User Stories

### User Story 1 - Report a Found Item with AI-Generated Tags

**Description**: A student finds a lost item and wants to report it to the platform quickly without typing lengthy descriptions.

**Acceptance Scenarios**:

1. **Given** a user is logged in, **When** they navigate to "Report Found Item", **Then** they see a form with image upload, title, category selector, location field, and description box.
2. **Given** a user uploads an image, **When** the upload completes, **Then** Gemini API processes the image and suggests tags and category (editable).
3. **Given** Gemini provides suggested tags and category, **When** the user reviews them, **Then** they can modify/delete tags or change the category before submitting.
4. **Given** a user submits a found item report, **When** the form is posted, **Then** the item appears on the dashboard visible to all users.

---

### User Story 2 - Search and Filter Items

**Description**: A student wants to find a lost item by searching and filtering through the platform.

**Acceptance Scenarios**:

1. **Given** a user is on the dashboard, **When** they use the search bar, **Then** results include items matching keywords in title or AI-generated tags.
2. **Given** search results are displayed, **When** the user applies a category filter, **Then** results are filtered to only show items in that category.
3. **Given** search and filter are applied, **When** results are empty, **Then** a helpful message is displayed ("No items found").

---

### User Story 3 - Claim a Found Item and Reveal Contact

**Description**: A user finds an item matching their lost item and wants to claim it and contact the finder.

**Acceptance Scenarios**:

1. **Given** a user views a found item, **When** they click "Claim", **Then** a modal appears asking for confirmation and optional claim message.
2. **Given** a user confirms the claim, **When** the claim is submitted, **Then** an in-app notification is sent to the item poster.
3. **Given** the item poster receives a claim notification, **When** they click "Reveal Contact", **Then** the claimer's contact info (email) is shown.
4. **Given** an item is claimed, **When** the status changes to "Claimed", **Then** it remains visible on the dashboard but marked as claimed.

---

### User Story 4 - User Authentication

**Description**: A user needs to sign up, log in, and maintain a session to use the platform.

**Acceptance Scenarios**:

1. **Given** a new user, **When** they visit the signup page, **Then** they can create an account with email and password.
2. **Given** a registered user, **When** they log in with valid credentials, **Then** they are authenticated and redirected to the dashboard.
3. **Given** a logged-in user, **When** they log out, **Then** they are redirected to the home page and session is cleared.

---

## Requirements

### Functional Requirements

1. **Item Posting**
   - Users can upload images for found items
   - Gemini API auto-generates editable tags and category from image
   - Category options: Electronics, Clothing, Accessories, Books, Jewelry, Documents, Keys, Other
   - Users can modify AI-suggested tags before submission
   - Items store: title, category, description, image URL (via Cloudinary), location, tags (JSON), status

2. **Dashboard & Display**
   - Dashboard displays all items in card layout using Bootstrap 5
   - Cards show: image, title, category, location, tags, status, claim button
   - Responsive design (mobile-first)

3. **Search & Filter**
   - Keyword search across title and AI-tags
   - Category filter dropdown
   - Search and filter work together

4. **Claim System**
   - "Claim" button on each item card
   - Modal confirmation with optional message
   - Claim creates notification for item poster
   - Claimer contact info hidden by default, revealed via "Reveal Contact" button

5. **Notifications**
   - In-app notification dashboard for claim alerts
   - Notifications show: who claimed, when, and "Reveal Contact" button
   - Mark notifications as read

6. **User Authentication**
   - Django built-in auth (User model)
   - Login/signup forms
   - User session management

---

## Success Criteria

1. ✅ Users can upload images and receive AI-generated tags within 5 seconds
2. ✅ Tags are editable and submission works smoothly
3. ✅ Dashboard displays all items with proper filtering and search
4. ✅ Claiming an item sends in-app notification to poster
5. ✅ Contact info is revealed securely only via button click
6. ✅ Responsive design works on mobile, tablet, desktop
7. ✅ All operations complete without manual type-heavy input for found items
8. ✅ Zero external API costs (free Gemini, free Cloudinary, free Django/SQLite)
