from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny

from . import serializers
from .models import User, Event, Booking
from .serializers import RegisterSerializer, LoginSerializer, LogoutSerializer, EventSerializer, EventListSerializer, \
    BookingSerializer, BookingDetailSerializer, PaymentSerializer, RevertPaymentSerializer
from .permissions import IsEventManager
from rest_framework import generics, status, permissions, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404


# Create your views here.

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
            return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)


class CreateEventView(generics.CreateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated, IsEventManager]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class EventListView(generics.ListAPIView):
    queryset = Event.objects.all()
    serializer_class = EventListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['location', 'date', 'category']
    search_fields = ['title', 'description']


class BookTicketView(generics.CreateAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MyBookingsView(generics.ListAPIView):
    serializer_class = BookingDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)


class CancelBookingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        if booking.status == 'cancelled':
            return Response({"detail": "Booking already cancelled."}, status=status.HTTP_400_BAD_REQUEST)

        booking.status = 'cancelled'
        booking.save()

        # Revert payment
        if hasattr(booking, 'payment'):
            payment = booking.payment
            payment.status = 'reverted'
            payment.save()

        # Update available tickets
        event = booking.event
        event.available_tickets += booking.number_of_tickets
        event.save()

        # Send Email Notification (optional)
        # Implement email sending here

        return Response({"detail": "Booking cancelled and payment reverted."}, status=status.HTTP_200_OK)


class MakePaymentView(generics.CreateAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        booking_id = self.request.data.get('booking_id')
        payment_method = self.request.data.get('payment_method')
        amount = self.request.data.get('amount')
        booking = get_object_or_404(Booking, id=booking_id, user=self.request.user)

        # Simulate payment validation
        # Implement actual payment gateway integration here if needed

        serializer.save(booking=booking, payment_method=payment_method, amount=amount, status='completed')

        # Send Email Notification (optional)
        # Implement email sending here


class RevertPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = RevertPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
            return Response({"detail": "Payment reverted and booking cancelled."}, status=status.HTTP_200_OK)
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)


class CancelEventView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEventManager]

    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id, created_by=request.user)
        bookings = event.bookings.filter(status='booked')

        for booking in bookings:
            # Cancel each booking
            booking.status = 'cancelled'
            booking.save()

            # Revert payment
            if hasattr(booking, 'payment'):
                payment = booking.payment
                payment.status = 'reverted'
                payment.save()

            # Update available tickets
            event.available_tickets += booking.number_of_tickets
            event.save()

            # Send cancellation email to user
            send_mail(
                'Event Cancelled',
                f'Hi {booking.user.username}, the event {event.title} has been cancelled.',
                settings.EMAIL_HOST_USER,
                [booking.user.email],
                fail_silently=False,
            )

        # Optionally, deactivate or delete the event
        event.delete()

        return Response({"detail": "Event cancelled and all associated bookings reverted."}, status=status.HTTP_200_OK)
