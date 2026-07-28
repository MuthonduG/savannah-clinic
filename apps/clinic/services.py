import logging
from math import radians, sin, cos, asin, sqrt
from typing import Optional, List, Dict, Any
from django.db.models import QuerySet
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from django.db.models import Q, Count, Avg
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from .models import Clinic, generate_unique_slug

logger = logging.getLogger(__name__)
User = get_user_model()


class ClinicServiceError(Exception):
    """Base exception for clinic service errors."""
    pass


# ============ VALIDATION HELPERS ============

def validate_coordinates(latitude: Optional[float], longitude: Optional[float]) -> None:
    """Validate geographic coordinates."""
    if latitude is not None and (latitude < -90 or latitude > 90):
        raise ValidationError({
            "latitude": "Latitude must be between -90 and 90 degrees."
        })
    
    if longitude is not None and (longitude < -180 or longitude > 180):
        raise ValidationError({
            "longitude": "Longitude must be between -180 and 180 degrees."
        })


def validate_clinic_type(clinic_type: str) -> None:
    """Validate clinic type."""
    valid_types = dict(Clinic.CLINIC_TYPES).keys()
    if clinic_type not in valid_types:
        raise ValidationError({
            "clinic_type": f"Invalid clinic type. Must be one of: {', '.join(valid_types)}"
        })


def validate_status(status: str) -> None:
    """Validate clinic status."""
    valid_statuses = dict(Clinic.STATUS_CHOICES).keys()
    if status not in valid_statuses:
        raise ValidationError({
            "status": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        })


class ClinicService:
    """Service layer for Clinic operations with full business logic."""

    # ============ CREATE ============
    
    @staticmethod
    @transaction.atomic
    def create_clinic(
        *,
        code: str,
        name: str,
        clinic_type: str = "clinic",
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        website: str = "",
        address: str = "",
        city: str = "",
        county: str = "",
        country: str = "Kenya",
        postal_code: str = "",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        license_number: str = "",
        registration_number: str = "",
        established_date=None,
        logo=None,
        description: str = "",
        emergency_contact: str = "",
        status: str = "active",
        is_active: bool = True,
        created_by: Optional[User] = None,
        **kwargs
    ) -> Clinic:
        """
        Create a new clinic.
        """
        # Normalize data
        code = code.strip().upper()
        name = name.strip().title()
        email = email.strip().lower() if email else None
        
        # Generate slug using the helper function
        slug = generate_unique_slug(Clinic, name)
        
        # Validate clinic type
        validate_clinic_type(clinic_type)
        
        # Validate status
        validate_status(status)
        
        # Validate coordinates
        validate_coordinates(latitude, longitude)
        
        # Create clinic - let database enforce uniqueness
        try:
            clinic = Clinic.objects.create(
                code=code,
                name=name,
                slug=slug,
                clinic_type=clinic_type,
                email=email,
                phone_number=phone_number,
                website=website.strip() if website else "",
                address=address.strip() if address else "",
                city=city.strip() if city else "",
                county=county.strip() if county else "",
                country=country.strip() if country else "Kenya",
                postal_code=postal_code.strip() if postal_code else "",
                latitude=latitude,
                longitude=longitude,
                license_number=license_number.strip() if license_number else "",
                registration_number=registration_number.strip() if registration_number else "",
                established_date=established_date,
                logo=logo,
                description=description.strip() if description else "",
                emergency_contact=emergency_contact.strip() if emergency_contact else "",
                status=status,
                is_active=is_active,
            )
        except IntegrityError as e:
            # Handle unique constraint violations
            error_msg = str(e).lower()
            if 'code' in error_msg:
                raise ValidationError({"code": f"Clinic with code '{code}' already exists."})
            elif 'name' in error_msg:
                raise ValidationError({"name": f"Clinic with name '{name}' already exists."})
            elif 'email' in error_msg:
                raise ValidationError({"email": f"Clinic with email '{email}' already exists."})
            elif 'slug' in error_msg:
                raise ValidationError({"slug": "Unable to generate unique slug."})
            else:
                logger.error(f"Integrity error creating clinic: {str(e)}")
                raise ClinicServiceError(f"Failed to create clinic: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to create clinic: {str(e)}")
            raise ClinicServiceError(f"Failed to create clinic: {str(e)}")
        
        # Log success - FIXED: use clinic_name instead of name
        logger.info(
            "Clinic created",
            extra={
                "clinic_id": clinic.id,
                "clinic_code": code,  # Changed from "code"
                "clinic_name": name,  # Changed from "name"
                "clinic_slug": slug,  # Changed from "slug"
                "clinic_type": clinic_type,
                "created_by": created_by.id if created_by else None,
                "ip_address": kwargs.get("ip_address"),
            }
        )
        
        return clinic

    # ============ RETRIEVE ============
    
    @staticmethod
    def get_clinic_by_id(clinic_id: int, prefetch_doctors: bool = False) -> Optional[Clinic]:
        """Get clinic by ID."""
        try:
            queryset = Clinic.objects
            if prefetch_doctors:
                queryset = queryset.prefetch_related('doctors')
            return queryset.get(pk=clinic_id)
        except Clinic.DoesNotExist:
            return None
    
    @staticmethod
    def get_clinic_by_code(code: str) -> Optional[Clinic]:
        """Get clinic by code."""
        try:
            return Clinic.objects.get(code__iexact=code.strip().upper())
        except Clinic.DoesNotExist:
            return None
    
    @staticmethod
    def get_clinic_by_slug(slug: str) -> Optional[Clinic]:
        """Get clinic by slug."""
        try:
            return Clinic.objects.get(slug=slug)
        except Clinic.DoesNotExist:
            return None
    
    @staticmethod
    def get_clinic_by_name(name: str) -> Optional[Clinic]:
        """Get clinic by name."""
        try:
            return Clinic.objects.get(name__iexact=name.strip().title())
        except Clinic.DoesNotExist:
            return None
    
    @staticmethod
    def search_clinics(
        *,
        search: Optional[str] = None,
        clinic_type: Optional[str] = None,
        status: Optional[str] = None,
        city: Optional[str] = None,
        county: Optional[str] = None,
        country: Optional[str] = None,
        is_active: Optional[bool] = None,
        has_coordinates: Optional[bool] = None,
        min_doctors: Optional[int] = None,
        max_doctors: Optional[int] = None,
        ordering: str = "name",
    ) -> QuerySet[Clinic]:
        """
        Search and filter clinics with optimized query.
        """
        # Annotate with doctor_count
        queryset = Clinic.objects.annotate(
            doctor_count=Count('doctors', filter=Q(doctors__is_active=True))
        )
        
        # Apply filters
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(slug__icontains=search) |
                Q(address__icontains=search) |
                Q(city__icontains=search) |
                Q(county__icontains=search) |
                Q(email__icontains=search) |
                Q(phone_number__icontains=search) |
                Q(description__icontains=search)
            )
        
        if clinic_type:
            queryset = queryset.filter(clinic_type=clinic_type)
        
        if status:
            queryset = queryset.filter(status=status)
        
        if city:
            queryset = queryset.filter(city__icontains=city)
        
        if county:
            queryset = queryset.filter(county__icontains=county)
        
        if country:
            queryset = queryset.filter(country__icontains=country)
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        
        if has_coordinates is not None:
            if has_coordinates:
                queryset = queryset.filter(
                    latitude__isnull=False,
                    longitude__isnull=False
                )
            else:
                queryset = queryset.filter(
                    Q(latitude__isnull=True) | Q(longitude__isnull=True)
                )
        
        if min_doctors is not None:
            queryset = queryset.filter(doctor_count__gte=min_doctors)
        
        if max_doctors is not None:
            queryset = queryset.filter(doctor_count__lte=max_doctors)
        
        # Apply ordering
        allowed_orderings = [
            "name", "-name",
            "code", "-code",
            "city", "-city",
            "county", "-county",
            "created_at", "-created_at",
            "updated_at", "-updated_at",
            "clinic_type", "-clinic_type",
            "status", "-status",
            "doctor_count", "-doctor_count",
        ]
        
        if ordering in allowed_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("name")
        
        return queryset

    # ============ UPDATE ============
    
    @staticmethod
    @transaction.atomic
    def update_clinic(
        clinic: Clinic,
        *,
        code: Optional[str] = None,
        name: Optional[str] = None,
        clinic_type: Optional[str] = None,
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        website: Optional[str] = None,
        address: Optional[str] = None,
        city: Optional[str] = None,
        county: Optional[str] = None,
        country: Optional[str] = None,
        postal_code: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        license_number: Optional[str] = None,
        registration_number: Optional[str] = None,
        established_date=None,
        logo=None,
        description: Optional[str] = None,
        emergency_contact: Optional[str] = None,
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
        updated_by: Optional[User] = None,
    ) -> Clinic:
        """
        Update a clinic.
        """
        update_fields = set()
        
        # Update fields with validation
        if code is not None:
            code = code.strip().upper()
            clinic.code = code
            update_fields.add("code")
        
        if name is not None:
            name = name.strip().title()
            new_slug = generate_unique_slug(Clinic, name)
            clinic.name = name
            clinic.slug = new_slug
            update_fields.add("name")
            update_fields.add("slug")
        
        if clinic_type is not None:
            validate_clinic_type(clinic_type)
            clinic.clinic_type = clinic_type
            update_fields.add("clinic_type")
        
        if email is not None:
            email = email.strip().lower() if email else None
            clinic.email = email
            update_fields.add("email")
        
        if phone_number is not None:
            clinic.phone_number = phone_number
            update_fields.add("phone_number")
        
        if website is not None:
            clinic.website = website.strip() if website else ""
            update_fields.add("website")
        
        if address is not None:
            clinic.address = address.strip() if address else ""
            update_fields.add("address")
        
        if city is not None:
            clinic.city = city.strip() if city else ""
            update_fields.add("city")
        
        if county is not None:
            clinic.county = county.strip() if county else ""
            update_fields.add("county")
        
        if country is not None:
            clinic.country = country.strip() if country else "Kenya"
            update_fields.add("country")
        
        if postal_code is not None:
            clinic.postal_code = postal_code.strip() if postal_code else ""
            update_fields.add("postal_code")
        
        if latitude is not None:
            validate_coordinates(latitude, longitude if longitude is not None else clinic.longitude)
            clinic.latitude = latitude
            update_fields.add("latitude")
        
        if longitude is not None:
            validate_coordinates(latitude if latitude is not None else clinic.latitude, longitude)
            clinic.longitude = longitude
            update_fields.add("longitude")
        
        if license_number is not None:
            clinic.license_number = license_number.strip() if license_number else ""
            update_fields.add("license_number")
        
        if registration_number is not None:
            clinic.registration_number = registration_number.strip() if registration_number else ""
            update_fields.add("registration_number")
        
        if established_date is not None:
            clinic.established_date = established_date
            update_fields.add("established_date")
        
        if logo is not None:
            clinic.logo = logo
            update_fields.add("logo")
        
        if description is not None:
            clinic.description = description.strip() if description else ""
            update_fields.add("description")
        
        if emergency_contact is not None:
            clinic.emergency_contact = emergency_contact.strip() if emergency_contact else ""
            update_fields.add("emergency_contact")
        
        if status is not None:
            validate_status(status)
            clinic.status = status
            update_fields.add("status")
            
            if status == "active":
                clinic.is_active = True
                update_fields.add("is_active")
            elif status in ["inactive", "closed"]:
                clinic.is_active = False
                update_fields.add("is_active")
        
        if is_active is not None:
            clinic.is_active = is_active
            update_fields.add("is_active")
            if is_active and clinic.status != "active":
                clinic.status = "active"
                update_fields.add("status")
            elif not is_active and clinic.status == "active":
                clinic.status = "inactive"
                update_fields.add("status")
        
        # Validate and save
        if update_fields:
            try:
                clinic.full_clean()
                clinic.save(update_fields=list(update_fields))
            except IntegrityError as e:
                error_msg = str(e).lower()
                if 'code' in error_msg:
                    raise ValidationError({"code": f"Clinic with code '{code}' already exists."})
                elif 'name' in error_msg:
                    raise ValidationError({"name": f"Clinic with name '{name}' already exists."})
                elif 'email' in error_msg:
                    raise ValidationError({"email": f"Clinic with email '{email}' already exists."})
                else:
                    raise ValidationError({"clinic": "Database integrity error occurred."})
            except ValidationError as e:
                raise ValidationError({"clinic": e.messages})
        
        # Log update - FIXED: use clinic_name instead of name
        logger.info(
            "Clinic updated",
            extra={
                "clinic_id": clinic.id,
                "clinic_code": clinic.code,  # Changed from "code"
                "clinic_name": clinic.name,  # Changed from "name"
                "updated_by": updated_by.id if updated_by else None,
                "updated_fields": list(update_fields),
            }
        )
        
        return clinic

    # ============ ACTIVATION / DEACTIVATION ============
    
    @staticmethod
    @transaction.atomic
    def activate_clinic(clinic: Clinic, activated_by: Optional[User] = None) -> Clinic:
        """Activate a clinic."""
        if clinic.is_active:
            raise ValidationError("Clinic is already active.")
        
        clinic.is_active = True
        clinic.status = "active"
        
        clinic.save(update_fields=["is_active", "status"])
        
        # FIXED: use clinic_name instead of name
        logger.info(
            "Clinic activated",
            extra={
                "clinic_id": clinic.id,
                "clinic_name": clinic.name,  # Changed from "name"
                "activated_by": activated_by.id if activated_by else None,
            }
        )
        
        return clinic
    
    @staticmethod
    @transaction.atomic
    def deactivate_clinic(clinic: Clinic, deactivated_by: Optional[User] = None) -> Clinic:
        """Deactivate a clinic."""
        if not clinic.is_active:
            raise ValidationError("Clinic is already inactive.")
        
        # Check if clinic has active doctors
        if clinic.doctors.filter(is_active=True).exists():
            active_doctor_count = clinic.doctors.filter(is_active=True).count()
            raise ValidationError(
                f"Cannot deactivate clinic. It has {active_doctor_count} active doctor(s). "
                "Please deactivate all doctors first."
            )
        
        clinic.is_active = False
        clinic.status = "inactive"
        
        clinic.save(update_fields=["is_active", "status"])
        
        # FIXED: use clinic_name instead of name
        logger.warning(
            "Clinic deactivated",
            extra={
                "clinic_id": clinic.id,
                "clinic_name": clinic.name,  # Changed from "name"
                "deactivated_by": deactivated_by.id if deactivated_by else None,
            }
        )
        
        return clinic

    # ============ ARCHIVE ============
    
    @staticmethod
    @transaction.atomic
    def archive_clinic(clinic: Clinic, archived_by: Optional[User] = None) -> None:
        """
        Soft delete/archive a clinic.
        Hard deletion is discouraged in healthcare systems.
        """
        # Check for active doctors
        if clinic.doctors.filter(is_active=True).exists():
            active_doctors = clinic.doctors.filter(is_active=True)
            doctor_names = [d.full_name for d in active_doctors[:5]]
            count = active_doctors.count()
            raise ValidationError(
                f"Cannot archive clinic. It has {count} active doctor(s): {', '.join(doctor_names)}"
            )
        
        # Soft delete
        clinic.is_active = False
        clinic.status = "closed"
        
        clinic.save(update_fields=["is_active", "status"])
        
        # FIXED: use clinic_name instead of name
        logger.warning(
            "Clinic archived",
            extra={
                "clinic_id": clinic.id,
                "clinic_name": clinic.name,  # Changed from "name"
                "archived_by": archived_by.id if archived_by else None,
            }
        )

    # ============ STATISTICS ============
    
    @staticmethod
    def get_statistics() -> Dict[str, Any]:
        """Get clinic statistics using optimized queries."""
        counts = Clinic.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
            inactive=Count('id', filter=Q(is_active=False)),
        )
        
        type_stats = dict(
            Clinic.objects.values('clinic_type')
            .annotate(count=Count('id'))
            .values_list('clinic_type', 'count')
        )
        
        status_stats = dict(
            Clinic.objects.values('status')
            .annotate(count=Count('id'))
            .values_list('status', 'count')
        )
        
        counties = list(
            Clinic.objects.values('county')
            .annotate(count=Count('id'))
            .filter(county__isnull=False)
            .exclude(county='')
            .order_by('-count')[:10]
        )
        
        cities = list(
            Clinic.objects.values('city')
            .annotate(count=Count('id'))
            .filter(city__isnull=False)
            .exclude(city='')
            .order_by('-count')[:10]
        )
        
        avg_doctors = Clinic.objects.annotate(
            doctor_count=Count('doctors', filter=Q(doctors__is_active=True))
        ).aggregate(avg=Avg('doctor_count'))['avg'] or 0
        
        with_coordinates = Clinic.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        ).count()
        
        return {
            "total": counts['total'],
            "active": counts['active'],
            "inactive": counts['inactive'],
            "type_distribution": type_stats,
            "status_distribution": status_stats,
            "top_counties": counties,
            "top_cities": cities,
            "average_doctors_per_clinic": round(avg_doctors, 2),
            "clinics_with_coordinates": with_coordinates,
        }
    
    @staticmethod
    def get_clinic_details(clinic: Clinic) -> Dict[str, Any]:
        """
        Get detailed information about a specific clinic.
        """
        active_doctors = clinic.doctors.filter(is_active=True)
        doctor_count = active_doctors.count()
        
        return {
            "id": clinic.id,
            "code": clinic.code,
            "slug": clinic.slug,
            "name": clinic.name,
            "type": clinic.clinic_type,
            "status": clinic.status,
            "is_active": clinic.is_active,
            "doctor_count": doctor_count,
            "active_doctors_count": doctor_count,
            "contact": {
                "email": clinic.email,
                "phone": clinic.phone_number,
                "website": clinic.website,
                "emergency": clinic.emergency_contact,
            },
            "location": {
                "address": clinic.address,
                "city": clinic.city,
                "county": clinic.county,
                "country": clinic.country,
                "postal_code": clinic.postal_code,
                "full_address": clinic.full_address,
                "coordinates": {
                    "latitude": float(clinic.latitude) if clinic.latitude else None,
                    "longitude": float(clinic.longitude) if clinic.longitude else None,
                }
            },
            "registration": {
                "license_number": clinic.license_number,
                "registration_number": clinic.registration_number,
            },
            "established_date": clinic.established_date,
            "logo": clinic.logo.url if clinic.logo else None,
            "description": clinic.description,
            "created_at": clinic.created_at,
            "updated_at": clinic.updated_at,
        }

    # ============ NEARBY CLINICS ============
    
    @staticmethod
    def get_nearby_clinics(
        latitude: float,
        longitude: float,
        radius_km: float = 10,
        limit: int = 10,
        only_active: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get clinics near a specific location using the Haversine formula.
        """
        queryset = Clinic.objects.annotate(
            doctor_count=Count('doctors', filter=Q(doctors__is_active=True))
        ).filter(
            latitude__isnull=False,
            longitude__isnull=False
        )
        
        if only_active:
            queryset = queryset.filter(is_active=True)
        
        clinics_with_distance = []
        EARTH_RADIUS_KM = 6371
        
        for clinic in queryset:
            lat1 = radians(latitude)
            lon1 = radians(longitude)
            lat2 = radians(float(clinic.latitude))
            lon2 = radians(float(clinic.longitude))
            
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            
            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
            c = 2 * asin(sqrt(a))
            distance = EARTH_RADIUS_KM * c
            
            if distance <= radius_km:
                clinics_with_distance.append({
                    'clinic': clinic,
                    'distance_km': round(distance, 2),
                    'doctor_count': clinic.doctor_count,
                })
        
        clinics_with_distance.sort(key=lambda x: x['distance_km'])
        clinics_with_distance = clinics_with_distance[:limit]
        
        return clinics_with_distance