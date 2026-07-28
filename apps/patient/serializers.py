from rest_framework import serializers
from phonenumber_field.serializerfields import PhoneNumberField
from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    """
    Full patient serializer with all fields.
    """
    full_name = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    
    class Meta:
        model = Patient
        fields = [
            'id',
            'clinic',
            'patient_number',
            'first_name',
            'last_name',
            'full_name',
            'gender',
            'date_of_birth',
            'age',
            'email',
            'phone_number',
            'national_id',
            'blood_group',
            'occupation',
            'address',
            'city',
            'county',
            'country',
            'postal_code',
            'emergency_contact_name',
            'emergency_contact_phone',
            'emergency_contact_relationship',
            'allergies',
            'chronic_conditions',
            'weight',
            'height',
            'profile_photo',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'patient_number', 'created_at', 'updated_at', 'full_name', 'age']


class PatientListSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for list views.
    """
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Patient
        fields = [
            'id',
            'patient_number',
            'first_name',
            'last_name',
            'full_name',
            'gender',
            'phone_number',
            'email',
            'is_active',
        ]
        read_only_fields = ['id', 'patient_number', 'full_name']


class PatientCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating patients.
    """
    phone_number = PhoneNumberField()
    emergency_contact_phone = PhoneNumberField(required=False, allow_null=True)
    
    class Meta:
        model = Patient
        fields = [
            'clinic',
            'first_name',
            'last_name',
            'gender',
            'date_of_birth',
            'email',
            'phone_number',
            'national_id',
            'blood_group',
            'occupation',
            'address',
            'city',
            'county',
            'country',
            'postal_code',
            'emergency_contact_name',
            'emergency_contact_phone',
            'emergency_contact_relationship',
            'allergies',
            'chronic_conditions',
            'weight',
            'height',
            'profile_photo',
            'is_active',
        ]
    
    def validate_email(self, value):
        """Validate email uniqueness."""
        if value:
            if Patient.objects.filter(email=value).exists():
                raise serializers.ValidationError("A patient with this email already exists.")
        return value
    
    def validate_national_id(self, value):
        """Validate national ID uniqueness."""
        if value:
            if Patient.objects.filter(national_id=value).exists():
                raise serializers.ValidationError("A patient with this national ID already exists.")
        return value
    
    def validate_phone_number(self, value):
        """Validate phone number."""
        if not value:
            raise serializers.ValidationError("Phone number is required.")
        return value