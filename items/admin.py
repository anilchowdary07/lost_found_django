from django.contrib import admin
from .models import Item, Claim, Notification, QRCode, ItemTimeline, LocationHistory


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'user', 'status', 'item_type', 'created_at']
    list_filter = ['status', 'category', 'item_type', 'created_at']
    search_fields = ['title', 'description', 'location']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ['id', 'item', 'claimer', 'claimed_at', 'contact_revealed', 'verified_at']
    list_filter = ['claimed_at', 'contact_revealed', 'verified_at']
    search_fields = ['item__title', 'claimer__username']
    readonly_fields = ['claimed_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'recipient', 'claim', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['recipient__username', 'claim__item__title']
    readonly_fields = ['created_at']


@admin.register(QRCode)
class QRCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'claim', 'scanned', 'scanned_at', 'created_at']
    list_filter = ['scanned', 'created_at']
    search_fields = ['claim__item__title', 'code']
    readonly_fields = ['code', 'created_at']


@admin.register(ItemTimeline)
class ItemTimelineAdmin(admin.ModelAdmin):
    list_display = ['item', 'status', 'changed_by', 'changed_at']
    list_filter = ['status', 'changed_at']
    search_fields = ['item__title']
    readonly_fields = ['changed_at']


@admin.register(LocationHistory)
class LocationHistoryAdmin(admin.ModelAdmin):
    list_display = ['item', 'location_name', 'latitude', 'longitude', 'recorded_at']
    list_filter = ['recorded_at']
    search_fields = ['item__title', 'location_name']
    readonly_fields = ['recorded_at']
