from django.urls import path
from . import views

urlpatterns = [
    # Service Categories
    path('categories/', views.ServiceCategoryListView.as_view(), name='service-categories'),
    path('categories/<int:pk>/', views.ServiceCategoryDetailView.as_view(), name='service-category-detail'),

    # Services
    path('', views.ServiceListView.as_view(), name='service-list'),
    path('<int:pk>/', views.ServiceDetailView.as_view(), name='service-detail'),
    path('create/', views.ServiceCreateView.as_view(), name='service-create'),
    path('<int:pk>/update/', views.ServiceUpdateView.as_view(), name='service-update'),
    path('<int:pk>/delete/', views.ServiceDeleteView.as_view(), name='service-delete'),
    path('popular/', views.popular_services_view, name='popular-services'),

    # Provider functionality
    path('providers/register/', views.become_provider_view, name='become-provider'),
    path('providers/profile/', views.ProviderProfileView.as_view(), name='provider-profile'),
    path('providers/dashboard/', views.provider_dashboard_view, name='provider-dashboard'),
    path('providers/earnings/', views.provider_earnings_view, name='provider-earnings'),
    path('providers/analytics/', views.provider_analytics_view, name='provider-analytics'),
    path('providers/schedule/', views.provider_schedule_view, name='provider-schedule'),
    path('providers/jobs/', views.provider_jobs_view, name='provider-jobs'),
    path('providers/jobs/<int:booking_id>/accept/', views.accept_job_view, name='accept-job'),
    path('providers/jobs/<int:booking_id>/decline/', views.decline_job_view, name='decline-job'),

    # Bookings
    path('bookings/', views.BookingListCreateView.as_view(), name='booking-list-create'),
    path('bookings/<int:pk>/', views.BookingDetailView.as_view(), name='booking-detail'),
    path('bookings/<int:booking_id>/status/', views.update_booking_status_view, name='booking-status'),
    path('bookings/<int:booking_id>/reschedule/', views.reschedule_booking_view, name='booking-reschedule'),
    path('bookings/<int:booking_id>/cancel/', views.cancel_booking_view, name='booking-cancel'),

    # Reviews
    path('reviews/', views.ReviewListCreateView.as_view(), name='review-list-create'),
    path('bookings/<int:booking_id>/review/', views.create_booking_review_view, name='create-booking-review'),
    path('reviews/<int:review_id>/respond/', views.respond_to_review_view, name='review-respond'),

    # Payments
    path('payments/', views.PaymentListView.as_view(), name='payment-list'),
    path('payments/process/', views.process_payment_view, name='payment-process'),
    path('payments/methods/', views.payment_methods_view, name='payment-methods'),
    path('payments/refund/', views.refund_payment_view, name='payment-refund'),

    # Credits
    path('credits/balance/', views.user_credits_balance_view, name='credits-balance'),
    path('credits/purchase/', views.purchase_credits_view, name='credits-purchase'),

    # Addresses
    path('addresses/', views.AddressListCreateView.as_view(), name='address-list-create'),
    path('addresses/<int:pk>/', views.AddressDetailView.as_view(), name='address-detail'),

    # Location Services
    path('nearby/', views.nearby_services_view, name='nearby-services'),
    path('location/geocode/', views.geocode_location_view, name='geocode-location'),
    path('location/validate/', views.validate_address_view, name='validate-address'),

    # Chat & Messaging
    path('chat/conversations/', views.ConversationListCreateView.as_view(), name='conversation-list-create'),
    path('chat/conversations/<int:pk>/', views.ConversationDetailView.as_view(), name='conversation-detail'),
    path('chat/messages/', views.MessageListCreateView.as_view(), name='message-list-create'),
    path('chat/conversations/<int:conversation_id>/mark-read/', views.mark_messages_read_view, name='mark-messages-read'),

    # Notifications
    path('notifications/', views.NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read_view, name='mark-notification-read'),
    path('notifications/read-all/', views.mark_all_notifications_read_view, name='mark-all-notifications-read'),
    path('notifications/<int:notification_id>/delete/', views.delete_notification_view, name='delete-notification'),
    path('notifications/count/', views.notification_count_view, name='notification-count'),
    path('notifications/preferences/', views.NotificationPreferenceView.as_view(), name='notification-preferences'),
    path('notifications/send/', views.send_notification_view, name='send-notification'),
]