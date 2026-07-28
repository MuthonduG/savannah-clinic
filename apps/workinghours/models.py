from django.db import models

from apps.common.models import BaseModel
from apps.doctor.models import Doctor


class WorkingHours(BaseModel):
    """
    Weekly recurring working schedule for a doctor.
    """

    class Days(models.TextChoices):
        MONDAY = "MONDAY", "Monday"
        TUESDAY = "TUESDAY", "Tuesday"
        WEDNESDAY = "WEDNESDAY", "Wednesday"
        THURSDAY = "THURSDAY", "Thursday"
        FRIDAY = "FRIDAY", "Friday"
        SATURDAY = "SATURDAY", "Saturday"
        SUNDAY = "SUNDAY", "Sunday"

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="working_hours",
    )

    day_of_week = models.CharField(
        max_length=10,
        choices=Days.choices,
    )

    start_time = models.TimeField()

    end_time = models.TimeField()

    slot_duration = models.PositiveIntegerField(
        default=30,
        help_text="Appointment duration in minutes."
    )

    is_available = models.BooleanField(
        default=True,
        help_text="Whether the doctor normally works on this day."
    )

    class Meta:
        db_table = "working_hours"
        verbose_name = "Working Hours"
        verbose_name_plural = "Working Hours"

        ordering = [
            "doctor",
            "day_of_week",
            "start_time",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "doctor",
                    "day_of_week",
                    "start_time",
                ],
                name="unique_doctor_working_period",
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.start_time >= self.end_time:
            raise ValidationError(
                {
                    "end_time": "End time must be after start time."
                }
            )

    def __str__(self):
        return (
            f"{self.doctor} - "
            f"{self.day_of_week} "
            f"{self.start_time.strftime('%H:%M')} - "
            f"{self.end_time.strftime('%H:%M')}"
        )