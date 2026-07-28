import logging
from typing import Optional, List, Dict, Any
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet
from django.contrib.auth import get_user_model

from .models import Patient
from apps.clinic.models import Clinic

logger = logging.getLogger(__name__)
User = get_user_model()


class PatientServiceError(Exception):
    """Base exception for patient service errors."""
    pass


class PatientService:
    """Service layer for Patient operations."""

    @staticmethod
    def generate_patient_number(clinic: Clinic) -> str:
        """
        Generate a unique patient number.
        Format: CLN-{clinic_id}-{sequential_number}
        """
        last_patient = Patient.objects.filter(clinic=clinic).order_by('-id').first()
        if last_patient:
            # Extract the number from the last patient number
            parts = last_patient.patient_number.split('-')
            if len(parts) == 3:
                try:
                    last_num = int(parts[2])
                    new_num = last_num + 1
                except ValueError:
                    new_num = 1
            else:
                new_num = 1
        else:
            new_num = 1
        
        return f"CLN-{clinic.id}-{new_num:04d}"

    @staticmethod
    @transaction.atomic
    def create_patient(
        *,
        clinic: Clinic,
        first_name: str,
        last_name: str,
        gender: str,
        date_of_birth,
        phone_number,
        created_by: Optional[User] = None,
        **kwargs
    ) -> Patient:
        """
        Create a new patient.
        """
        try:
            # Generate patient number
            patient_number = PatientService.generate_patient_number(clinic)
            
            # Create patient
            patient = Patient.objects.create(
                clinic=clinic,
                patient_number=patient_number,
                first_name=first_name.strip().title(),
                last_name=last_name.strip().title(),
                gender=gender,
                date_of_birth=date_of_birth,
                phone_number=phone_number,
                created_by=created_by,
                **kwargs
            )
            
            logger.info(
                f"Patient created: {patient.full_name} (ID: {patient.id}) "
                f"by {created_by.email if created_by else 'System'}"
            )
            
            return patient
            
        except Exception as e:
            logger.error(f"Failed to create patient: {str(e)}", exc_info=True)
            raise PatientServiceError(f"Failed to create patient: {str(e)}")

    @staticmethod
    def get_patient_by_id(patient_id: int) -> Optional[Patient]:
        """Get patient by ID."""
        try:
            return Patient.objects.select_related('clinic').get(id=patient_id)
        except Patient.DoesNotExist:
            return None

    @staticmethod
    def get_patient_by_number(patient_number: str) -> Optional[Patient]:
        """Get patient by patient number."""
        try:
            return Patient.objects.select_related('clinic').get(patient_number=patient_number)
        except Patient.DoesNotExist:
            return None

    @staticmethod
    def search_patients(
        *,
        search: Optional[str] = None,
        clinic_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        gender: Optional[str] = None,
        ordering: str = "last_name",
    ) -> QuerySet[Patient]:
        """
        Search and filter patients.
        """
        queryset = Patient.objects.select_related('clinic')
        
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(patient_number__icontains=search) |
                Q(phone_number__icontains=search) |
                Q(email__icontains=search) |
                Q(national_id__icontains=search)
            )
        
        if clinic_id:
            queryset = queryset.filter(clinic_id=clinic_id)
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        
        if gender:
            queryset = queryset.filter(gender=gender)
        
        queryset = queryset.order_by(ordering)
        return queryset

    @staticmethod
    @transaction.atomic
    def update_patient(
        patient: Patient,
        updated_by: Optional[User] = None,
        **validated_data
    ) -> Patient:
        """
        Update a patient.
        """
        try:
            for key, value in validated_data.items():
                if hasattr(patient, key):
                    setattr(patient, key, value)
            
            patient.updated_by = updated_by
            patient.save()
            
            logger.info(
                f"Patient updated: {patient.full_name} (ID: {patient.id}) "
                f"by {updated_by.email if updated_by else 'System'}"
            )
            
            return patient
            
        except Exception as e:
            logger.error(f"Failed to update patient {patient.id}: {str(e)}", exc_info=True)
            raise PatientServiceError(f"Failed to update patient: {str(e)}")

    @staticmethod
    @transaction.atomic
    def archive_patient(patient: Patient, archived_by: Optional[User] = None) -> None:
        """Soft delete a patient."""
        patient.is_deleted = True
        patient.is_active = False
        patient.deleted_by = archived_by
        patient.save(update_fields=['is_deleted', 'is_active', 'deleted_by'])
        
        logger.info(
            f"Patient archived: {patient.full_name} (ID: {patient.id}) "
            f"by {archived_by.email if archived_by else 'System'}"
        )