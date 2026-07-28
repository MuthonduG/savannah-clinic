import logging
from typing import Optional, List, Dict, Any
from datetime import time, datetime, timedelta
from django.db import transaction
from django.db.models import Q, QuerySet
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from .models import WorkingHours
from apps.doctor.models import Doctor

logger = logging.getLogger(__name__)
User = get_user_model()


class WorkingHoursServiceError(Exception):
    """Base exception for working hours service errors."""
    pass


class WorkingHoursService:
    """Service layer for Working Hours operations."""

    # ============ CREATE ============
    
    @staticmethod
    @transaction.atomic
    def create_working_hours(
        *,
        doctor: Doctor,
        day_of_week: str,
        start_time: time,
        end_time: time,
        slot_duration: int = 30,
        is_available: bool = True,
        created_by: Optional[User] = None,
        **kwargs
    ) -> WorkingHours:
        """
        Create a new working hours entry.
        """
        try:
            # Validate time range
            if start_time >= end_time:
                raise ValidationError({
                    "end_time": "End time must be after start time."
                })
            
            # Check for overlapping entries
            if WorkingHours.objects.filter(
                doctor=doctor,
                day_of_week=day_of_week,
                is_available=True
            ).filter(
                Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
            ).exists():
                raise ValidationError({
                    "start_time": "This time overlaps with existing working hours for this doctor."
                })
            
            # Create working hours
            working_hours = WorkingHours.objects.create(
                doctor=doctor,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
                slot_duration=slot_duration,
                is_available=is_available,
            )
            
            logger.info(
                "Working hours created",
                extra={
                    "working_hours_id": working_hours.id,
                    "doctor_id": doctor.id,
                    "doctor_name": doctor.full_name,
                    "day": day_of_week,
                    "start_time": start_time.strftime('%H:%M'),
                    "end_time": end_time.strftime('%H:%M'),
                    "created_by": created_by.id if created_by else None,
                }
            )
            
            return working_hours
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to create working hours: {str(e)}", exc_info=True)
            raise WorkingHoursServiceError(f"Failed to create working hours: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def bulk_create_working_hours(
        *,
        doctor: Doctor,
        working_hours_list: List[Dict[str, Any]],
        created_by: Optional[User] = None,
    ) -> List[WorkingHours]:
        """
        Bulk create working hours for a doctor.
        """
        created_entries = []
        errors = []
        
        for idx, data in enumerate(working_hours_list):
            try:
                entry = WorkingHoursService.create_working_hours(
                    doctor=doctor,
                    day_of_week=data['day_of_week'],
                    start_time=data['start_time'],
                    end_time=data['end_time'],
                    slot_duration=data.get('slot_duration', 30),
                    is_available=data.get('is_available', True),
                    created_by=created_by,
                )
                created_entries.append(entry)
            except ValidationError as e:
                errors.append({
                    "index": idx,
                    "data": data,
                    "errors": e.message_dict if hasattr(e, 'message_dict') else str(e)
                })
            except Exception as e:
                errors.append({
                    "index": idx,
                    "data": data,
                    "errors": str(e)
                })
        
        if errors:
            logger.warning(
                f"Bulk create working hours completed with {len(errors)} errors",
                extra={
                    "doctor_id": doctor.id,
                    "total_attempted": len(working_hours_list),
                    "successful": len(created_entries),
                    "errors": errors,
                }
            )
        
        return created_entries

    # ============ RETRIEVE ============
    
    @staticmethod
    def get_working_hours_by_id(working_hours_id: int) -> Optional[WorkingHours]:
        """Get working hours by ID."""
        try:
            return WorkingHours.objects.select_related('doctor__user').get(id=working_hours_id)
        except WorkingHours.DoesNotExist:
            return None
    
    @staticmethod
    def get_working_hours_for_doctor(
        doctor_id: int,
        day_of_week: Optional[str] = None,
        is_available: Optional[bool] = None,
    ) -> QuerySet[WorkingHours]:
        """
        Get working hours for a specific doctor.
        """
        queryset = WorkingHours.objects.select_related('doctor__user').filter(doctor_id=doctor_id)
        
        if day_of_week:
            queryset = queryset.filter(day_of_week=day_of_week)
        
        if is_available is not None:
            queryset = queryset.filter(is_available=is_available)
        
        return queryset.order_by('day_of_week', 'start_time')
    
    @staticmethod
    def get_available_slots(
        doctor_id: int,
        day_of_week: str,
        date=None,
    ) -> List[Dict[str, Any]]:
        """
        Get available time slots for a doctor on a specific day.
        """
        working_hours = WorkingHours.objects.filter(
            doctor_id=doctor_id,
            day_of_week=day_of_week,
            is_available=True
        ).order_by('start_time')
        
        slots = []
        for wh in working_hours:
            # Convert time to minutes for easier calculation
            start_minutes = wh.start_time.hour * 60 + wh.start_time.minute
            end_minutes = wh.end_time.hour * 60 + wh.end_time.minute
            slot_duration_minutes = wh.slot_duration
            
            current_minutes = start_minutes
            while current_minutes + slot_duration_minutes <= end_minutes:
                start_hour = current_minutes // 60
                start_min = current_minutes % 60
                end_hour = (current_minutes + slot_duration_minutes) // 60
                end_min = (current_minutes + slot_duration_minutes) % 60
                
                slots.append({
                    'start_time': f"{start_hour:02d}:{start_min:02d}",
                    'end_time': f"{end_hour:02d}:{end_min:02d}",
                    'slot_duration': wh.slot_duration,
                })
                current_minutes += slot_duration_minutes
        
        return slots
    
    @staticmethod
    def search_working_hours(
        *,
        doctor_id: Optional[int] = None,
        day_of_week: Optional[str] = None,
        is_available: Optional[bool] = None,
        start_time_from: Optional[time] = None,
        start_time_to: Optional[time] = None,
        ordering: str = "day_of_week,start_time",
    ) -> QuerySet[WorkingHours]:
        """
        Search and filter working hours.
        """
        queryset = WorkingHours.objects.select_related('doctor__user')
        
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        
        if day_of_week:
            queryset = queryset.filter(day_of_week=day_of_week)
        
        if is_available is not None:
            queryset = queryset.filter(is_available=is_available)
        
        if start_time_from:
            queryset = queryset.filter(start_time__gte=start_time_from)
        
        if start_time_to:
            queryset = queryset.filter(start_time__lte=start_time_to)
        
        # Apply ordering - handle multiple fields separated by comma
        if ordering:
            # Split by comma and strip whitespace
            order_fields = [field.strip() for field in ordering.split(',') if field.strip()]
            
            # Validate fields to prevent SQL injection
            allowed_fields = {
                'day_of_week', '-day_of_week',
                'start_time', '-start_time',
                'end_time', '-end_time',
                'doctor', '-doctor',
                'is_available', '-is_available',
                'created_at', '-created_at',
                'updated_at', '-updated_at',
            }
            
            valid_order_fields = []
            for field in order_fields:
                if field in allowed_fields:
                    valid_order_fields.append(field)
                else:
                    # Log warning but continue with valid fields
                    logger.warning(f"Ignoring invalid ordering field: {field}")
            
            if valid_order_fields:
                # Use * to unpack the list
                queryset = queryset.order_by(*valid_order_fields)
            else:
                # Default ordering
                queryset = queryset.order_by('day_of_week', 'start_time')
        else:
            # Default ordering
            queryset = queryset.order_by('day_of_week', 'start_time')
        
        return queryset

    # ============ UPDATE ============
    
    @staticmethod
    @transaction.atomic
    def update_working_hours(
        working_hours: WorkingHours,
        *,
        day_of_week: Optional[str] = None,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        slot_duration: Optional[int] = None,
        is_available: Optional[bool] = None,
        updated_by: Optional[User] = None,
    ) -> WorkingHours:
        """
        Update working hours.
        """
        update_fields = []
        
        if day_of_week is not None:
            working_hours.day_of_week = day_of_week
            update_fields.append('day_of_week')
        
        if start_time is not None:
            working_hours.start_time = start_time
            update_fields.append('start_time')
        
        if end_time is not None:
            working_hours.end_time = end_time
            update_fields.append('end_time')
        
        if slot_duration is not None:
            working_hours.slot_duration = slot_duration
            update_fields.append('slot_duration')
        
        if is_available is not None:
            working_hours.is_available = is_available
            update_fields.append('is_available')
        
        if update_fields:
            try:
                # Validate
                if working_hours.start_time >= working_hours.end_time:
                    raise ValidationError({
                        "end_time": "End time must be after start time."
                    })
                
                # Check for overlaps (excluding self)
                if working_hours.is_available:
                    overlapping = WorkingHours.objects.filter(
                        doctor=working_hours.doctor,
                        day_of_week=working_hours.day_of_week,
                        is_available=True
                    ).exclude(id=working_hours.id).filter(
                        Q(start_time__lt=working_hours.end_time) & 
                        Q(end_time__gt=working_hours.start_time)
                    )
                    
                    if overlapping.exists():
                        raise ValidationError({
                            "start_time": "This time overlaps with existing working hours."
                        })
                
                working_hours.full_clean()
                working_hours.save(update_fields=update_fields)
                
                logger.info(
                    "Working hours updated",
                    extra={
                        "working_hours_id": working_hours.id,
                        "doctor_id": working_hours.doctor.id,
                        "updated_by": updated_by.id if updated_by else None,
                        "updated_fields": update_fields,
                    }
                )
                
            except ValidationError:
                raise
            except Exception as e:
                logger.error(f"Failed to update working hours: {str(e)}", exc_info=True)
                raise WorkingHoursServiceError(f"Failed to update working hours: {str(e)}")
        
        return working_hours

    # ============ DELETE ============
    
    @staticmethod
    @transaction.atomic
    def delete_working_hours(
        working_hours: WorkingHours,
        deleted_by: Optional[User] = None,
    ) -> None:
        """
        Delete working hours entry.
        """
        try:
            doctor = working_hours.doctor
            working_hours.delete()
            
            logger.info(
                "Working hours deleted",
                extra={
                    "working_hours_id": working_hours.id,
                    "doctor_id": doctor.id,
                    "deleted_by": deleted_by.id if deleted_by else None,
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to delete working hours: {str(e)}", exc_info=True)
            raise WorkingHoursServiceError(f"Failed to delete working hours: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def delete_working_hours_for_doctor(
        doctor_id: int,
        day_of_week: Optional[str] = None,
        deleted_by: Optional[User] = None,
    ) -> Dict[str, Any]:
        """
        Delete all working hours for a doctor, optionally filtered by day.
        """
        try:
            queryset = WorkingHours.objects.filter(doctor_id=doctor_id)
            
            if day_of_week:
                queryset = queryset.filter(day_of_week=day_of_week)
            
            count = queryset.count()
            queryset.delete()
            
            logger.info(
                f"Deleted {count} working hours for doctor",
                extra={
                    "doctor_id": doctor_id,
                    "day_of_week": day_of_week,
                    "count": count,
                    "deleted_by": deleted_by.id if deleted_by else None,
                }
            )
            
            return {"deleted_count": count}
            
        except Exception as e:
            logger.error(f"Failed to delete working hours for doctor: {str(e)}", exc_info=True)
            raise WorkingHoursServiceError(f"Failed to delete working hours: {str(e)}")

    # ============ STATISTICS ============
    
    @staticmethod
    def get_statistics(doctor_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get statistics for working hours.
        """
        queryset = WorkingHours.objects.select_related('doctor')
        
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        
        total = queryset.count()
        available = queryset.filter(is_available=True).count()
        unavailable = total - available
        
        # Breakdown by day
        by_day = {}
        for day_code, day_label in WorkingHours.Days.choices:
            count = queryset.filter(day_of_week=day_code).count()
            available_count = queryset.filter(day_of_week=day_code, is_available=True).count()
            by_day[day_code] = {
                'label': day_label,
                'total': count,
                'available': available_count,
                'unavailable': count - available_count,
            }
        
        return {
            "total": total,
            "available": available,
            "unavailable": unavailable,
            "by_day": by_day,
        }