from rest_framework import serializers
from .models import Clinic


class ClinicSerializer(serializers.ModelSerializer):
    """
    Serializer for Clinic model with computed fields.
    """
    doctor_count = serializers.IntegerField(read_only=True)
    full_address = serializers.ReadOnlyField()
    location_display = serializers.ReadOnlyField()
    has_coordinates = serializers.ReadOnlyField()
    
    class Meta:
        model = Clinic
        fields = [
            'id',
            'code',
            'name',
            'slug',
            'clinic_type',
            'email',
            'phone_number',
            'emergency_contact',
            'website',
            'address',
            'city',
            'county',
            'country',
            'postal_code',
            'latitude',
            'longitude',
            'license_number',
            'registration_number',
            'logo',
            'description',
            'status',
            'is_active',
            'established_date',
            'created_at',
            'updated_at',
            # Computed fields
            'doctor_count',
            'full_address',
            'location_display',
            'has_coordinates',
        ]
        read_only_fields = [
            'id',
            'slug',
            'created_at',
            'updated_at',
            'doctor_count',
            'full_address',
            'location_display',
            'has_coordinates',
        ]


class ClinicListSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for list views - fewer fields for better performance.
    """
    doctor_count = serializers.IntegerField(read_only=True)
    full_address = serializers.ReadOnlyField()
    
    class Meta:
        model = Clinic
        fields = [
            'id',
            'code',
            'name',
            'slug',
            'clinic_type',
            'city',
            'county',
            'country',
            'phone_number',
            'status',
            'is_active',
            'logo',
            'doctor_count',
            'full_address',
        ]
        read_only_fields = [
            'id',
            'slug',
            'doctor_count',
            'full_address',
        ]


class ClinicCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for create and update operations.
    Excludes read-only computed fields.
    """
    
    class Meta:
        model = Clinic
        fields = [
            'code',
            'name',
            'clinic_type',
            'email',
            'phone_number',
            'emergency_contact',
            'website',
            'address',
            'city',
            'county',
            'country',
            'postal_code',
            'latitude',
            'longitude',
            'license_number',
            'registration_number',
            'logo',
            'description',
            'status',
            'is_active',
            'established_date',
        ]
        extra_kwargs = {
            'code': {'required': True},
            'name': {'required': True},
        }


class ClinicActivationSerializer(serializers.Serializer):
    """
    Serializer for activation/deactivation operations.
    """
    is_active = serializers.BooleanField(required=True)


class ClinicNearbySerializer(serializers.Serializer):
    """
    Serializer for nearby clinics query parameters.
    """
    latitude = serializers.FloatField(required=True, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=True, min_value=-180, max_value=180)
    radius = serializers.FloatField(required=False, min_value=0.1, max_value=500, default=10)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=100, default=10)
    only_active = serializers.BooleanField(required=False, default=True)