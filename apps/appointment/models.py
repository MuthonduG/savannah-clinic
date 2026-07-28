from django.db import models
from django.contrib.auth import get_user_model
from apps.doctor.models import Doctor
from apps.patient.models import Patient

User = get_user_model()


class Appointment(models.Model):
    """
    Appointment model with booking logic.
    """

    class Status(models.TextChoices):
        BOOKED = "BOOKED", "Booked"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"
        NO_SHOW = "NO_SHOW", "No Show"

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.PROTECT,
        related_name="appointments",
        db_index=True,
    )

    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="appointments",
        db_index=True,
    )

    appointment_date = models.DateField(db_index=True)

    start_time = models.TimeField()

    slot_duration = models.PositiveSmallIntegerField(
        default=30,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.BOOKED,
        db_index=True,
    )

    cancellation_reason = models.TextField(
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "appointments"
        ordering = ["appointment_date", "start_time"]
        indexes = [
            models.Index(fields=['doctor', 'appointment_date', 'status']),
            models.Index(fields=['patient', 'appointment_date']),
            models.Index(fields=['appointment_date', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "doctor",
                    "appointment_date",
                    "start_time",
                ],
                condition=models.Q(status="BOOKED"),
                name="unique_active_doctor_slot",
            )
        ]

    def __str__(self):
        return (
            f"{self.patient} -> {self.doctor} "
            f"{self.appointment_date} "
            f"{self.start_time}"
        )