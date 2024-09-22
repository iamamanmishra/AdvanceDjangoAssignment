from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView, CreateEventView,
    EventListView, BookTicketView
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
]