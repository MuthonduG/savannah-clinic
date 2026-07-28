import logging
from django.core.exceptions import ValidationError as DjangoValidationError
# Remove unused imports: Count, Q
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.pagination import LimitOffsetPagination
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend

from .models import Doctor, Specialization
from .serializers import (
    SpecializationSerializer,
    # DoctorSerializer,  # REMOVED - doesn't exist
    DoctorListSerializer,
    DoctorDetailSerializer,
    DoctorCreateSerializer,
    DoctorUpdateSerializer,
    DoctorChangePasswordSerializer,
    DoctorBulkUpdateSerializer,
    DoctorBulkTransferSerializer,
    DoctorActivationSerializer,
)
from .services import DoctorService, DoctorServiceError

logger = logging.getLogger(__name__)


class DoctorViewSet(viewsets.ModelViewSet):
    """
    Doctor ViewSet with full CRUD operations and custom actions.
    All business logic is delegated to DoctorService.
    """
    
    # Constants
    PUBLIC_ACTIONS = ['list', 'retrieve']
    ADMIN_ACTIONS = ['statistics', 'bulk_update', 'bulk_transfer']
    
    # Authentication & Permissions
    authentication_classes = [JWTAuthentication]
    
    # Filtering, Searching, Ordering
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['specialization', 'clinic', 'is_active', 'gender', 'employment_type']
    search_fields = ['user__first_name', 'user__last_name', 'license_number', 'user__email']
    ordering_fields = ['user__first_name', 'user__last_name', 'years_of_experience', 'created_at']
    ordering = ['user__last_name', 'user__first_name']
    
    # Pagination
    pagination_class = LimitOffsetPagination
    
    # ============ Queryset ============
    
    def get_queryset(self):
        """
        Return base queryset with necessary select_related.
        """
        return Doctor.objects.select_related(
            'user', 'clinic', 'specialization'
        ).all().order_by('user__last_name', 'user__first_name')
    
    # ============ Helper Methods ============
    
    def _get_bool(self, name: str, default: bool = None) -> bool:
        """
        Parse boolean query parameter.
        
        Args:
            name: Query parameter name
            default: Default value if parameter is missing
            
        Returns:
            bool: Parsed boolean value
        """
        value = self.request.query_params.get(name)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')
    
    def _get_int(self, name: str, default: int = None) -> int:
        """
        Parse integer query parameter.
        
        Args:
            name: Query parameter name
            default: Default value if parameter is missing or invalid
            
        Returns:
            int: Parsed integer value or default
        """
        value = self.request.query_params.get(name)
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    
    def _get_search_filters(self) -> dict:
        """
        Build search filters dictionary from query parameters.
        
        Returns:
            dict: Filters for DoctorService.search_doctors()
        """
        return {
            'search': self.request.query_params.get('search'),
            'clinic': self.request.query_params.get('clinic'),
            'specialization': self.request.query_params.get('specialization'),
            'is_active': self._get_bool('is_active'),
            'gender': self.request.query_params.get('gender'),
            'employment_type': self.request.query_params.get('employment_type'),
            'min_experience': self._get_int('min_experience'),
            'max_experience': self._get_int('max_experience'),
            'ordering': self.request.query_params.get('ordering', '-created_at'),
        }
    
    # ============ Exception Handlers ============
    
    def handle_validation_error(self, e):
        """
        Handle Django validation errors consistently.
        
        Args:
            e: DjangoValidationError instance
            
        Returns:
            Response: 400 Bad Request response
        """
        return Response(
            {'errors': e.message_dict if hasattr(e, 'message_dict') else str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    def handle_service_error(self, e, action="operation"):
        """
        Handle service layer errors consistently.
        
        Args:
            e: DoctorServiceError instance
            action: Description of the action that failed
            
        Returns:
            Response: 500 Internal Server Error response
        """
        logger.error(f"Doctor {action} error: {str(e)}", exc_info=True)
        return Response(
            {'detail': f'Failed to {action}. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    def handle_not_found(self, detail="Doctor not found."):
        """
        Handle not found errors consistently.
        
        Args:
            detail: Error message detail
            
        Returns:
            Response: 404 Not Found response
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
            # Public read-only access
            return [AllowAny()]
        elif self.action in self.ADMIN_ACTIONS:
            # Admin only for admin operations
            return [IsAdminUser()]
        else:
            # Authenticated for all write operations
            return [IsAuthenticated()]
    
    # ============ Serializer Selection ============
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        # Map actions to serializers
        serializer_map = {
            'create': DoctorCreateSerializer,
            'update': DoctorUpdateSerializer,
            'partial_update': DoctorUpdateSerializer,
            'list': DoctorListSerializer,
            'retrieve': DoctorDetailSerializer,
            'bulk_update': DoctorBulkUpdateSerializer,
            'bulk_transfer': DoctorBulkTransferSerializer,
        }
        
        # Return the appropriate serializer or fallback to DetailSerializer
        return serializer_map.get(self.action, DoctorDetailSerializer)
    
    # ============ List / Search ============
    
    def list(self, request, *args, **kwargs):
        """
        List doctors with advanced search and filtering via service layer.
        GET /doctors/
        """
        try:
            # Build filters from query parameters
            filters = self._get_search_filters()
            
            # Get filtered queryset using service layer
            queryset = DoctorService.search_doctors(**filters)
            
            # Apply DRF pagination
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            # Fallback for non-paginated response
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except DoctorServiceError as e:
            return self.handle_service_error(e, "list doctors")
    
    # ============ Retrieve ============
    
    def retrieve(self, request, *args, **kwargs):
        """
        Get detailed doctor information using service layer.
        GET /doctors/{id}/
        """
        try:
            # Use service method for optimized retrieval
            doctor = DoctorService.get_doctor_by_id(
                kwargs["pk"],
                prefetch_related=True
            )
            
            if not doctor:
                return self.handle_not_found()
            
            serializer = self.get_serializer(doctor)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except DoctorServiceError as e:
            return self.handle_service_error(e, "retrieve doctor")
    
    # ============ Create ============
    
    def create(self, request, *args, **kwargs):
        """
        Create a new doctor using service layer.
        POST /doctors/
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            doctor = DoctorService.create_doctor(
                **serializer.validated_data,
                created_by=request.user,  # User is guaranteed authenticated by permissions
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            
            return Response(
                DoctorDetailSerializer(doctor).data,
                status=status.HTTP_201_CREATED
            )
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except DoctorServiceError as e:
            return self.handle_service_error(e, "create doctor")
    
    # ============ Update ============
    
    def update(self, request, *args, **kwargs):
        """
        Full update of a doctor using service layer.
        PUT /doctors/{id}/
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Pass validated data directly to service
            doctor = DoctorService.update_doctor(
                instance,
                updated_by=request.user,  # User is guaranteed authenticated by permissions
                **serializer.validated_data
            )
            
            return Response(
                DoctorDetailSerializer(doctor).data,
                status=status.HTTP_200_OK
            )
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except DoctorServiceError as e:
            return self.handle_service_error(e, "update doctor")
    
    def partial_update(self, request, *args, **kwargs):
        """
        Partial update of a doctor.
        PATCH /doctors/{id}/
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    # ============ Delete / Archive ============
    
    def destroy(self, request, *args, **kwargs):
        """
        Archive (soft delete) a doctor using service layer.
        DELETE /doctors/{id}/
        """
        instance = self.get_object()
        
        try:
            DoctorService.delete_doctor(
                instance,
                deleted_by=request.user,  # User is guaranteed authenticated by permissions
            )
            
            return Response(
                {'detail': 'Doctor archived successfully.'},
                status=status.HTTP_200_OK
            )
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except DoctorServiceError as e:
            return self.handle_service_error(e, "archive doctor")
    
    # ============ Custom Actions ============
    
    @action(detail=True, methods=['patch'], url_path='toggle-active')
    def toggle_active(self, request, pk=None):
        """
        Toggle doctor active status.
        PATCH /doctors/{id}/toggle-active/
        Body: {"is_active": true/false}
        
        This endpoint replaces the separate activate/deactivate endpoints
        for a cleaner REST API.
        """
        doctor = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        is_active = serializer.validated_data['is_active']
        
        try:
            if is_active:
                updated_doctor = DoctorService.activate_doctor(
                    doctor,
                    activated_by=request.user,
                )
                message = 'Doctor activated successfully.'
            else:
                updated_doctor = DoctorService.deactivate_doctor(
                    doctor,
                    deactivated_by=request.user,
                )
                message = 'Doctor deactivated successfully.'
            
            return Response(
                {
                    'detail': message,
                    'data': DoctorDetailSerializer(updated_doctor).data
                },
                status=status.HTTP_200_OK
            )
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except DoctorServiceError as e:
            return self.handle_service_error(e, "toggle doctor status")
    
    @action(detail=True, methods=['post'], url_path='change-password')
    def change_password(self, request, pk=None):
        """
        Change a doctor's password (self-service).
        POST /doctors/{id}/change-password/
        Body: {"current_password": "...", "new_password": "...", "confirm_password": "..."}
        """
        doctor = self.get_object()
        
        # Check if user is updating their own password or is admin
        if request.user != doctor.user and not request.user.is_staff:
            return Response(
                {'detail': 'You can only change your own password.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DoctorChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        try:
            DoctorService.change_password(
                doctor,
                old_password=serializer.validated_data['current_password'],
                new_password=serializer.validated_data['new_password']
            )
            
            return Response(
                {'detail': 'Password changed successfully.'},
                status=status.HTTP_200_OK
            )
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except DoctorServiceError as e:
            return self.handle_service_error(e, "change password")
    
    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        """
        Reset a doctor's password (admin only).
        POST /doctors/{id}/reset-password/
        Body: {"new_password": "..."}
        """
        doctor = self.get_object()
        new_password = request.data.get('new_password')
        
        if not new_password:
            return Response(
                {'errors': {'new_password': 'This field is required.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            DoctorService.reset_password(
                doctor,
                new_password=new_password,
                reset_by=request.user
            )
            
            return Response(
                {'detail': f'Password reset for {doctor.full_name} successfully.'},
                status=status.HTTP_200_OK
            )
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except DoctorServiceError as e:
            return self.handle_service_error(e, "reset password")
    
    @action(detail=False, methods=['post'], url_path='bulk-update')
    def bulk_update(self, request):
        """
        Bulk update doctors (activate, deactivate, change employment type).
        POST /doctors/bulk-update/
        Body: {"doctor_ids": [1,2,3], "is_active": true, "employment_type": "FULL_TIME"}
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        doctor_ids = serializer.validated_data['doctor_ids']
        is_active = serializer.validated_data.get('is_active')
        employment_type = serializer.validated_data.get('employment_type')
        
        results = {}
        
        try:
            if is_active is not None:
                if is_active:
                    result = DoctorService.bulk_activate(doctor_ids, activated_by=request.user)
                else:
                    result = DoctorService.bulk_deactivate(doctor_ids, deactivated_by=request.user)
                results['activation'] = result
            
            if employment_type is not None:
                result = DoctorService.bulk_change_employment_type(
                    doctor_ids,
                    employment_type,
                    changed_by=request.user
                )
                results['employment_type'] = result
            
            return Response(
                {
                    'detail': 'Bulk update completed successfully.',
                    'results': results
                },
                status=status.HTTP_200_OK
            )
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except DoctorServiceError as e:
            return self.handle_service_error(e, "bulk update")
    
    @action(detail=False, methods=['post'], url_path='bulk-transfer')
    def bulk_transfer(self, request):
        """
        Bulk transfer doctors to another clinic.
        POST /doctors/bulk-transfer/
        Body: {"doctor_ids": [1,2,3], "clinic_id": 5}
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        doctor_ids = serializer.validated_data['doctor_ids']
        clinic = serializer.validated_data['clinic']
        
        try:
            result = DoctorService.bulk_transfer_clinic(
                doctor_ids,
                clinic,
                transferred_by=request.user
            )
            
            return Response(
                {
                    'detail': f"Successfully transferred {result['updated_count']} doctors.",
                    'results': result
                },
                status=status.HTTP_200_OK
            )
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except DoctorServiceError as e:
            return self.handle_service_error(e, "bulk transfer")
    
    @action(
        detail=False,
        methods=['get'],
        url_path='statistics',
        permission_classes=[IsAdminUser]
    )
    def statistics(self, request):
        """
        Get doctor statistics (admin only).
        GET /doctors/statistics/?clinic_id=1
        """
        try:
            clinic_id = request.query_params.get('clinic_id')
            clinic = None
            
            if clinic_id:
                from apps.clinic.models import Clinic
                clinic = Clinic.objects.get(id=clinic_id)
            
            stats = DoctorService.get_statistics(clinic)
            return Response(stats, status=status.HTTP_200_OK)
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except DoctorServiceError as e:
            return self.handle_service_error(e, "retrieve statistics")


class SpecializationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing specializations (read-only).
    """
    queryset = Specialization.objects.all().order_by('name')
    serializer_class = SpecializationSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name']
    ordering = ['name']