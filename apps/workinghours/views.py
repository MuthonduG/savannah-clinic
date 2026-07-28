import logging
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.pagination import LimitOffsetPagination
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend

from .models import WorkingHours
from .serializers import (
    WorkingHoursSerializer,
    WorkingHoursListSerializer,
    WorkingHoursCreateUpdateSerializer,
    WorkingHoursBulkCreateSerializer,
    WorkingHoursFilterSerializer,
)
from .services import WorkingHoursService, WorkingHoursServiceError

logger = logging.getLogger(__name__)


class WorkingHoursViewSet(viewsets.ModelViewSet):
    """
    Working Hours ViewSet with full CRUD operations and custom actions.
    All business logic is delegated to WorkingHoursService.
    """
    
    # Constants
    PUBLIC_ACTIONS = ['list', 'retrieve', 'available_slots']
    
    # Authentication & Permissions
    authentication_classes = [JWTAuthentication]
    
    # Filtering, Searching, Ordering
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['doctor', 'day_of_week', 'is_available']
    search_fields = ['doctor__user__first_name', 'doctor__user__last_name']
    ordering_fields = ['doctor', 'day_of_week', 'start_time', 'end_time']
    ordering = ['doctor', 'day_of_week', 'start_time']
    
    # Pagination
    pagination_class = LimitOffsetPagination
    
    # ============ Queryset ============
    
    def get_queryset(self):
        """
        Return base queryset with select_related.
        """
        return WorkingHours.objects.select_related(
            'doctor',
            'doctor__user',
        ).all()
    
    # ============ Helper Methods ============
    
    def _get_int(self, name: str, default: int = None) -> int:
        """
        Parse integer query parameter.
        """
        value = self.request.query_params.get(name)
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    
    def _get_bool(self, name: str, default: bool = None) -> bool:
        """
        Parse boolean query parameter.
        """
        value = self.request.query_params.get(name)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')
    
    def _get_search_filters(self) -> dict:
        """
        Build search filters dictionary from query parameters.
        """
        return {
            'doctor_id': self._get_int('doctor_id'),
            'day_of_week': self.request.query_params.get('day_of_week'),
            'is_available': self._get_bool('is_available'),
            'start_time_from': self.request.query_params.get('start_time_from'),
            'start_time_to': self.request.query_params.get('start_time_to'),
            'ordering': self.request.query_params.get('ordering', 'day_of_week,start_time'),
        }
    
    # ============ Exception Handlers ============
    
    def handle_validation_error(self, e):
        """
        Handle Django validation errors consistently.
        """
        return Response(
            {'errors': e.message_dict if hasattr(e, 'message_dict') else str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    def handle_service_error(self, e, action="operation"):
        """
        Handle service layer errors consistently.
        """
        logger.error(f"Working hours {action} error: {str(e)}", exc_info=True)
        return Response(
            {'detail': f'Failed to {action}. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    def handle_not_found(self, detail="Working hours not found."):
        """
        Handle not found errors consistently.
        """
        return Response(
            {'detail': detail},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # ============ Permissions ============
    
    def get_permissions(self):
        """
        Custom permissions based on action.
        """
        if self.action in self.PUBLIC_ACTIONS:
            return [AllowAny()]
        else:
            return [IsAuthenticated()]
    
    # ============ Serializer Selection ============
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action in ['create', 'update', 'partial_update']:
            return WorkingHoursCreateUpdateSerializer
        elif self.action == 'list':
            return WorkingHoursListSerializer
        elif self.action == 'bulk_create':
            return WorkingHoursBulkCreateSerializer
        return WorkingHoursSerializer
    
    # ============ List / Search ============
    
    def list(self, request, *args, **kwargs):
        """
        List working hours with advanced search and filtering.
        GET /working-hours/
        """
        try:
            filters = self._get_search_filters()
            queryset = WorkingHoursService.search_working_hours(**filters)
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except WorkingHoursServiceError as e:
            return self.handle_service_error(e, "list working hours")
    
    # ============ Retrieve ============
    
    def retrieve(self, request, *args, **kwargs):
        """
        Get detailed working hours information.
        GET /working-hours/{id}/
        """
        try:
            working_hours = WorkingHoursService.get_working_hours_by_id(kwargs["pk"])
            
            if not working_hours:
                return self.handle_not_found()
            
            serializer = self.get_serializer(working_hours)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except WorkingHoursServiceError as e:
            return self.handle_service_error(e, "retrieve working hours")
    
    # ============ Create ============
    
    def create(self, request, *args, **kwargs):
        """
        Create a new working hours entry.
        POST /working-hours/
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            working_hours = WorkingHoursService.create_working_hours(
                **serializer.validated_data,
                created_by=request.user,
            )
            
            response_serializer = WorkingHoursSerializer(working_hours)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except WorkingHoursServiceError as e:
            return self.handle_service_error(e, "create working hours")
    
    # ============ Update ============
    
    def update(self, request, *args, **kwargs):
        """
        Full update of working hours.
        PUT /working-hours/{id}/
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        try:
            working_hours = WorkingHoursService.update_working_hours(
                instance,
                **serializer.validated_data,
                updated_by=request.user,
            )
            
            response_serializer = WorkingHoursSerializer(working_hours)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except WorkingHoursServiceError as e:
            return self.handle_service_error(e, "update working hours")
    
    def partial_update(self, request, *args, **kwargs):
        """
        Partial update of working hours.
        PATCH /working-hours/{id}/
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    # ============ Delete ============
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete working hours entry.
        DELETE /working-hours/{id}/
        """
        instance = self.get_object()
        
        try:
            WorkingHoursService.delete_working_hours(
                instance,
                deleted_by=request.user,
            )
            
            return Response(
                {'detail': 'Working hours deleted successfully.'},
                status=status.HTTP_200_OK
            )
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except WorkingHoursServiceError as e:
            return self.handle_service_error(e, "delete working hours")
    
    # ============ Custom Actions ============
    
    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        """
        Bulk create working hours for a doctor.
        POST /working-hours/bulk-create/
        Body: {
            "doctor_id": 1,
            "working_hours": [
                {"day_of_week": "MONDAY", "start_time": "09:00", "end_time": "17:00"},
                {"day_of_week": "TUESDAY", "start_time": "09:00", "end_time": "17:00"}
            ]
        }
        """
        serializer = WorkingHoursBulkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        doctor = serializer.validated_data['doctor_id']
        working_hours_list = serializer.validated_data['working_hours']
        
        try:
            created_entries = WorkingHoursService.bulk_create_working_hours(
                doctor=doctor,
                working_hours_list=working_hours_list,
                created_by=request.user,
            )
            
            response_serializer = WorkingHoursListSerializer(created_entries, many=True)
            return Response(
                {
                    'detail': f'Successfully created {len(created_entries)} working hours entries.',
                    'data': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except WorkingHoursServiceError as e:
            return self.handle_service_error(e, "bulk create working hours")
    
    @action(detail=False, methods=['delete'], url_path='doctor/(?P<doctor_id>[^/.]+)')
    def delete_by_doctor(self, request, doctor_id=None):
        """
        Delete all working hours for a doctor.
        DELETE /working-hours/doctor/{doctor_id}/?day_of_week=MONDAY
        """
        day_of_week = request.query_params.get('day_of_week')
        
        try:
            result = WorkingHoursService.delete_working_hours_for_doctor(
                doctor_id=doctor_id,
                day_of_week=day_of_week,
                deleted_by=request.user,
            )
            
            return Response(
                {
                    'detail': f"Deleted {result['deleted_count']} working hours entries.",
                    'data': result
                },
                status=status.HTTP_200_OK
            )
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except WorkingHoursServiceError as e:
            return self.handle_service_error(e, "delete working hours for doctor")
    
    @action(detail=False, methods=['get'], url_path='available-slots')
    def available_slots(self, request):
        """
        Get available time slots for a doctor on a specific day.
        GET /working-hours/available-slots/?doctor_id=1&day_of_week=MONDAY
        """
        doctor_id = self._get_int('doctor_id')
        day_of_week = request.query_params.get('day_of_week')
        
        if not doctor_id:
            return Response(
                {'errors': {'doctor_id': 'This field is required.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not day_of_week:
            return Response(
                {'errors': {'day_of_week': 'This field is required.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            slots = WorkingHoursService.get_available_slots(
                doctor_id=doctor_id,
                day_of_week=day_of_week,
            )
            
            return Response({
                'doctor_id': doctor_id,
                'day_of_week': day_of_week,
                'slots': slots,
                'total_slots': len(slots),
            }, status=status.HTTP_200_OK)
            
        except WorkingHoursServiceError as e:
            return self.handle_service_error(e, "get available slots")
    
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """
        Get working hours statistics.
        GET /working-hours/statistics/?doctor_id=1
        """
        doctor_id = self._get_int('doctor_id')
        
        try:
            stats = WorkingHoursService.get_statistics(doctor_id)
            return Response(stats, status=status.HTTP_200_OK)
            
        except WorkingHoursServiceError as e:
            return self.handle_service_error(e, "get statistics")