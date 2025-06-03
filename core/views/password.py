from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.serializers.password import ChangePasswordSerializer


class ChangePasswordView(APIView):
    """API untuk mengubah password user"""
    permission_classes = [AllowAny]

    def post(self, request):
        """Change user password"""
        try:
            serializer = ChangePasswordSerializer(
                data=request.data, 
                context={'request': request}
            )
            
            if serializer.is_valid():
                # Save new password
                serializer.save()
                
                return Response({
                    'success': True,
                    'message': 'Password berhasil diubah'
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)