from django.urls import path
from . import views

app_name = 'items'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('report/', views.report_item, name='report_item'),
    path('api/claim/', views.claim_item, name='claim_item'),
    path('api/search-nearby/', views.search_nearby_items, name='search_nearby_items'),
    path('notifications/', views.notifications, name='notifications'),
    path('api/notifications/<int:notification_id>/reveal-contact/', views.reveal_contact_view, name='reveal_contact'),
    path('api/notifications/<int:notification_id>/mark-read/', views.mark_notification_read_view, name='mark_notification_read'),
    path('api/claims/<int:claim_id>/accept/', views.accept_claim, name='accept_claim'),
    path('api/claims/<int:claim_id>/reject/', views.reject_claim, name='reject_claim'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('<int:item_id>/', views.item_detail, name='item_detail'),
    path('<int:item_id>/edit/', views.edit_item, name='edit_item'),
    path('api/<int:item_id>/delete/', views.delete_item, name='delete_item'),
    path('api/notify-owner/', views.notify_owner, name='notify_owner'),
    path('api/claim/<int:claim_id>/qrcode/', views.generate_qr_code_view, name='generate_qr_code'),
    path('api/qrcode/verify/', views.verify_qr_code, name='verify_qr_code'),
    path('api/<int:item_id>/mark-returned/', views.mark_item_returned, name='mark_item_returned'),
    path('admin/heatmap/', views.admin_heatmap, name='admin_heatmap'),
    path('gallery/', views.found_items_gallery, name='found_items_gallery'),
    path('lost/', views.lost_items_gallery, name='lost_items_gallery'),
    path('api/updates/', views.get_updates, name='get_updates'),
    path('admin/moderation/', views.admin_moderation, name='admin_moderation'),
    path('api/flag-content/', views.flag_content, name='flag_content'),
    path('api/handle-moderation/', views.handle_moderation, name='handle_moderation'),
    path('admin/disputes/', views.disputes_dashboard, name='disputes_dashboard'),
    path('api/create-dispute/', views.create_dispute, name='create_dispute'),
    path('api/resolve-dispute/', views.resolve_dispute, name='resolve_dispute'),
]
