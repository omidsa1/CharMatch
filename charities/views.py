from rest_framework import status, generics
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCharityOwner, IsBenefactor
from charities.models import Task, Benefactor
from charities.serializers import (
    TaskSerializer, CharitySerializer, BenefactorSerializer
)


class BenefactorRegistration(APIView):
    def post(self, request):
        serializer = BenefactorSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CharityRegistration(APIView):
    def post(self, request):
        serializer = CharitySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class Tasks(generics.ListCreateAPIView):
    serializer_class = TaskSerializer

    def get_queryset(self):
        return Task.objects.all_related_tasks_to_user(self.request.user)

    def post(self, request, *args, **kwargs):
        data = {
            **request.data,
            "charity_id": request.user.charity.id
        }
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            self.permission_classes = [IsAuthenticated, ]
        else:
            self.permission_classes = [IsCharityOwner, ]

        return [permission() for permission in self.permission_classes]

    def filter_queryset(self, queryset):
        filter_lookups = {}
        for name, value in Task.filtering_lookups:
            param = self.request.GET.get(value)
            if param:
                filter_lookups[name] = param
        exclude_lookups = {}
        for name, value in Task.excluding_lookups:
            param = self.request.GET.get(value)
            if param:
                exclude_lookups[name] = param

        return queryset.filter(**filter_lookups).exclude(**exclude_lookups)


class TaskRequest(APIView):
    def get(self, request, task_id):
        if request.user.is_benefactor:
            try:
                task = Task.objects.get(id=task_id)
            except Task.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
            if task.state != 'P':
                return Response(data={'detail': 'This task is not pending.'}, status=status.HTTP_404_NOT_FOUND)
            else:
                task.state = "W"
                task.assigned_benefactor = Benefactor.objects.get(user=request.user)
                task.save()
                return Response(data={'detail': 'Request sent.'}, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)


class TaskResponse(APIView):
    def post(self,request,task_id):
        if request.user.is_charity:
            task = Task.objects.get(id=task_id)
            if request.data["response"] not in ['R', 'A']:
                return Response(data={'detail': 'Required field ("A" for accepted / "R" for rejected)'},
                                status=status.HTTP_400_BAD_REQUEST)
            if task.state != "W":
                return Response(data={'detail': 'This task is not waiting.'}, status=status.HTTP_404_NOT_FOUND)

            if request.data["response"] == "A":
                task.state = "A"
                task.save()
                return Response(data={'detail': 'Response sent.'}, status=status.HTTP_200_OK)

            if request.data["response"] == "R":
                task.state = "P"
                task.assigned_benefactor = None
                task.save()
                return Response(data={'detail': 'Response sent.'}, status=status.HTTP_200_OK)

        return Response(status=status.HTTP_403_FORBIDDEN)




class DoneTask(APIView):
    def post(self,request,task_id):
        if request.user.is_charity:
            try:
                task = Task.objects.get(id=task_id)
            except Task.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

            if task.state != "A":
                return Response(data={'detail': 'Task is not assigned yet.'},
                                status=status.HTTP_404_NOT_FOUND)
            else:
                task.state = "D"
                task.save()
                return Response(data={'detail': 'Task has been done successfully.'},
                                status=status.HTTP_200_OK)

        return Response(status=status.HTTP_403_FORBIDDEN)

