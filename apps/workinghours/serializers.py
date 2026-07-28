from rest_framework import serializers
from django.core.exceptions import ValidationError
from .models import WorkingHours
from apps.doctor.models import Doctor


class WorkingHoursSerializer(serializers.ModelSerializer):
    """
    Full serializer for Working Hours with validation.
    """
    doctor_name = serializers.SerializerMethodField()
    day_display = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkingHours
        fields = [
            'id',
            'doctor',
            'doctor_name',
            'day_of_week',
            'day_display',
            'start_time',
            'end_time',
            'slot_duration',
            'is_available',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'doctor_name',
            'day_display',
            'created_at',
            'updated_at',
        ]
    
    def get_doctor_name(self, obj):
        """Get the doctor's full name."""
        return obj.doctor.full_name if obj.doctor else None
    
    def get_day_display(self, obj):
        """Get the human-readable day name."""
        return obj.get_day_of_week_display()
    
    def validate(self, data):
        """
        Cross-field validation.
        """
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError({
                "end_time": "End time must be after start time."
            })
        
        # Check for overlapping working hours for the same doctor
        doctor = data.get('doctor')
        day_of_week = data.get('day_of_week')
        
        if doctor and day_of_week:
            instance = self.instance
            overlapping = WorkingHours.objects.filter(
                doctor=doctor,
                day_of_week=day_of_week,
                is_available=True
            )
            
            if instance:
                overlapping = overlapping.exclude(id=instance.id)
            
            # Check if the time range overlaps with existing entries
            for existing in overlapping:
                if (start_time < existing.end_time and end_time > existing.start_time):
                    raise serializers.ValidationError({
                        "start_time": f"This time overlaps with existing working hours ({existing.start_time.strftime('%H:%M')} - {existing.end_time.strftime('%H:%M')})"
                    })
        
        return data


class WorkingHoursListSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for list views.
    """
    doctor_name = serializers.SerializerMethodField()
    day_display = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkingHours
        fields = [
            'id',
            'doctor',
            'doctor_name',
            'day_of_week',
            'day_display',
            'start_time',
            'end_time',
            'slot_duration',
            'is_available',
        ]
    
    def get_doctor_name(self, obj):
        return obj.doctor.full_name if obj.doctor else None
    
    def get_day_display(self, obj):
        return obj.get_day_of_week_display()


class WorkingHoursCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for create and update operations.
    """
    
    class Meta:
        model = WorkingHours
        fields = [
            'doctor',
            'day_of_week',
            'start_time',
            'end_time',
            'slot_duration',
            'is_available',
        ]
        extra_kwargs = {
            'doctor': {'required': True},
            'day_of_week': {'required': True},
            'start_time': {'required': True},
            'end_time': {'required': True},
        }
    
    def validate(self, data):
        """
        Cross-field validation.
        """
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError({
                "end_time": "End time must be after start time."
            })
        
        # Check for overlapping working hours
        doctor = data.get('doctor')
        day_of_week = data.get('day_of_week')
        
        if doctor and day_of_week:
            instance = self.instance
            overlapping = WorkingHours.objects.filter(
                doctor=doctor,
                day_of_week=day_of_week,
                is_available=True
            )
            
            if instance:
                overlapping = overlapping.exclude(id=instance.id)
            
            for existing in overlapping:
                if (start_time < existing.end_time and end_time > existing.start_time):
                    raise serializers.ValidationError({
                        "start_time": f"This time overlaps with existing working hours ({existing.start_time.strftime('%H:%M')} - {existing.end_time.strftime('%H:%M')})"
                    })
        
        return data


class WorkingHoursBulkCreateSerializer(serializers.Serializer):
    """
    Serializer for bulk creation of working hours.
    """
    doctor_id = serializers.IntegerField(required=True)
    working_hours = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        required=True
    )
    
    def validate_doctor_id(self, value):
        """Validate that the doctor exists."""
        try:
            doctor = Doctor.objects.get(id=value)
            return doctor
        except Doctor.DoesNotExist:
            raise serializers.ValidationError(f"Doctor with ID {value} does not exist.")
    
    def validate_working_hours(self, value):
        """Validate each working hour entry."""
        for entry in value:
            # Check required fields
            required_fields = ['day_of_week', 'start_time', 'end_time']
            for field in required_fields:
                if field not in entry:
                    raise serializers.ValidationError(f"'{field}' is required for each working hour entry.")
            
            # Validate day_of_week
            valid_days = [choice[0] for choice in WorkingHours.Days.choices]
            if entry['day_of_week'] not in valid_days:
                raise serializers.ValidationError(
                    f"Invalid day_of_week: {entry['day_of_week']}. Must be one of: {', '.join(valid_days)}"
                )
        
        return value


class WorkingHoursFilterSerializer(serializers.Serializer):
    """
    Serializer for filtering working hours.
    """
    doctor_id = serializers.IntegerField(required=False)
    day_of_week = serializers.ChoiceField(
        choices=WorkingHours.Days.choices,
        required=False
    )
    is_available = serializers.BooleanField(required=False)