from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import User, Event, Booking, Payment
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from datetime import timedelta
from django.core import mail

class APITestSetup(APITestCase):
    def setUp(self):
        # Create a regular user
        self.user = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='password123',
            role='user',
            first_name='User',
            last_name='One'
        )
        
        # Create an event manager
        self.manager = User.objects.create_user(
            username='manager1',
            email='manager1@example.com',
            password='password123',
            role='event_manager',
            first_name='Manager',
            last_name='One'
        )
        
        # Obtain tokens for both users
        self.user_tokens = self.get_tokens_for_user(self.user)
        self.manager_tokens = self.get_tokens_for_user(self.manager)
        
        # Create a sample event
        self.event = Event.objects.create(
            title="Concert",
            description="Live music concert",
            date=timezone.now().date() + timedelta(days=10),
            time=timezone.now().replace(hour=18, minute=0, second=0, microsecond=0).time(),
            location="Stadium",
            category="music",
            payment_options="Credit Card, PayPal",
            created_by=self.manager,
            total_tickets=100,
            available_tickets=100
        )
    
    def get_tokens_for_user(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

class UserRegistrationTests(APITestSetup):
    def test_register_user_success(self):
        url = reverse('register')
        data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "newpassword123",
            "role": "user",
            "first_name": "New",
            "last_name": "User"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 3)
        self.assertEqual(User.objects.get(username='newuser').email, 'newuser@example.com')
    
    def test_register_user_existing_email(self):
        url = reverse('register')
        data = {
            "email": "user1@example.com",  # Existing email
            "username": "anotheruser",
            "password": "password123",
            "role": "user",
            "first_name": "Another",
            "last_name": "User"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
    
    def test_register_user_invalid_data(self):
        url = reverse('register')
        data = {
            "email": "invalidemail",  # Invalid email format
            "username": "",  # Empty username
            "password": "short",  # Password too short
            "role": "unknown_role",  # Invalid role
            # Missing first_name and last_name if required
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertIn('username', response.data)
        self.assertIn('password', response.data)
        self.assertIn('role', response.data)

class UserAuthenticationTests(APITestSetup):
    def test_login_success(self):
        url = reverse('login')
        data = {
            "email": "user1@example.com",
            "password": "password123"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_login_incorrect_credentials(self):
        url = reverse('login')
        data = {
            "email": "user1@example.com",
            "password": "wrongpassword"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('detail', response.data)
    
    def test_logout_success(self):
        url = reverse('logout')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user_tokens['access'])
        data = {
            "refresh": self.user_tokens['refresh']
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], "Successfully logged out.")
    
    def test_logout_invalid_token(self):
        url = reverse('logout')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user_tokens['access'])
        data = {
            "refresh": "invalidtoken123"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

class EventManagementTests(APITestSetup):
    def test_create_event_success_by_event_manager(self):
        url = reverse('create-event')
        data = {
            "title": "Theatre Play",
            "description": "Drama performance",
            "date": (timezone.now().date() + timedelta(days=20)).isoformat(),
            "time": "19:00",
            "location": "Theatre Hall",
            "category": "theatre",
            "payment_options": "Credit Card, PayPal",
            "total_tickets": 50
        }
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.manager_tokens['access'])
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Event.objects.count(), 2)
        self.assertEqual(Event.objects.get(title="Theatre Play").location, "Theatre Hall")
    
    def test_create_event_by_non_event_manager(self):
        url = reverse('create-event')
        data = {
            "title": "Basketball Game",
            "description": "Professional basketball match",
            "date": (timezone.now().date() + timedelta(days=15)).isoformat(),
            "time": "17:00",
            "location": "Sports Arena",
            "category": "sports",
            "payment_options": "Credit Card",
            "total_tickets": 200
        }
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user_tokens['access'])
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_create_event_invalid_data(self):
        url = reverse('create-event')
        data = {
            "title": "",  # Missing title
            "description": "Invalid event",
            "date": "invalid-date",  # Incorrect date format
            "time": "25:00",  # Invalid time
            "location": "",
            "category": "unknown_category",
            "payment_options": "",
            "total_tickets": -10  # Invalid ticket count
        }
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.manager_tokens['access'])
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)
        self.assertIn('date', response.data)
        self.assertIn('time', response.data)
        self.assertIn('location', response.data)
        self.assertIn('category', response.data)
        self.assertIn('payment_options', response.data)
        self.assertIn('total_tickets', response.data)

class TicketBookingTests(APITestSetup):
    def test_book_ticket_success(self):
        url = reverse('book-ticket')
        data = {
            "event_id": self.event.id,
            "number_of_tickets": 2
        }
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user_tokens['access'])
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['number_of_tickets'], 2)
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(Event.objects.get(id=self.event.id).available_tickets, 98)
    
    def test_book_ticket_insufficient_tickets(self):
        url = reverse('book-ticket')
        data = {
            "event_id": self.event.id,
            "number_of_tickets": 150  # Exceeds available tickets
        }
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user_tokens['access'])
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertEqual(Booking.objects.count(), 0)
    
    def test_book_ticket_nonexistent_event(self):
        url = reverse('book-ticket')
        data = {
            "event_id": 999,  # Assuming this ID doesn't exist
            "number_of_tickets": 1
        }
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user_tokens['access'])
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('detail', response.data)

class BookingManagementTests(APITestSetup):
    def setUp(self):
        super().setUp()
        # Create a booking for user
        self.booking = Booking.objects.create(
            user=self.user,
            event=self.event,
            number_of_tickets=3,
            status='booked'
        )
        self.event.available_tickets -= 3
        self.event.save()
    
    def test_view_bookings_user(self):
        url = reverse('my-bookings')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user_tokens['access'])
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['number_of_tickets'], 3)
    
    def test_cancel_booking_success(self):
        url = reverse('cancel-booking', kwargs={'booking_id': self.booking.id})
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user_tokens['access'])
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.booking.refresh_from_db()
        self.event.refresh_from_db()
        self.assertEqual(self.booking.status, 'cancelled')
        self.assertEqual(self.event.available_tickets, 100)
    
    def test_cancel_booking_already_cancelled(self):
        # Cancel the booking first
        self.booking.status = 'cancelled'
        self.booking.save()
        self.event.available_tickets += 3
        self.event.save()
        
        url = reverse('cancel-booking', kwargs={'booking_id': self.booking.id})
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user_tokens['access'])
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], "Booking already cancelled.")
    
    def test_cancel_booking_not_owner(self):
        # Create another user
        other_user = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='password123',
            role='user',
            first_name='User',
            last_name='Two'
        )
        other_tokens = self.get_tokens_for_user(other_user)
        
        url = reverse('cancel-booking', kwargs={'booking_id': self.booking.id})
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + other_tokens['access'])
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  # As per get_object_or_404

class PaymentSimulationTests(APITestSetup):
    def setUp(self):
        super().setUp()
        # Create a booking for payment
        self.booking = Booking.objects.create(
            user=self.user,
            event=self.event,
            number_of_tickets=2,
            status='booked'
        )
        self.event.available_tickets -= 2
        self.event.save()
    
    def test_make_payment_success(self):
        url = reverse('make-payment')
        data = {
            "booking_id": self.booking.id,
            "payment_method": "Credit Card",
            "amount": 100.00
        }
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user_tokens['access'])
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Payment.objects.count(), 1)
        payment = Payment.objects.get(booking=self.booking)
        self.assertEqual(payment.status, 'completed')
        self.assertEqual(payment.amount, 100.00)
    
    def test_make_payment_canceled_booking(self):
        # Cancel the booking first
        self.booking.status = 'cancelled'
        self.booking.save()
        self.event.available_tickets += 2
        self.event.save()
        
        url = reverse('make-payment')
        data = {
            "booking_id": self.booking.id,
            "payment_method": "PayPal",
            "amount": 50.00
        }
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user_tokens['access'])
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
    
    def test_make_payment_duplicate(self):
        # Make the first payment
        Payment.objects.create(
            booking=self.booking,
            payment_method="Credit Card",
            amount=100.00,
            status='completed'
        )
        
        url = reverse('make-payment')
        data = {
            "booking_id": self.booking.id,
            "payment_method": "PayPal",
            "amount": 100.00
        }
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user_tokens['access'])
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
    
    def test_revert_payment_success(self):
        # Make a payment first
        payment = Payment.objects.create(
            booking=self.booking,
            payment_method="Credit Card",
            amount=100.00,
            status='completed'
        )
        
        url = reverse('revert-payment')
        data = {
            "booking_id": self.booking.id,
            "reason": "Booking canceled"
        }
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user_tokens['access'])
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.event.refresh_from_db()
        self.assertEqual(payment.status, 'reverted')
        self.assertEqual(self.booking.status, 'cancelled')
        self.assertEqual(self.event.available_tickets, 100)
    
    def test_revert_payment_nonexistent_payment(self):
        url = reverse('revert-payment')
        data = {
            "booking_id": self.booking.id,
            "reason": "No payment made"
        }
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user_tokens['access'])
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

class EventFilteringTests(APITestSetup):
    def setUp(self):
        super().setUp()
        # Create additional events for filtering
        Event.objects.create(
            title="Sports Event",
            description="Basketball match",
            date=timezone.now().date() + timedelta(days=5),
            time=timezone.now().replace(hour=15, minute=0, second=0, microsecond=0).time(),
            location="Sports Arena",
            category="sports",
            payment_options="Credit Card",
            created_by=self.manager,
            total_tickets=150,
            available_tickets=150
        )
        
        Event.objects.create(
            title="Music Festival",
            description="Outdoor music festival",
            date=timezone.now().date() + timedelta(days=20),
            time=timezone.now().replace(hour=20, minute=0, second=0, microsecond=0).time(),
            location="City Park",
            category="music",
            payment_options="Credit Card, PayPal",
            created_by=self.manager,
            total_tickets=300,
            available_tickets=300
        )
    
    def test_filter_events_by_location(self):
        url = reverse('event-list') + '?location=Stadium'
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['location'], "Stadium")
    
    def test_filter_events_by_date(self):
        target_date = (timezone.now().date() + timedelta(days=5)).isoformat()
        url = reverse('event-list') + f'?date={target_date}'
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['date'], target_date)
    
    def test_filter_events_by_category(self):
        url = reverse('event-list') + '?category=music'
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        for event in response.data:
            self.assertEqual(event['category'], "music")
    
    def test_filter_events_multiple_parameters(self):
        target_date = (timezone.now().date() + timedelta(days=20)).isoformat()
        url = reverse('event-list') + f'?location=City Park&date={target_date}&category=music'
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        event = response.data[0]
        self.assertEqual(event['location'], "City Park")
        self.assertEqual(event['category'], "music")
        self.assertEqual(event['date'], target_date)

class EventCancellationTests(APITestSetup):
    def setUp(self):
        super().setUp()
        # Create bookings for the event
        self.booking1 = Booking.objects.create(
            user=self.user,
            event=self.event,
            number_of_tickets=5,
            status='booked'
        )
        self.event.available_tickets -= 5
        self.event.save()
    
    def test_cancel_event_success(self):
        url = reverse('cancel-event', kwargs={'event_id': self.event.id})
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.manager_tokens['access'])
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Event.objects.filter(id=self.event.id).exists())
        self.booking1.refresh_from_db()
        self.assertEqual(self.booking1.status, 'cancelled')
        self.assertEqual(self.event.available_tickets, 100)  # Assuming event is deleted
    
    def test_cancel_event_by_non_manager(self):
        url = reverse('cancel-event', kwargs={'event_id': self.event.id})
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user_tokens['access'])
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_cancel_event_nonexistent_event(self):
        url = reverse('cancel-event', kwargs={'event_id': 999})  # Assuming this ID doesn't exist
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.manager_tokens['access'])
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)