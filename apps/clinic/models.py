from django.db import models
from django.core.validators import RegexValidator
from django.utils.text import slugify


def generate_unique_slug(model, value, slug_field="slug"):
    """
    Generate a unique slug for any Django model.

    Example:
        Clinic Name      -> clinic-name
        Clinic Name      -> clinic-name-1
        Clinic Name      -> clinic-name-2
    """
    slug = slugify(value)

    if not slug:
        slug = "clinic"

    unique_slug = slug
    counter = 1

    while model.objects.filter(**{slug_field: unique_slug}).exists():
        unique_slug = f"{slug}-{counter}"
        counter += 1

    return unique_slug


class Clinic(models.Model):

    CLINIC_TYPES = [
        ("hospital", "Hospital"),
        ("clinic", "Clinic"),
        ("dispensary", "Dispensary"),
        ("health_center", "Health Center"),
        ("medical_center", "Medical Center"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("closed", "Closed"),
    ]

    code = models.CharField(
        max_length=20,
        unique=True
    )

    name = models.CharField(
        max_length=255,
        unique=True
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True
    )

    clinic_type = models.CharField(
        max_length=30,
        choices=CLINIC_TYPES,
        default="clinic"
    )

    email = models.EmailField(
        unique=True,
        blank=True,
        null=True
    )

    phone_number = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r"^\+?[0-9]{9,15}$",
                message="Enter a valid phone number."
            )
        ],
        blank=True,
        null=True
    )

    emergency_contact = models.CharField(
        max_length=20,
        blank=True
    )

    website = models.URLField(
        blank=True
    )

    address = models.TextField(
        blank=True
    )

    city = models.CharField(
        max_length=100,
        blank=True
    )

    county = models.CharField(
        max_length=100,
        blank=True
    )

    country = models.CharField(
        max_length=100,
        default="Kenya"
    )

    postal_code = models.CharField(
        max_length=20,
        blank=True
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    license_number = models.CharField(
        max_length=100,
        blank=True
    )

    registration_number = models.CharField(
        max_length=100,
        blank=True
    )

    logo = models.ImageField(
        upload_to="clinics/logos/",
        blank=True,
        null=True
    )

    description = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active"
    )

    is_active = models.BooleanField(
        default=True
    )

    established_date = models.DateField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "clinic"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Automatically generate a unique slug when creating
        a clinic or when the slug is empty.
        """
        if not self.slug:
            self.slug = generate_unique_slug(
                Clinic,
                self.name,
                slug_field="slug"
            )

        super().save(*args, **kwargs)

    # RENAMED: Avoids conflict with annotation
    @property
    def total_active_doctors(self):
        """
        Returns the number of active doctors in the clinic.
        Use this for single clinic instances.
        """
        return self.doctors.filter(is_active=True).count()

    @property
    def active_doctors_list(self):
        """
        Returns only active doctors.
        """
        return self.doctors.filter(is_active=True)

    @property
    def full_address(self):
        """
        Returns a formatted clinic address.
        """
        parts = [
            self.address,
            self.city,
            self.county,
            self.country,
        ]
        return ", ".join(filter(None, parts))