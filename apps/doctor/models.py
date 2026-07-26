from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.urls import reverse
from phonenumber_field.modelfields import PhoneNumberField
from apps.clinic.models import Clinic
from datetime import date

User = get_user_model()


class Gender(models.TextChoices):
    MALE = "MALE", "Male"
    FEMALE = "FEMALE", "Female"
    OTHER = "OTHER", "Other"


class EmploymentType(models.TextChoices):
    FULL_TIME = "FULL_TIME", "Full Time"
    PART_TIME = "PART_TIME", "Part Time"
    VISITING = "VISITING", "Visiting Consultant"


class Specialization(models.Model):
    """Lookup table for medical specializations."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ["name"]
        verbose_name = "Specialization"
        verbose_name_plural = "Specializations"
    
    def __str__(self):
        return self.name


class Doctor(models.Model):
    """
    Represents a doctor practicing at a clinic.
    Authentication data is stored in the User model.
    """
    
    # Link to Django's User model (authentication)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="doctor_profile",
    )
    
    # Clinic relationship
    clinic = models.ForeignKey(
        Clinic,
        on_delete=models.PROTECT,  # Prevent accidental deletion
        related_name="doctors",
    )
    
    # Doctor-specific information (only what's NOT in User)
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
    )
    
    date_of_birth = models.DateField(
        validators=[
            MinValueValidator(
                limit_value=date(1900, 1, 1),
                message="Date of birth cannot be before 1900"
            )
        ]
    )
    
    phone_number = PhoneNumberField(region="KE")  # International phone number
    
    license_number = models.CharField(
        max_length=100,
        unique=True,
        help_text="Medical board registration/license number",
    )
    
    specialization = models.ForeignKey(
        Specialization,
        on_delete=models.PROTECT,
        related_name="doctors",
        help_text="Medical specialization",
    )
    
    qualification = models.CharField(
        max_length=150,
        blank=True,
        help_text="e.g. MBChB, MD, BDS",
    )
    
    years_of_experience = models.PositiveIntegerField(default=0)
    
    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME,
    )
    
    bio = models.TextField(blank=True)
    
    profile_photo = models.ImageField(
        upload_to="doctors/",
        blank=True,
        null=True,
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether this doctor is currently practicing"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["user__last_name", "user__first_name"]
        indexes = [
            models.Index(fields=["specialization"]),
            models.Index(fields=["clinic"]),
            models.Index(fields=["is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["license_number", "clinic"],
                name="unique_license_per_clinic"
            ),
        ]
    
    def __str__(self):
        return f"Dr. {self.full_name} ({self.specialization})"
    
    def get_absolute_url(self):
        return reverse("doctor-detail", kwargs={"pk": self.pk})
    
    # Properties that delegate to User model
    @property
    def first_name(self):
        """Get first name from associated User."""
        return self.user.first_name
    
    @property
    def last_name(self):
        """Get last name from associated User."""
        return self.user.last_name
    
    @property
    def full_name(self):
        """Get full name from associated User."""
        return self.user.get_full_name()
    
    @property
    def full_name_with_title(self):
        """Get full name with Dr. prefix."""
        return f"Dr. {self.full_name}"
    
    @property
    def email(self):
        """Get email from associated User."""
        return self.user.email
    
    @property
    def age(self):
        """Calculate age from date of birth."""
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    
    def clean(self):
        """Validate model fields."""
        super().clean()
        
        # Validate age
        if self.date_of_birth:
            age = self.age
            if age is not None:
                if age < 18:
                    raise ValidationError(
                        {"date_of_birth": "Doctor must be at least 18 years old"}
                    )
                if age > 100:
                    raise ValidationError(
                        {"date_of_birth": "Invalid date of birth"}
                    )
        
        # Validate that user exists
        if not self.user_id:
            raise ValidationError(
                {"user": "Doctor must be associated with a User account"}
            )
    
    def save(self, *args, **kwargs):
        """Validate before saving."""
        self.full_clean()
        super().save(*args, **kwargs)