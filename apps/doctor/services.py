import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone
from phonenumber_field.phonenumber import PhoneNumber

from apps.doctor.models import Doctor, Specialization
from apps.clinic.models import Clinic

logger = logging.getLogger(__name__)
User = get_user_model()


class DoctorServiceError(Exception):
    """Base exception for doctor service errors."""
    pass


class DoctorService:
    """Service layer for Doctor operations with full business logic."""

    # ============ CREATE ============
    
    @staticmethod
    @transaction.atomic
    def create_doctor(
        *,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        clinic: Clinic,
        gender: str,
        date_of_birth: str,
        phone_number: PhoneNumber,
        license_number: str,
        specialization: Specialization,
        qualification: str = "",
        years_of_experience: int = 0,
        employment_type: str = None,
        bio: str = "",
        profile_photo=None,
        is_active: bool = True,
        **kwargs
    ) -> Doctor:
        """
        Create a doctor with a user account.
        
        Args:
            email: Unique email for user account
            password: Secure password (validated)
            first_name: User's first name
            last_name: User's last name
            clinic: Clinic where doctor works
            gender: Doctor's gender
            date_of_birth: Doctor's date of birth
            phone_number: Doctor's phone number
            license_number: Medical license number
            specialization: Doctor's specialization
            qualification: Doctor's qualification (e.g., MBChB)
            years_of_experience: Years of experience
            employment_type: Employment type
            bio: Doctor's biography
            profile_photo: Profile photo image
            is_active: Whether doctor is active
            **kwargs: Additional fields
            
        Returns:
            Doctor: The created doctor instance
            
        Raises:
            ValidationError: If validation fails
            DoctorServiceError: If creation fails
        """
        
        # Normalize and validate
        email = email.strip().lower()
        username = email  # Using email as username
        
        # Validate uniqueness
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError({
                "email": "A user with this email already exists."
            })
        
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError({
                "username": "A user with this username already exists."
            })
        
        if Doctor.objects.filter(license_number__iexact=license_number).exists():
            raise ValidationError({
                "license_number": "A doctor with this license number already exists."
            })
        
        # Validate password
        try:
            validate_password(password)
        except ValidationError as e:
            raise ValidationError({
                "password": e.messages[0] if e.messages else "Invalid password."
            })
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name.strip().title(),
            last_name=last_name.strip().title(),
            is_active=is_active,
        )
        
        # Create doctor
        try:
            doctor = Doctor.objects.create(
                user=user,
                clinic=clinic,
                gender=gender,
                date_of_birth=date_of_birth,
                phone_number=phone_number,
                license_number=license_number.strip(),
                specialization=specialization,
                qualification=qualification.strip() if qualification else "",
                years_of_experience=years_of_experience,
                employment_type=employment_type or Doctor._meta.get_field('employment_type').default,
                bio=bio.strip() if bio else "",
                profile_photo=profile_photo,
                is_active=is_active,
            )
        except Exception as e:
            # Rollback user creation if doctor creation fails
            user.delete()
            logger.error(f"Failed to create doctor: {str(e)}")
            raise DoctorServiceError(f"Failed to create doctor profile: {str(e)}")
        
        # Log success
        logger.info(
            "Doctor created",
            extra={
                "doctor_id": doctor.id,
                "user_id": user.id,
                "email": email,
                "clinic_id": clinic.id,
                "specialization_id": specialization.id,
                "ip_address": kwargs.get("ip_address"),
                "created_by": kwargs.get("created_by"),
            }
        )
        
        return doctor

    # ============ RETRIEVE ============
    
    @staticmethod
    def get_doctor_by_id(doctor_id: int) -> Doctor:
        """Get doctor by ID with optimized query."""
        return Doctor.objects.select_related(
            "user",
            "clinic",
            "specialization"
        ).get(id=doctor_id)
    
    @staticmethod
    def get_doctor_by_email(email: str) -> Doctor:
        """Get doctor by email with optimized query."""
        email = email.strip().lower()
        try:
            user = User.objects.select_related().get(email__iexact=email)
            return Doctor.objects.select_related(
                "user", "clinic", "specialization"
            ).get(user=user)
        except (User.DoesNotExist, Doctor.DoesNotExist):
            return None
    
    @staticmethod
    def get_doctor_by_license(license_number: str) -> Doctor:
        """Get doctor by license number."""
        return Doctor.objects.select_related(
            "user", "clinic", "specialization"
        ).get(license_number__iexact=license_number.strip())
    
    @staticmethod
    def search_doctors(
        *,
        search: str = None,
        clinic: Clinic = None,
        specialization: Specialization = None,
        is_active: bool = None,
        gender: str = None,
        employment_type: str = None,
        min_experience: int = None,
        max_experience: int = None,
        ordering: str = "-created_at",
        limit: int = 20,
        offset: int = 0,
    ) -> QuerySet:
        """
        Search and filter doctors with optimized query.
        
        Returns:
            QuerySet: Filtered doctor queryset
        """
        queryset = Doctor.objects.select_related(
            "user",
            "clinic",
            "specialization"
        ).all()
        
        # Apply filters
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(license_number__icontains=search) |
                Q(specialization__name__icontains=search)
            )
        
        if clinic:
            queryset = queryset.filter(clinic=clinic)
        
        if specialization:
            queryset = queryset.filter(specialization=specialization)
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        
        if gender:
            queryset = queryset.filter(gender=gender)
        
        if employment_type:
            queryset = queryset.filter(employment_type=employment_type)
        
        if min_experience is not None:
            queryset = queryset.filter(years_of_experience__gte=min_experience)
        
        if max_experience is not None:
            queryset = queryset.filter(years_of_experience__lte=max_experience)
        
        # Apply ordering
        allowed_orderings = [
            "first_name", "-first_name",
            "last_name", "-last_name",
            "years_of_experience", "-years_of_experience",
            "created_at", "-created_at",
            "updated_at", "-updated_at",
        ]
        
        if ordering in allowed_orderings:
            if ordering.startswith("-"):
                order_field = ordering[1:]
                if order_field in ["first_name", "last_name"]:
                    ordering = f"user__{order_field}"
            elif ordering in ["first_name", "last_name"]:
                ordering = f"user__{ordering}"
            
            queryset = queryset.order_by(ordering)
        
        # Apply pagination
        if limit > 0:
            queryset = queryset[offset:offset + limit]
        
        return queryset

    # ============ UPDATE ============
    
    @staticmethod
    @transaction.atomic
    def update_doctor(
        doctor: Doctor,
        *,
        first_name: str = None,
        last_name: str = None,
        email: str = None,
        clinic: Clinic = None,
        gender: str = None,
        date_of_birth = None,
        phone_number: PhoneNumber = None,
        specialization: Specialization = None,
        qualification: str = None,
        years_of_experience: int = None,
        employment_type: str = None,
        bio: str = None,
        profile_photo=None,
        is_active: bool = None,
        updated_by: User = None,
    ) -> Doctor:
        """
        Update a doctor and their associated user.
        
        Args:
            doctor: Doctor instance to update
            first_name: Updated first name
            last_name: Updated last name
            email: Updated email
            clinic: Updated clinic
            gender: Updated gender
            date_of_birth: Updated date of birth
            phone_number: Updated phone number
            specialization: Updated specialization
            qualification: Updated qualification
            years_of_experience: Updated years of experience
            employment_type: Updated employment type
            bio: Updated bio
            profile_photo: Updated profile photo
            is_active: Updated active status
            updated_by: User performing the update
            
        Returns:
            Doctor: Updated doctor instance
        """
        user_updated = False
        
        # Update User fields
        if email is not None:
            email = email.strip().lower()
            
            if User.objects.exclude(
                pk=doctor.user.pk
            ).filter(email__iexact=email).exists():
                raise ValidationError({
                    "email": "A user with this email already exists."
                })
            
            doctor.user.email = email
            doctor.user.username = email  # If using email as username
            user_updated = True
        
        if first_name is not None:
            doctor.user.first_name = first_name.strip().title()
            user_updated = True
        
        if last_name is not None:
            doctor.user.last_name = last_name.strip().title()
            user_updated = True
        
        # Save user if updated
        if user_updated:
            try:
                doctor.user.full_clean()
                doctor.user.save(update_fields=["username", "email", "first_name", "last_name"])
            except ValidationError as e:
                raise ValidationError({"user": e.messages})
        
        # Update Doctor fields
        update_fields = []
        
        if clinic is not None:
            doctor.clinic = clinic
            update_fields.append("clinic")
        
        if gender is not None:
            doctor.gender = gender
            update_fields.append("gender")
        
        if date_of_birth is not None:
            doctor.date_of_birth = date_of_birth
            update_fields.append("date_of_birth")
        
        if phone_number is not None:
            doctor.phone_number = phone_number
            update_fields.append("phone_number")
        
        if specialization is not None:
            doctor.specialization = specialization
            update_fields.append("specialization")
        
        if qualification is not None:
            doctor.qualification = qualification.strip() if qualification else ""
            update_fields.append("qualification")
        
        if years_of_experience is not None:
            doctor.years_of_experience = years_of_experience
            update_fields.append("years_of_experience")
        
        if employment_type is not None:
            doctor.employment_type = employment_type
            update_fields.append("employment_type")
        
        if bio is not None:
            doctor.bio = bio.strip() if bio else ""
            update_fields.append("bio")
        
        if profile_photo is not None:
            doctor.profile_photo = profile_photo
            update_fields.append("profile_photo")
        
        if is_active is not None:
            doctor.is_active = is_active
            doctor.user.is_active = is_active
            doctor.user.save(update_fields=["is_active"])
            update_fields.append("is_active")
        
        # Validate and save doctor
        if update_fields:
            try:
                doctor.full_clean()
                doctor.save(update_fields=update_fields)
            except ValidationError as e:
                raise ValidationError({"doctor": e.messages})
        
        # Log update
        logger.info(
            "Doctor updated",
            extra={
                "doctor_id": doctor.id,
                "user_id": doctor.user.id,
                "email": doctor.user.email,
                "updated_by": updated_by.id if updated_by else None,
                "updated_fields": update_fields,
            }
        )
        
        return doctor

    # ============ ACTIVATION / DEACTIVATION ============
    
    @staticmethod
    @transaction.atomic
    def activate_doctor(doctor: Doctor, activated_by: User = None) -> Doctor:
        """Activate a doctor account."""
        if doctor.is_active:
            raise ValidationError("Doctor is already active.")
        
        doctor.is_active = True
        doctor.user.is_active = True
        
        doctor.user.save(update_fields=["is_active"])
        doctor.save(update_fields=["is_active"])
        
        logger.info(
            "Doctor activated",
            extra={
                "doctor_id": doctor.id,
                "user_id": doctor.user.id,
                "activated_by": activated_by.id if activated_by else None,
            }
        )
        
        return doctor
    
    @staticmethod
    @transaction.atomic
    def deactivate_doctor(doctor: Doctor, deactivated_by: User = None) -> Doctor:
        """Deactivate a doctor account."""
        if not doctor.is_active:
            raise ValidationError("Doctor is already inactive.")
        
        doctor.is_active = False
        doctor.user.is_active = False
        
        doctor.user.save(update_fields=["is_active"])
        doctor.save(update_fields=["is_active"])
        
        logger.warning(
            "Doctor deactivated",
            extra={
                "doctor_id": doctor.id,
                "user_id": doctor.user.id,
                "deactivated_by": deactivated_by.id if deactivated_by else None,
            }
        )
        
        return doctor

    # ============ PASSWORD MANAGEMENT ============
    
    @staticmethod
    @transaction.atomic
    def change_password(
        doctor: Doctor,
        old_password: str,
        new_password: str,
    ) -> Doctor:
        """
        Change doctor's password after verifying old password.
        """
        if not doctor.user.check_password(old_password):
            raise ValidationError({
                "old_password": "Current password is incorrect."
            })
        
        return DoctorService.reset_password(doctor, new_password)
    
    @staticmethod
    @transaction.atomic
    def reset_password(
        doctor: Doctor,
        new_password: str,
        reset_by: User = None,
    ) -> Doctor:
        """
        Reset doctor's password (admin only).
        """
        try:
            validate_password(new_password, user=doctor.user)
        except ValidationError as e:
            raise ValidationError({
                "new_password": e.messages[0] if e.messages else "Invalid password."
            })
        
        doctor.user.set_password(new_password)
        doctor.user.save(update_fields=["password"])
        
        logger.warning(
            "Doctor password changed",
            extra={
                "doctor_id": doctor.id,
                "user_id": doctor.user.id,
                "reset_by": reset_by.id if reset_by else None,
            }
        )
        
        return doctor

    # ============ DELETE / ARCHIVE ============
    
    @staticmethod
    @transaction.atomic
    def delete_doctor(doctor: Doctor, deleted_by: User = None) -> None:
        """
        Soft delete or archive a doctor.
        Hard deletion is discouraged in healthcare systems.
        """
        # Check for active appointments
        if hasattr(doctor, 'appointments') and doctor.appointments.filter(
            status__in=['SCHEDULED', 'CONFIRMED'],
            date__gte=timezone.now().date()
        ).exists():
            raise ValidationError(
                "Cannot delete doctor with upcoming appointments."
            )
        
        # Instead of hard delete, deactivate and archive
        doctor.is_active = False
        doctor.user.is_active = False
        
        # Set a flag for archival if you have one
        # doctor.is_archived = True
        
        doctor.user.save(update_fields=["is_active"])
        doctor.save(update_fields=["is_active"])
        
        logger.warning(
            "Doctor archived",
            extra={
                "doctor_id": doctor.id,
                "user_id": doctor.user.id,
                "deleted_by": deleted_by.id if deleted_by else None,
            }
        )

    # ============ BULK OPERATIONS ============
    
    @staticmethod
    @transaction.atomic
    def bulk_activate(doctor_ids: list, activated_by: User = None) -> dict:
        """Bulk activate doctors."""
        doctors = Doctor.objects.filter(id__in=doctor_ids)
        
        if not doctors.exists():
            raise DoctorServiceError("No doctors found to activate.")
        
        updated_count = doctors.update(is_active=True)
        
        # Update associated users
        User.objects.filter(
            id__in=doctors.values_list('user_id', flat=True)
        ).update(is_active=True)
        
        logger.info(
            "Bulk doctor activation",
            extra={
                "doctor_ids": doctor_ids,
                "count": updated_count,
                "activated_by": activated_by.id if activated_by else None,
            }
        )
        
        return {
            "updated_count": updated_count,
            "doctor_ids": list(doctors.values_list('id', flat=True))
        }
    
    @staticmethod
    @transaction.atomic
    def bulk_deactivate(doctor_ids: list, deactivated_by: User = None) -> dict:
        """Bulk deactivate doctors."""
        doctors = Doctor.objects.filter(id__in=doctor_ids)
        
        if not doctors.exists():
            raise DoctorServiceError("No doctors found to deactivate.")
        
        # Check for active appointments
        for doctor in doctors:
            if hasattr(doctor, 'appointments') and doctor.appointments.filter(
                status__in=['SCHEDULED', 'CONFIRMED'],
                date__gte=timezone.now().date()
            ).exists():
                raise ValidationError(
                    f"Doctor {doctor.full_name} has upcoming appointments."
                )
        
        updated_count = doctors.update(is_active=False)
        
        # Update associated users
        User.objects.filter(
            id__in=doctors.values_list('user_id', flat=True)
        ).update(is_active=False)
        
        logger.warning(
            "Bulk doctor deactivation",
            extra={
                "doctor_ids": doctor_ids,
                "count": updated_count,
                "deactivated_by": deactivated_by.id if deactivated_by else None,
            }
        )
        
        return {
            "updated_count": updated_count,
            "doctor_ids": list(doctors.values_list('id', flat=True))
        }
    
    @staticmethod
    @transaction.atomic
    def bulk_change_employment_type(
        doctor_ids: list,
        employment_type: str,
        changed_by: User = None
    ) -> dict:
        """Bulk change employment type."""
        if employment_type not in dict(Doctor._meta.get_field('employment_type').choices):
            raise ValidationError({
                "employment_type": f"Invalid employment type: {employment_type}"
            })
        
        updated_count = Doctor.objects.filter(
            id__in=doctor_ids
        ).update(employment_type=employment_type)
        
        logger.info(
            "Bulk employment type change",
            extra={
                "doctor_ids": doctor_ids,
                "employment_type": employment_type,
                "count": updated_count,
                "changed_by": changed_by.id if changed_by else None,
            }
        )
        
        return {
            "updated_count": updated_count,
            "doctor_ids": doctor_ids,
            "employment_type": employment_type
        }
    
    @staticmethod
    @transaction.atomic
    def bulk_transfer_clinic(
        doctor_ids: list,
        clinic: Clinic,
        transferred_by: User = None
    ) -> dict:
        """Bulk transfer doctors to another clinic."""
        if not clinic:
            raise ValidationError({
                "clinic": "Valid clinic is required."
            })
        
        updated_count = Doctor.objects.filter(
            id__in=doctor_ids
        ).update(clinic=clinic)
        
        logger.info(
            "Bulk clinic transfer",
            extra={
                "doctor_ids": doctor_ids,
                "clinic_id": clinic.id,
                "clinic_name": clinic.name,
                "count": updated_count,
                "transferred_by": transferred_by.id if transferred_by else None,
            }
        )
        
        return {
            "updated_count": updated_count,
            "doctor_ids": doctor_ids,
            "clinic_id": clinic.id,
            "clinic_name": clinic.name
        }

    # ============ STATISTICS ============
    
    @staticmethod
    def get_statistics(clinic: Clinic = None) -> dict:
        """Get doctor statistics."""
        queryset = Doctor.objects.all()
        
        if clinic:
            queryset = queryset.filter(clinic=clinic)
        
        total = queryset.count()
        active = queryset.filter(is_active=True).count()
        inactive = total - active
        
        # Gender breakdown
        male = queryset.filter(gender='MALE').count()
        female = queryset.filter(gender='FEMALE').count()
        other = queryset.filter(gender='OTHER').count()
        
        # Employment type breakdown
        full_time = queryset.filter(employment_type='FULL_TIME').count()
        part_time = queryset.filter(employment_type='PART_TIME').count()
        visiting = queryset.filter(employment_type='VISITING').count()
        
        # Experience distribution
        junior = queryset.filter(years_of_experience__lt=5).count()
        mid = queryset.filter(years_of_experience__gte=5, years_of_experience__lt=10).count()
        senior = queryset.filter(years_of_experience__gte=10, years_of_experience__lt=20).count()
        expert = queryset.filter(years_of_experience__gte=20).count()
        
        return {
            "total": total,
            "active": active,
            "inactive": inactive,
            "gender_distribution": {
                "male": male,
                "female": female,
                "other": other,
            },
            "employment_type_distribution": {
                "full_time": full_time,
                "part_time": part_time,
                "visiting": visiting,
            },
            "experience_levels": {
                "junior": junior,
                "mid_level": mid,
                "senior": senior,
                "expert": expert,
            }
        }

    # ============ VALIDATION HELPERS ============
    
    @staticmethod
    def validate_doctor_data(
        *,
        email: str = None,
        license_number: str = None,
        exclude_doctor: Doctor = None,
    ) -> dict:
        """Validate doctor data for uniqueness."""
        errors = {}
        
        if email:
            email = email.strip().lower()
            qs = User.objects.filter(email__iexact=email)
            if exclude_doctor and exclude_doctor.user:
                qs = qs.exclude(pk=exclude_doctor.user.pk)
            
            if qs.exists():
                errors["email"] = "A user with this email already exists."
        
        if license_number:
            license_number = license_number.strip()
            qs = Doctor.objects.filter(license_number__iexact=license_number)
            if exclude_doctor:
                qs = qs.exclude(pk=exclude_doctor.pk)
            
            if qs.exists():
                errors["license_number"] = "A doctor with this license number already exists."
        
        if errors:
            raise ValidationError(errors)
        
        return {"email": email, "license_number": license_number}