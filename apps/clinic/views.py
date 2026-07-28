import logging
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.pagination import LimitOffsetPagination
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend

from .models import Clinic
from .serializers import (
    ClinicSerializer,
    ClinicListSerializer,
    ClinicCreateUpdateSerializer,
    ClinicActivationSerializer,
    ClinicNearbySerializer,
)
from .services import ClinicService, ClinicServiceError

logger = logging.getLogger(__name__)


class ClinicViewSet(viewsets.ModelViewSet):
    """
    Clinic ViewSet with full CRUD operations and custom actions.
    All business logic is delegated to ClinicService.
    """
    
    # Constants
    PUBLIC_ACTIONS = ['list', 'retrieve', 'nearby']
    
    # Authentication & Permissions
    authentication_classes = [JWTAuthentication]
    
    # Filtering, Searching, Ordering
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['clinic_type', 'status', 'is_active', 'city', 'county', 'country']
    search_fields = ['name', 'code', 'address', 'city', 'county', 'email', 'phone_number']
    ordering_fields = ['name', 'code', 'city', 'county', 'created_at', 'updated_at']
    ordering = ['name']
    
    # Pagination
    pagination_class = LimitOffsetPagination
    
    # ============ Queryset ============
    
    def get_queryset(self):
        """
        Return base queryset without annotations.
        Annotations are handled by the service layer.
        """
        return Clinic.objects.all().order_by('name')
    
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
            dict: Filters for ClinicService.search_clinics()
        """
        return {
            'search': self.request.query_params.get('search'),
            'clinic_type': self.request.query_params.get('clinic_type'),
            'status': self.request.query_params.get('status'),
            'city': self.request.query_params.get('city'),
            'county': self.request.query_params.get('county'),
            'country': self.request.query_params.get('country'),
            'is_active': self._get_bool('is_active'),
            'has_coordinates': self._get_bool('has_coordinates'),
            'min_doctors': self._get_int('min_doctors'),
            'max_doctors': self._get_int('max_doctors'),
            'ordering': self.request.query_params.get('ordering', 'name'),
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
            e: ClinicServiceError instance
            action: Description of the action that failed
            
        Returns:
            Response: 500 Internal Server Error response
        """
        logger.error(f"Clinic {action} error: {str(e)}", exc_info=True)
        return Response(
            {'detail': f'Failed to {action}. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    def handle_not_found(self, detail="Clinic not found."):
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
        elif self.action == 'statistics':
            # Admin only for statistics
            return [IsAdminUser()]
        else:
            # Authenticated for all write operations
            return [IsAuthenticated()]
    
    # ============ Serializer Selection ============
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action in ['create', 'update', 'partial_update']:
            return ClinicCreateUpdateSerializer
        elif self.action == 'list':
            return ClinicListSerializer
        return ClinicSerializer
    
    # ============ List / Search ============
    
    def list(self, request, *args, **kwargs):
        """
        List clinics with advanced search and filtering via service layer.
        GET /clinics/
        """
        try:
            # Build filters from query parameters
            filters = self._get_search_filters()
            
            # Get filtered queryset using service layer
            # Service returns annotated queryset WITHOUT pagination
            queryset = ClinicService.search_clinics(**filters)
            
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
        except ClinicServiceError as e:
            return self.handle_service_error(e, "list clinics")
    
    # ============ Retrieve ============
    
    def retrieve(self, request, *args, **kwargs):
        """
        Get detailed clinic information using service layer.
        GET /clinics/{id}/
        """
        try:
            # Use service method for optimized retrieval with prefetching
            clinic = ClinicService.get_clinic_by_id(
                kwargs["pk"],
                prefetch_doctors=True
            )
            
            if not clinic:
                return self.handle_not_found()
            
            # Get detailed information including related data
            details = ClinicService.get_clinic_details(clinic)
            return Response(details, status=status.HTTP_200_OK)
            
        except ClinicServiceError as e:
            return self.handle_service_error(e, "retrieve clinic")
    
    # ============ Create ============
    
    def create(self, request, *args, **kwargs):
        """
        Create a new clinic using service layer.
        POST /clinics/
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            clinic = ClinicService.create_clinic(
                **serializer.validated_data,
                created_by=request.user,  # User is guaranteed authenticated by permissions
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            
            response_serializer = ClinicSerializer(clinic)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except ClinicServiceError as e:
            return self.handle_service_error(e, "create clinic")
    
    # ============ Update ============
    
    def update(self, request, *args, **kwargs):
        """
        Full update of a clinic using service layer.
        PUT /clinics/{id}/
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        try:
            clinic = ClinicService.update_clinic(
                instance,
                **serializer.validated_data,
                updated_by=request.user,  # User is guaranteed authenticated by permissions
            )
            
            response_serializer = ClinicSerializer(clinic)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except ClinicServiceError as e:
            return self.handle_service_error(e, "update clinic")
    
    def partial_update(self, request, *args, **kwargs):
        """
        Partial update of a clinic.
        PATCH /clinics/{id}/
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    # ============ Delete / Archive ============
    
    def destroy(self, request, *args, **kwargs):
        """
        Archive (soft delete) a clinic using service layer.
        DELETE /clinics/{id}/
        """
        instance = self.get_object()
        
        try:
            ClinicService.archive_clinic(
                instance,
                archived_by=request.user,  # User is guaranteed authenticated by permissions
            )
            
            return Response(
                {'detail': 'Clinic archived successfully.'},
                status=status.HTTP_200_OK
            )
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except ClinicServiceError as e:
            return self.handle_service_error(e, "archive clinic")
    
    # ============ Custom Actions ============
    
    @action(detail=True, methods=['patch'], url_path='toggle-active')
    def toggle_active(self, request, pk=None):
        """
        Toggle clinic active status.
        PATCH /clinics/{id}/toggle-active/
        Body: {"is_active": true/false}
        
        This endpoint replaces the separate activate/deactivate endpoints
        for a cleaner REST API.
        """
        clinic = self.get_object()
        serializer = ClinicActivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        is_active = serializer.validated_data['is_active']
        
        try:
            if is_active:
                updated_clinic = ClinicService.activate_clinic(
                    clinic,
                    activated_by=request.user,
                )
                message = 'Clinic activated successfully.'
            else:
                updated_clinic = ClinicService.deactivate_clinic(
                    clinic,
                    deactivated_by=request.user,
                )
                message = 'Clinic deactivated successfully.'
            
            response_serializer = ClinicSerializer(updated_clinic)
            return Response(
                {
                    'detail': message,
                    'data': response_serializer.data
                },
                status=status.HTTP_200_OK
            )
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except ClinicServiceError as e:
            return self.handle_service_error(e, "toggle clinic status")
    
    @action(
        detail=False,
        methods=['get'],
        url_path='statistics',
        permission_classes=[IsAdminUser]
    )
    def statistics(self, request):
        """
        Get clinic statistics (admin only).
        GET /clinics/statistics/
        """
        try:
            stats = ClinicService.get_statistics()
            return Response(stats, status=status.HTTP_200_OK)
            
        except ClinicServiceError as e:
            return self.handle_service_error(e, "retrieve statistics")
    
    @action(detail=False, methods=['get'], url_path='nearby')
    def nearby(self, request):
        """
        Get clinics near a specific location.
        GET /clinics/nearby/?latitude=-1.286389&longitude=36.817223&radius=10&limit=10
        """
        serializer = ClinicNearbySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Get nearby clinics from service
            clinics = ClinicService.get_nearby_clinics(
                latitude=serializer.validated_data['latitude'],
                longitude=serializer.validated_data['longitude'],
                radius_km=serializer.validated_data.get('radius', 10),
                limit=serializer.validated_data.get('limit', 10),
                only_active=serializer.validated_data.get('only_active', True),
            )
            
            # Extract clinic objects and distances
            clinic_objects = [item['clinic'] for item in clinics]
            distances = {item['clinic'].id: item['distance_km'] for item in clinics}
            doctor_counts = {item['clinic'].id: item.get('doctor_count', 0) for item in clinics}
            
            # Serialize clinics using list serializer
            clinic_serializer = ClinicListSerializer(clinic_objects, many=True)
            results = clinic_serializer.data
            
            # Add distance and doctor count to each result
            for result in results:
                clinic_id = result['id']
                result['distance_km'] = distances.get(clinic_id)
                result['doctor_count'] = doctor_counts.get(clinic_id, 0)
            
            return Response({
                'results': results,
                'count': len(results),
                'radius_km': serializer.validated_data.get('radius', 10),
                'center': {
                    'latitude': serializer.validated_data['latitude'],
                    'longitude': serializer.validated_data['longitude'],
                }
            }, status=status.HTTP_200_OK)
            
        except DjangoValidationError as e:
            return self.handle_validation_error(e)
        except ClinicServiceError as e:
            return self.handle_service_error(e, "find nearby clinics")