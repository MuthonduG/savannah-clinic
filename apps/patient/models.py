from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from phonenumber_field.modelfields import PhoneNumberField

from apps.clinic.models import Clinic

User = get_user_model()


class Patient(models.Model):
    """
    Stores patient demographic and contact information.
    """

    class Gender(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        OTHER = "OTHER", "Other"

    class BloodGroup(models.TextChoices):
        A_POSITIVE = "A+", "A+"
        A_NEGATIVE = "A-", "A-"
        B_POSITIVE = "B+", "B+"
        B_NEGATIVE = "B-", "B-"
        AB_POSITIVE = "AB+", "AB+"
        AB_NEGATIVE = "AB-", "AB-"
        O_POSITIVE = "O+", "O+"
        O_NEGATIVE = "O-", "O-"

    clinic = models.ForeignKey(
        Clinic,
        on_delete=models.CASCADE,
        related_name="patients",
    )

    patient_number = models.CharField(
        max_length=30,
        unique=True,
    )

    first_name = models.CharField(
        max_length=100,
    )

    last_name = models.CharField(
        max_length=100,
    )

    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
    )

    date_of_birth = models.DateField()

    email = models.EmailField(
        blank=True,
        null=True,
    )

    phone_number = PhoneNumberField()

    national_id = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        unique=True,
    )

    blood_group = models.CharField(
        max_length=3,
        choices=BloodGroup.choices,
        blank=True,
        null=True,
    )

    occupation = models.CharField(
        max_length=100,
        blank=True,
    )

    address = models.TextField(
        blank=True,
    )

    city = models.CharField(
        max_length=100,
        blank=True,
    )

    county = models.CharField(
        max_length=100,
        blank=True,
    )

    country = models.CharField(
        max_length=100,
        default="Kenya",
    )

    postal_code = models.CharField(
        max_length=20,
        blank=True,
    )

    emergency_contact_name = models.CharField(
        max_length=150,
        blank=True,
    )

    emergency_contact_phone = PhoneNumberField(
        blank=True,
        null=True,
    )

    emergency_contact_relationship = models.CharField(
        max_length=100,
        blank=True,
    )

    allergies = models.TextField(
        blank=True,
        help_text="Known allergies.",
    )

    chronic_conditions = models.TextField(
        blank=True,
        help_text="Known chronic illnesses.",
    )

    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text="Weight in kilograms.",
    )

    height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text="Height in centimeters.",
    )

    profile_photo = models.ImageField(
        upload_to="patients/",
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    # Audit fields
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patients_created",
    )

    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patients_updated",
    )

    is_deleted = models.BooleanField(
        default=False,
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patients_deleted",
    )

    class Meta:
        db_table = "patients"
        ordering = ["last_name", "first_name"]
        verbose_name = "Patient"
        verbose_name_plural = "Patients"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        from datetime import date

        today = date.today()

        return (
            today.year
            - self.date_of_birth.year
            - (
                (today.month, today.day)
                < (
                    self.date_of_birth.month,
                    self.date_of_birth.day,
                )
            )
        )

    def __str__(self):
        return f"{self.patient_number} - {self.full_name}"