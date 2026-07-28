from rest_framework import serializers
from datetime import datetime, time, timedelta
from .models import Appointment
from apps.doctor.models import Doctor
from apps.patient.models import Patient


class AppointmentSerializer(serializers.ModelSerializer):
    """
    Full appointment serializer.
    """
    doctor_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = [
            'id',
            'doctor',
            'doctor_name',
            'patient',
            'patient_name',
            'appointment_date',
            'start_time',
            'slot_duration',
            'status',
            'status_display',
            'cancellation_reason',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'doctor_name', 'patient_name', 'status_display']
    
    def get_doctor_name(self, obj):
        return obj.doctor.full_name if obj.doctor else None
    
    def get_patient_name(self, obj):
        return obj.patient.full_name if obj.patient else None
    
    def get_status_display(self, obj):
        return obj.get_status_display()


class AppointmentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for booking appointments.
    """
    class Meta:
        model = Appointment
        fields = [
            'doctor',
            'patient',
            'appointment_date',
            'start_time',
            'notes',
        ]
    
    def validate_doctor(self, value):
        """Validate doctor exists and is active."""
        if not value.is_active:
            raise serializers.ValidationError("This doctor is not active.")
        return value
    
    def validate_patient(self, value):
        """Validate patient exists and is active."""
        if not value.is_active:
            raise serializers.ValidationError("This patient is not active.")
        return value
    
    def validate_appointment_date(self, value):
        """Validate appointment date is not in the past."""
        from datetime import date
        if value < date.today():
            raise serializers.ValidationError("Appointment date cannot be in the past.")
        return value
    
    def validate(self, data):
        """
        Additional validation that requires multiple fields.
        """
        from datetime import datetime, timedelta
        
        appointment_date = data.get('appointment_date')
        start_time = data.get('start_time')
        doctor = data.get('doctor')
        
        # Check if appointment is at least 1 hour from now
        now = datetime.now()
        appointment_datetime = datetime.combine(appointment_date, start_time)
        if appointment_datetime < now + timedelta(hours=1):
            raise serializers.ValidationError(
                "Appointments must be booked at least 1 hour in advance."
            )
        
        return data


class AppointmentCancelSerializer(serializers.Serializer):
    """
    Serializer for cancelling appointments.
    """
    cancellation_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Reason for cancellation"
    )


class AppointmentRescheduleSerializer(serializers.Serializer):
    """
    Serializer for rescheduling appointments.
    """
    appointment_date = serializers.DateField(required=True)
    start_time = serializers.TimeField(required=True)
    
    def validate_appointment_date(self, value):
        """Validate appointment date is not in the past."""
        from datetime import date
        if value < date.today():
            raise serializers.ValidationError("Appointment date cannot be in the past.")
        return value
    
    def validate(self, data):
        """
        Validate the new slot.
        """
        from datetime import datetime, timedelta
        
        appointment_date = data.get('appointment_date')
        start_time = data.get('start_time')
        
        # Check if appointment is at least 1 hour from now
        now = datetime.now()
        appointment_datetime = datetime.combine(appointment_date, start_time)
        if appointment_datetime < now + timedelta(hours=1):
            raise serializers.ValidationError(
                "Appointments must be rescheduled at least 1 hour in advance."
            )
        
        return data


class AvailabilitySerializer(serializers.Serializer):
    """
    Serializer for availability responses.
    """
    doctor = serializers.IntegerField()
    date = serializers.DateField()
    available_slots = serializers.ListField(
        child=serializers.CharField()
    )


class PatientAppointmentSerializer(serializers.ModelSerializer):
    """
    Serializer for patient's upcoming appointments.
    """
    doctor_name = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = [
            'id',
            'doctor',
            'doctor_name',
            'appointment_date',
            'start_time',
            'slot_duration',
            'status',
            'status_display',
            'notes',
        ]
        read_only_fields = ['id', 'doctor_name', 'status_display']
    
    def get_doctor_name(self, obj):
        return obj.doctor.full_name if obj.doctor else None
    
    def get_status_display(self, obj):
        return obj.get_status_display()