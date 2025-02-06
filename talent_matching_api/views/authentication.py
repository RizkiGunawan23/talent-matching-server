from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..serializers import SignUpSerializer, SignInSerializer, CustomTokenSerializer
from rest_framework.permissions import AllowAny


class SignUpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignUpSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.save()
            token_data = CustomTokenSerializer.get_token(user)
            return Response(token_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SignInView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignInSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.validated_data['user']
            token_data = CustomTokenSerializer.get_token(user)
            return Response(token_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgetPasswordView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"message": "get ForgetPasswordApiView"}, status=status.HTTP_200_OK)
