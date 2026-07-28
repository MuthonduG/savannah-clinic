import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date, time, timedelta
from django.db import transaction
from django.db.models import Q, QuerySet
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from .models import Appointment
from apps.doctor.models import Doctor
from apps.patient.models import Patient
from apps.workinghours.models import WorkingHours

logger = logging.getLogger(__name__)
User = get_user_model()


class AppointmentServiceError(Exception):
    """Base exception for appointment service errors."""
    pass


class AppointmentService:
    """Service layer for Appointment operations with full business logic."""

    SLOT_DURATION = 30  # minutes

    @staticmethod
    def validate_working_hours(doctor: Doctor, appointment_date: date, start_time: time) -> bool:
        """
        Validate that the appointment falls within the doctor's working hours.
        """
        day_of_week = appointment_date.strftime('%A').upper()
        
        # Get working hours for this doctor on this day
        working_hours = WorkingHours.objects.filter(
            doctor=doctor,
            day_of_week=day_of_week,
            is_available=True
        ).first()
        
        if not working_hours:
            raise ValidationError(
                f"Doctor does not work on {appointment_date.strftime('%A')}."
            )
        
        # Check if start time is within working hours
        if start_time < working_hours.start_time or start_time >= working_hours.end_time:
            raise ValidationError(
                f"Doctor's working hours on {appointment_date.strftime('%A')} are "
                f"{working_hours.start_time.strftime('%H:%M')} to "
                f"{working_hours.end_time.strftime('%H:%M')}."
            )
        
        # Check if slot fits within working hours (30-minute increments)
        slot_end = (datetime.combine(date.today(), start_time) + 
                   timedelta(minutes=AppointmentService.SLOT_DURATION)).time()
        
        if slot_end > working_hours.end_time:
            raise ValidationError(
                f"The slot must end within working hours "
                f"({working_hours.start_time.strftime('%H:%M')} to "
                f"{working_hours.end_time.strftime('%H:%M')})."
            )
        
        return True

    @staticmethod
    def validate_slot_not_taken(doctor: Doctor, appointment_date: date, start_time: time) -> bool:
        """
        Validate that the slot is not already booked.
        """
        if Appointment.objects.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            start_time=start_time,
            status=Appointment.Status.BOOKED
        ).exists():
            raise ValidationError("This slot is already booked.")
        
        return True

    @staticmethod
    def validate_future_booking(appointment_date: date, start_time: time) -> bool:
        """
        Validate that the appointment is at least 1 hour in the future.
        """
        now = datetime.now()
        appointment_datetime = datetime.combine(appointment_date, start_time)
        
        if appointment_datetime < now + timedelta(hours=1):
            raise ValidationError(
                "Appointments must be booked at least 1 hour in advance."
            )
        
        return True

    @staticmethod
    def generate_slots(working_hours: WorkingHours) -> List[time]:
        """
        Generate all 30-minute slots within working hours.
        """
        slots = []
        current_time = working_hours.start_time
        
        while current_time < working_hours.end_time:
            slots.append(current_time)
            # Add 30 minutes
            current_time = (datetime.combine(date.today(), current_time) + 
                          timedelta(minutes=AppointmentService.SLOT_DURATION)).time()
        
        return slots

    @staticmethod
    def get_available_slots(doctor_id: int, appointment_date: date) -> List[Dict[str, Any]]:
        """
        Get all available slots for a doctor on a specific date.
        """
        try:
            doctor = Doctor.objects.get(id=doctor_id, is_active=True)
        except Doctor.DoesNotExist:
            raise AppointmentServiceError("Doctor not found or inactive.")
        
        day_of_week = appointment_date.strftime('%A').upper()
        
        # Get working hours
        working_hours = WorkingHours.objects.filter(
            doctor=doctor,
            day_of_week=day_of_week,
            is_available=True
        ).first()
        
        if not working_hours:
            return []
        
        # Generate all possible slots
        all_slots = AppointmentService.generate_slots(working_hours)
        
        # Get booked slots
        booked_slots = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            status=Appointment.Status.BOOKED
        ).values_list('start_time', flat=True)
        
        booked_times = set(booked_slots)
        
        # Filter out booked slots
        available_slots = [
            {
                'start_time': slot.strftime('%H:%M'),
                'end_time': (datetime.combine(date.today(), slot) + 
                           timedelta(minutes=AppointmentService.SLOT_DURATION)).strftime('%H:%M'),
                'slot_duration': AppointmentService.SLOT_DURATION,
            }
            for slot in all_slots
            if slot not in booked_times
        ]
        
        return available_slots

    @staticmethod
    @transaction.atomic
    def book_appointment(
        *,
        doctor: Doctor,
        patient: Patient,
        appointment_date: date,
        start_time: time,
        notes: str = "",
        created_by: Optional[User] = None,
    ) -> Appointment:
        """
        Book a new appointment with full validation.
        """
        # Validate doctor and patient
        if not doctor.is_active:
            raise ValidationError("This doctor is not active.")
        
        if not patient.is_active:
            raise ValidationError("This patient is not active.")
        
        # Validate future booking (at least 1 hour ahead)
        AppointmentService.validate_future_booking(appointment_date, start_time)
        
        # Validate working hours
        AppointmentService.validate_working_hours(doctor, appointment_date, start_time)
        
        # Validate slot not taken (with lock for concurrency)
        # Use select_for_update to lock the row for concurrent requests
        existing_appointment = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            start_time=start_time,
            status=Appointment.Status.BOOKED
        ).select_for_update().first()
        
        if existing_appointment:
            raise ValidationError("This slot is already booked.")
        
        # Create appointment
        try:
            appointment = Appointment.objects.create(
                doctor=doctor,
                patient=patient,
                appointment_date=appointment_date,
                start_time=start_time,
                slot_duration=AppointmentService.SLOT_DURATION,
                status=Appointment.Status.BOOKED,
                notes=notes or "",
            )
            
            logger.info(
                f"Appointment booked: {appointment.id} "
                f"Doctor: {doctor.full_name}, Patient: {patient.full_name} "
                f"on {appointment_date} at {start_time}"
            )
            
            return appointment
            
        except Exception as e:
            logger.error(f"Failed to book appointment: {str(e)}", exc_info=True)
            raise AppointmentServiceError(f"Failed to book appointment: {str(e)}")

    @staticmethod
    @transaction.atomic
    def cancel_appointment(
        appointment: Appointment,
        cancellation_reason: str = "",
        cancelled_by: Optional[User] = None,
    ) -> Appointment:
        """
        Cancel an appointment.
        """
        if appointment.status == Appointment.Status.CANCELLED:
            raise ValidationError("This appointment is already cancelled.")
        
        if appointment.status == Appointment.Status.COMPLETED:
            raise ValidationError("Cannot cancel a completed appointment.")
        
        appointment.status = Appointment.Status.CANCELLED
        appointment.cancellation_reason = cancellation_reason or ""
        appointment.save(update_fields=['status', 'cancellation_reason'])
        
        logger.info(
            f"Appointment cancelled: {appointment.id} "
            f"Doctor: {appointment.doctor.full_name}, "
            f"Patient: {appointment.patient.full_name} "
            f"Reason: {cancellation_reason or 'No reason provided'}"
        )
        
        return appointment

    @staticmethod
    @transaction.atomic
    def reschedule_appointment(
        appointment: Appointment,
        new_date: date,
        new_time: time,
        rescheduled_by: Optional[User] = None,
    ) -> Appointment:
        """
        Reschedule an appointment to a new slot.
        """
        if appointment.status == Appointment.Status.CANCELLED:
            raise ValidationError("Cannot reschedule a cancelled appointment.")
        
        if appointment.status == Appointment.Status.COMPLETED:
            raise ValidationError("Cannot reschedule a completed appointment.")
        
        # Validate new slot
        AppointmentService.validate_future_booking(new_date, new_time)
        AppointmentService.validate_working_hours(
            appointment.doctor, new_date, new_time
        )
        AppointmentService.validate_slot_not_taken(
            appointment.doctor, new_date, new_time
        )
        
        # Update appointment
        old_date = appointment.appointment_date
        old_time = appointment.start_time
        
        appointment.appointment_date = new_date
        appointment.start_time = new_time
        appointment.save(update_fields=['appointment_date', 'start_time'])
        
        logger.info(
            f"Appointment rescheduled: {appointment.id} "
            f"From {old_date} at {old_time} "
            f"To {new_date} at {new_time}"
        )
        
        return appointment

    @staticmethod
    def get_upcoming_patient_appointments(patient_id: int) -> QuerySet[Appointment]:
        """
        Get upcoming appointments for a patient, sorted by date.
        """
        from datetime import date, datetime
        
        today = date.today()
        now = datetime.now().time()
        
        # Get future appointments (date > today) or (date == today and time > now)
        return Appointment.objects.filter(
            patient_id=patient_id,
            status=Appointment.Status.BOOKED
        ).filter(
            Q(appointment_date__gt=today) |
            Q(appointment_date=today, start_time__gt=now)
        ).select_related(
            'doctor',
            'doctor__user',
            'patient'
        ).order_by('appointment_date', 'start_time')

    @staticmethod
    def get_appointment_by_id(appointment_id: int) -> Optional[Appointment]:
        """Get appointment by ID."""
        try:
            return Appointment.objects.select_related(
                'doctor',
                'doctor__user',
                'patient'
            ).get(id=appointment_id)
        except Appointment.DoesNotExist:
            return None

    @staticmethod
    def search_appointments(
        *,
        doctor_id: Optional[int] = None,
        patient_id: Optional[int] = None,
        status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        ordering: str = "appointment_date,start_time",
    ) -> QuerySet[Appointment]:
        """
        Search and filter appointments.
        """
        queryset = Appointment.objects.select_related(
            'doctor',
            'doctor__user',
            'patient'
        )
        
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        
        if status:
            queryset = queryset.filter(status=status)
        
        if date_from:
            queryset = queryset.filter(appointment_date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(appointment_date__lte=date_to)
        
        if ordering:
            queryset = queryset.order_by(ordering)
        
        return queryset