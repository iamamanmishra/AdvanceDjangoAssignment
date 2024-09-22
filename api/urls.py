from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView, CreateEventView,
    EventListView, BookTicketView, MyBookingsView,
    CancelBookingView, MakePaymentView, RevertPaymentView, CancelEventView
)
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('create-event/', CreateEventView.as_view(), name='create-event'),
    path('events/', EventListView.as_view(), name='event-list'),
    path('book-ticket/', BookTicketView.as_view(), name='book-ticket'),
    path('my-bookings/', MyBookingsView.as_view(), name='my-bookings'),
    path('cancel-booking/<int:booking_id>/', CancelBookingView.as_view(), name='cancel-booking'),
    path('make-payment/', MakePaymentView.as_view(), name='make-payment'),
    path('revert-payment/', RevertPaymentView.as_view(), name='revert-payment'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('cancel-event/<int:event_id>/', CancelEventView.as_view(), name='cancel-event'),
]