from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from orders.permissions import IsStaff, IsSubscribedUser
from django.http import Http404
from django.shortcuts import get_object_or_404
from .models import Notification
from .serializers import NotificationSerializer


class NotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notificaton = Notification.objects.filter(user = request.user)
        read = request.query_params.get('type', None)
        if read:
            notificaton = notificaton.filter(is_read=read)
        serializer = NotificationSerializer(notificaton, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, id):
        try:
            notification = get_object_or_404(Notification, pk=id, user=request.user)
        except Http404:
            return Response("Not authorized for this operation", status=status.HTTP_401_UNAUTHORIZED)
        notification.is_read = True
        notification.save()
        serializer = NotificationSerializer(notification)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)   