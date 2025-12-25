from django.db import models
from django.contrib.auth.models import User
import uuid


CATEGORY_CHOICES = [
    ('electronics', 'Electronics'),
    ('clothing', 'Clothing'),
    ('accessories', 'Accessories'),
    ('books', 'Books'),
    ('jewelry', 'Jewelry'),
    ('documents', 'Documents'),
    ('keys', 'Keys'),
    ('other', 'Other'),
]

STATUS_CHOICES = [
    ('reported', 'Reported'),
    ('claimed', 'Claimed'),
    ('verified', 'Identity Verified'),
    ('returned', 'Returned'),
]

ITEM_TYPE_CHOICES = [
    ('lost', 'Lost'),
    ('found', 'Found'),
]


class Item(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='items')
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True, null=True)
    image_url = models.URLField()
    location = models.CharField(max_length=300)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    ai_tags = models.JSONField(default=list)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='reported'
    )
    item_type = models.CharField(
        max_length=10,
        choices=ITEM_TYPE_CHOICES,
        default='found'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'category']),
        ]

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"


CLAIM_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('accepted', 'Accepted'),
    ('rejected', 'Rejected'),
    ('completed', 'Completed'),
]


class Claim(models.Model):
    item = models.OneToOneField(Item, on_delete=models.CASCADE, related_name='claim')
    claimer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='claims')
    message = models.TextField(blank=True, null=True)
    claimed_at = models.DateTimeField(auto_now_add=True)
    contact_revealed = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=CLAIM_STATUS_CHOICES,
        default='pending'
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['item', 'claimed_at']),
            models.Index(fields=['claimer', 'claimed_at']),
        ]

    def __str__(self):
        return f"Claim on {self.item.title} by {self.claimer.username}"


class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'created_at']),
        ]

    def __str__(self):
        return f"Notification for {self.recipient.username} - Claim on {self.claim.item.title}"


class QRCode(models.Model):
    claim = models.OneToOneField(Claim, on_delete=models.CASCADE, related_name='qr_code')
    code = models.CharField(max_length=255, unique=True, default=uuid.uuid4)
    qr_image_url = models.URLField(null=True, blank=True)
    scanned = models.BooleanField(default=False)
    scanned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"QR Code for {self.claim.item.title}"


class ItemTimeline(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='timeline')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['changed_at']
        indexes = [
            models.Index(fields=['item', 'changed_at']),
        ]

    def __str__(self):
        return f"{self.item.title} - {self.status} at {self.changed_at}"


class LocationHistory(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='location_history')
    latitude = models.FloatField()
    longitude = models.FloatField()
    location_name = models.CharField(max_length=300)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
        verbose_name_plural = 'Location Histories'

    def __str__(self):
        return f"{self.item.title} at {self.location_name}"


MODERATION_STATUS_CHOICES = [
    ('pending', 'Pending Review'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('removed', 'Content Removed'),
]

FLAG_REASON_CHOICES = [
    ('inappropriate', 'Inappropriate Content'),
    ('spam', 'Spam'),
    ('misleading', 'Misleading Information'),
    ('offensive', 'Offensive Language'),
    ('fraud', 'Suspected Fraud'),
    ('duplicate', 'Duplicate Listing'),
    ('other', 'Other'),
]


class ContentModeration(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='moderation_flags', null=True, blank=True)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='moderation_flags', null=True, blank=True)
    flagged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='flags_created')
    reason = models.CharField(max_length=20, choices=FLAG_REASON_CHOICES)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=MODERATION_STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='flags_reviewed')
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['item', 'status']),
            models.Index(fields=['claim', 'status']),
        ]

    def __str__(self):
        return f"Flag on {self.get_content_type()} - {self.get_reason_display()}"

    def get_content_type(self):
        return f"Item: {self.item.title}" if self.item else f"Claim: {self.claim.id}"


DISPUTE_STATUS_CHOICES = [
    ('open', 'Open'),
    ('in_progress', 'In Progress'),
    ('resolved', 'Resolved'),
    ('closed', 'Closed'),
]

DISPUTE_RESOLUTION_CHOICES = [
    ('favor_claimer', 'Favor Claimer'),
    ('favor_reporter', 'Favor Reporter'),
    ('mutual_agreement', 'Mutual Agreement'),
    ('no_resolution', 'No Resolution'),
]


class DisputeResolution(models.Model):
    claim = models.OneToOneField(Claim, on_delete=models.CASCADE, related_name='dispute')
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disputes_reported')
    claimer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disputes_claimed')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=DISPUTE_STATUS_CHOICES, default='open')
    resolution = models.CharField(max_length=20, choices=DISPUTE_RESOLUTION_CHOICES, null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='disputes_assigned')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['claim', 'status']),
        ]

    def __str__(self):
        return f"Dispute on Claim {self.claim.id} - {self.get_status_display()}"
