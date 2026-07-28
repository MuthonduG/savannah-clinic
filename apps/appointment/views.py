import logging
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import LimitOffsetPagination
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from .models import Appointment
from .serializers import (
    AppointmentSerializer,
    AppointmentCreateSerializer,
    AppointmentCancelSerializer,
    AppointmentRescheduleSerializer,
    AvailabilitySerializer,
    PatientAppointmentSerializer,
)
from .services import AppointmentService, AppointmentServiceError
from apps.doctor.models import Doctor
from apps.patient.models import Patient

logger = logging.getLogger(__name__)


class AppointmentViewSet(viewsets.ModelViewSet):
    """
    Appointment ViewSet with booking logic.
    """
    
    authentication_classes = [JWTAuthentication]
    pagination_class = LimitOffsetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['doctor', 'patient', 'status']
    search_fields = ['doctor__user__first_name', 'doctor__user__last_name', 'patient__first_name', 'patient__last_name']
    ordering_fields = ['appointment_date', 'start_time', 'created_at']
    ordering = ['appointment_date', 'start_time']
    
    def get_queryset(self):
        return Appointment.objects.select_related(
            'doctor',
            'doctor__user',
            'patient'
        ).all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AppointmentCreateSerializer
        elif self.action == 'cancel':
            return AppointmentCancelSerializer
        elif self.action == 'reschedule':
            return AppointmentRescheduleSerializer
        return AppointmentSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    # ============ Exception Handlers ============
    
    def handle_validation_error(self, e):
        return Response(
            {'errors': e.message_dict if hasattr(e, 'message_dict') else str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    def handle_service_error(self, e, action="operation"):
        logger.error(f"Appointment {action} error: {str(e)}", exc_info=True)
        return Response(
            {'detail': f'Failed to {action}. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    def handle_not_found(self, detail="Appointment not found."):
        return Response(
            {'detail': detail},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # ============ CRUD Operations ============
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            return self.handle_service_error(e, "list appointments")
    
    def create(self, request, *args, **kwargs):
        """
        Book an appointment.
        POST /api/appointments/
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            appointment = AppointmentService.book_appointment(
                doctor=serializer.validated_data['doctor'],
                patient=serializer.validated_data['patient'],
                appointment_date=serializer.validated_data['appointment_date'],
                start_time=serializer.validated_data['start_time'],
                notes=serializer.validated_data.get('notes', ''),
                created_by=request.user,
            )
            
            response_serializer = AppointmentSerializer(appointment)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except AppointmentServiceError as e:
            return self.handle_service_error(e, "book appointment")
    
    def retrieve(self, request, *args, **kwargs):
        try:
            appointment = AppointmentService.get_appointment_by_id(kwargs["pk"])
            if not appointment:
                return self.handle_not_found()
            serializer = self.get_serializer(appointment)
            return Response(serializer.data)
        except AppointmentServiceError as e:
            return self.handle_service_error(e, "retrieve appointment")
    
    # ============ Custom Actions ============
    
    @action(detail=True, methods=['patch'], url_path='cancel')
    def cancel(self, request, pk=None):
        """
        Cancel an appointment.
        PATCH /api/appointments/{id}/cancel/
        Body: {"cancellation_reason": "Patient can't make it"}
        """
        appointment = AppointmentService.get_appointment_by_id(pk)
        if not appointment:
            return self.handle_not_found()
        
        serializer = AppointmentCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            cancelled_appointment = AppointmentService.cancel_appointment(
                appointment=appointment,
                cancellation_reason=serializer.validated_data.get('cancellation_reason', ''),
                cancelled_by=request.user,
            )
            
            response_serializer = AppointmentSerializer(cancelled_appointment)
            return Response(
                {
                    'detail': 'Appointment cancelled successfully.',
                    'data': response_serializer.data
                },
                status=status.HTTP_200_OK
            )
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except AppointmentServiceError as e:
            return self.handle_service_error(e, "cancel appointment")
    
    @action(detail=True, methods=['patch'], url_path='reschedule')
    def reschedule(self, request, pk=None):
        """
        Reschedule an appointment.
        PATCH /api/appointments/{id}/reschedule/
        Body: {"appointment_date": "2026-08-01", "start_time": "10:00:00"}
        """
        appointment = AppointmentService.get_appointment_by_id(pk)
        if not appointment:
            return self.handle_not_found()
        
        serializer = AppointmentRescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            rescheduled_appointment = AppointmentService.reschedule_appointment(
                appointment=appointment,
                new_date=serializer.validated_data['appointment_date'],
                new_time=serializer.validated_data['start_time'],
                rescheduled_by=request.user,
            )
            
            response_serializer = AppointmentSerializer(rescheduled_appointment)
            return Response(
                {
                    'detail': 'Appointment rescheduled successfully.',
                    'data': response_serializer.data
                },
                status=status.HTTP_200_OK
            )
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except AppointmentServiceError as e:
            return self.handle_service_error(e, "reschedule appointment")


class DoctorAvailabilityView(viewsets.GenericViewSet):
    """
    Get available slots for a doctor.
    GET /api/doctors/{id}/availability/?date=2026-08-01
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    
    def list(self, request, doctor_id=None):
        """
        Get available slots for a doctor on a specific date.
        """
        date_str = request.query_params.get('date')
        
        if not date_str:
            return Response(
                {'errors': {'date': 'Date parameter is required.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'errors': {'date': 'Invalid date format. Use YYYY-MM-DD.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            doctor = Doctor.objects.get(id=doctor_id, is_active=True)
        except Doctor.DoesNotExist:
            return Response(
                {'detail': 'Doctor not found or inactive.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            available_slots = AppointmentService.get_available_slots(doctor_id, appointment_date)
            
            return Response({
                'doctor': doctor_id,
                'doctor_name': doctor.full_name,
                'date': appointment_date.strftime('%Y-%m-%d'),
                'available_slots': available_slots,
                'total_slots': len(available_slots),
            }, status=status.HTTP_200_OK)
            
        except AppointmentServiceError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PatientAppointmentsView(viewsets.GenericViewSet):
    """
    Get upcoming appointments for a patient.
    GET /api/patients/{id}/appointments/
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def list(self, request, patient_id=None):
        """
        Get upcoming appointments for a patient.
        """
        try:
            patient = Patient.objects.get(id=patient_id, is_active=True)
        except Patient.DoesNotExist:
            return Response(
                {'detail': 'Patient not found or inactive.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            appointments = AppointmentService.get_upcoming_patient_appointments(patient_id)
            
            serializer = PatientAppointmentSerializer(appointments, many=True)
            return Response({
                'patient': patient_id,
                'patient_name': patient.full_name,
                'appointments': serializer.data,
                'total': len(serializer.data),
            }, status=status.HTTP_200_OK)
            
        except AppointmentServiceError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )