from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from phonenumber_field.serializerfields import PhoneNumberField

from apps.clinic.models import Clinic
from apps.clinic.serializers import ClinicSerializer
from .models import Doctor, Specialization, Gender, EmploymentType

User = get_user_model()


class SpecializationSerializer(serializers.ModelSerializer):
    """Serializer for medical specializations."""
    
    class Meta:
        model = Specialization
        fields = [
            "id",
            "name",
            "description",
        ]
        read_only_fields = ["id"]


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
        ]
        read_only_fields = ["id"]


class ClinicMiniSerializer(serializers.ModelSerializer):
    """Minimal Clinic serializer for nested display."""
    
    class Meta:
        model = Clinic
        fields = [
            "id",
            "name",
            "address",
            "phone_number",
        ]
        read_only_fields = ["id"]


class DoctorListSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for list endpoints.
    Returns only the most commonly needed fields.
    """
    
    full_name = serializers.SerializerMethodField()
    specialization = SpecializationSerializer(read_only=True)
    clinic = ClinicMiniSerializer(read_only=True)
    
    class Meta:
        model = Doctor
        fields = [
            "id",
            "full_name",
            "specialization",
            "clinic",
            "phone_number",
            "is_active",
            "profile_photo",
        ]
        read_only_fields = ["id", "full_name"]
    
    def get_full_name(self, obj):
        return obj.full_name


class DoctorDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for single doctor views.
    Includes nested clinic and specialization details plus computed fields.
    """
    
    # Nested user serializer
    user = UserSerializer(read_only=True)
    
    # Computed fields using SerializerMethodField for flexibility
    full_name = serializers.SerializerMethodField()
    full_name_with_title = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    
    # Nested related fields
    specialization = SpecializationSerializer(read_only=True)
    clinic = ClinicSerializer(read_only=True)
    
    # Human-readable choices
    gender_display = serializers.CharField(
        source="get_gender_display",
        read_only=True
    )
    employment_type_display = serializers.CharField(
        source="get_employment_type_display",
        read_only=True
    )
    
    class Meta:
        model = Doctor
        fields = [
            # Identification
            "id",
            "user",
            
            # Personal info (from User via nested serializer)
            "full_name",
            "full_name_with_title",
            
            # Clinic
            "clinic",
            
            # Personal info (from Doctor)
            "gender",
            "gender_display",
            "date_of_birth",
            "age",
            "phone_number",
            
            # Professional info
            "license_number",
            "specialization",
            "qualification",
            "years_of_experience",
            "employment_type",
            "employment_type_display",
            
            # Additional
            "bio",
            "profile_photo",
            "is_active",
            
            # Timestamps
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "full_name",
            "full_name_with_title",
            "age",
            "created_at",
            "updated_at",
            "gender_display",
            "employment_type_display",
        ]
    
    def get_full_name(self, obj):
        return obj.full_name
    
    def get_full_name_with_title(self, obj):
        return obj.full_name_with_title
    
    def get_age(self, obj):
        return obj.age


class DoctorCreateSerializer(serializers.ModelSerializer):
    """
    Creates both User and Doctor in a single transaction.
    Uses ModelSerializer with write-only user fields.
    """
    
    # User fields (write-only)
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    
    # Doctor fields with enhanced validation
    phone_number = PhoneNumberField()
    
    class Meta:
        model = Doctor
        fields = (
            # User fields (write-only)
            "username",
            "password",
            "first_name",
            "last_name",
            "email",
            
            # Doctor fields
            "clinic",
            "gender",
            "date_of_birth",
            "phone_number",
            "license_number",
            "specialization",
            "qualification",
            "years_of_experience",
            "employment_type",
            "bio",
            "profile_photo",
            "is_active",
        )
    
    def validate_username(self, value):
        """Validate username is unique (case-insensitive)."""
        if User.objects.filter(username__iexact=value).exists():
            raise ValidationError("A user with this username already exists.")
        return value
    
    def validate_email(self, value):
        """Validate email is unique (case-insensitive)."""
        if User.objects.filter(email__iexact=value).exists():
            raise ValidationError("A user with this email already exists.")
        return value
    
    def validate_license_number(self, value):
        """Validate license number is unique."""
        if Doctor.objects.filter(license_number__iexact=value).exists():
            raise ValidationError("This license number is already registered.")
        return value
    
    def validate_date_of_birth(self, value):
        """Validate date of birth is reasonable."""
        from datetime import date
        today = date.today()
        age = today.year - value.year - (
            (today.month, today.day) < (value.month, value.day)
        )
        
        if age < 18:
            raise ValidationError("Doctor must be at least 18 years old.")
        if age > 100:
            raise ValidationError("Invalid date of birth.")
        
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        """Create User and Doctor in a single transaction."""
        
        # Create user
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
        )
        
        # Remove user fields before creating doctor
        user_fields = ["username", "password", "first_name", "last_name", "email"]
        for field in user_fields:
            validated_data.pop(field, None)
        
        # Create doctor
        doctor = Doctor.objects.create(
            user=user,
            **validated_data
        )
        
        return doctor
    
    def to_representation(self, instance):
        """Return detailed representation after creation."""
        return DoctorDetailSerializer(instance).data


class DoctorUpdateSerializer(serializers.ModelSerializer):
    """
    Updates both User and Doctor fields.
    Handles partial updates with proper validation.
    """
    
    # User fields that can be updated
    first_name = serializers.CharField(
        source="user.first_name",
        required=False
    )
    last_name = serializers.CharField(
        source="user.last_name",
        required=False
    )
    email = serializers.EmailField(
        source="user.email",
        required=False
    )
    
    # Enhanced validation
    phone_number = PhoneNumberField(required=False)
    
    class Meta:
        model = Doctor
        fields = [
            # User fields
            "first_name",
            "last_name",
            "email",
            # Doctor fields
            "clinic",
            "gender",
            "date_of_birth",
            "phone_number",
            # License number removed from editable fields
            "specialization",
            "qualification",
            "years_of_experience",
            "employment_type",
            "bio",
            "profile_photo",
            "is_active",
        ]
    
    def validate_email(self, value):
        """Validate email is unique (case-insensitive, excluding current user)."""
        if self.instance and self.instance.user:
            if User.objects.exclude(
                pk=self.instance.user.pk
            ).filter(email__iexact=value).exists():
                raise ValidationError("A user with this email already exists.")
        return value
    
    @transaction.atomic
    def update(self, instance, validated_data):
        """Update both User and Doctor."""
        
        # Update User fields
        user_data = validated_data.pop("user", {})
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        
        if user_data:
            instance.user.save()
        
        # Update Doctor fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        return instance
    
    def to_representation(self, instance):
        """Return detailed representation after update."""
        return DoctorDetailSerializer(instance).data


class DoctorChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for changing doctor's password.
    Requires current password verification and Django's password validators.
    """
    
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )
    confirm_password = serializers.CharField(write_only=True)
    
    def validate_current_password(self, value):
        """Verify current password."""
        user = self.context.get("request").user
        if not user.check_password(value):
            raise ValidationError("Current password is incorrect.")
        return value
    
    def validate(self, data):
        """Check that new password matches confirmation."""
        if data["new_password"] != data["confirm_password"]:
            raise ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return data
    
    def save(self, **kwargs):
        """Change the user's password."""
        user = self.context.get("request").user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user


class DoctorBulkUpdateSerializer(serializers.Serializer):
    """
    Serializer for bulk operations like changing employment type
    or activating/deactivating multiple doctors.
    """
    
    doctor_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    is_active = serializers.BooleanField(required=False)
    employment_type = serializers.ChoiceField(
        choices=EmploymentType.choices,
        required=False
    )
    
    def validate_doctor_ids(self, value):
        """Ensure all doctors exist."""
        existing_ids = set(
            Doctor.objects.filter(id__in=value).values_list("id", flat=True)
        )
        missing_ids = set(value) - existing_ids
        
        if missing_ids:
            raise ValidationError(
                f"Doctor(s) with IDs {list(missing_ids)} do not exist."
            )
        
        return value
    
    def validate(self, data):
        """Ensure at least one field to update is provided."""
        if "is_active" not in data and "employment_type" not in data:
            raise ValidationError(
                "At least one of 'is_active' or 'employment_type' must be provided."
            )
        return data
    
    @transaction.atomic
    def save(self):
        """Perform bulk update and return result."""
        doctor_ids = self.validated_data["doctor_ids"]
        
        # Prepare update data
        update_data = {}
        if "is_active" in self.validated_data:
            update_data["is_active"] = self.validated_data["is_active"]
        if "employment_type" in self.validated_data:
            update_data["employment_type"] = self.validated_data["employment_type"]
        
        if update_data:
            updated_count = Doctor.objects.filter(
                id__in=doctor_ids
            ).update(**update_data)
            return {
                "updated_count": updated_count,
                "doctor_ids": doctor_ids
            }
        return {"updated_count": 0, "doctor_ids": []}


class DoctorSearchSerializer(serializers.Serializer):
    """
    Serializer for doctor search/filtering with ordering support.
    """
    
    search = serializers.CharField(required=False, allow_blank=True)
    specialization = serializers.PrimaryKeyRelatedField(
        queryset=Specialization.objects.all(),
        required=False
    )
    clinic = serializers.PrimaryKeyRelatedField(
        queryset=Clinic.objects.all(),
        required=False
    )
    is_active = serializers.BooleanField(required=False)
    gender = serializers.ChoiceField(
        choices=Gender.choices,
        required=False
    )
    employment_type = serializers.ChoiceField(
        choices=EmploymentType.choices,
        required=False
    )
    min_experience = serializers.IntegerField(
        min_value=0,
        required=False
    )
    max_experience = serializers.IntegerField(
        min_value=0,
        required=False
    )
    ordering = serializers.ChoiceField(
        choices=[
            "first_name",
            "-first_name",
            "last_name",
            "-last_name",
            "years_of_experience",
            "-years_of_experience",
            "created_at",
            "-created_at",
            "updated_at",
            "-updated_at",
        ],
        required=False,
        default="-created_at"
    )
    limit = serializers.IntegerField(
        min_value=1,
        max_value=100,
        required=False,
        default=20
    )
    offset = serializers.IntegerField(
        min_value=0,
        required=False,
        default=0
    )
    
    def validate(self, data):
        """Validate min/max experience combination."""
        min_exp = data.get("min_experience")
        max_exp = data.get("max_experience")
        
        if min_exp is not None and max_exp is not None and min_exp > max_exp:
            raise ValidationError(
                "Minimum experience cannot be greater than maximum experience."
            )
        
        return data


class DoctorBulkTransferSerializer(serializers.Serializer):
    """
    Serializer for bulk transfer of doctors to another clinic.
    """
    doctor_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    clinic_id = serializers.PrimaryKeyRelatedField(
        queryset=Clinic.objects.all(),
        source='clinic'
    )
    
    def validate_doctor_ids(self, value):
        """Ensure all doctors exist and are active."""
        doctors = Doctor.objects.filter(id__in=value)
        if doctors.count() != len(value):
            existing_ids = set(doctors.values_list('id', flat=True))
            missing_ids = set(value) - existing_ids
            raise serializers.ValidationError(
                f"Doctor(s) with IDs {list(missing_ids)} do not exist."
            )
        return value