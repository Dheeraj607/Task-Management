from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.dateparse import parse_date
from rest_framework import permissions, status, generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .forms import SimpleUserForm, TaskForm, TaskEditForm, UserEditForm
from .models import Task, CustomUser
from .decorators import admin_required, super_admin_required, admin_or_super_admin_required
from .serializers import LoginSerializer, TaskSerializer, TaskUpdateSerializer
from .permissions import IsUser, IsAdminOrSuperAdmin
###
def home_page(request):
    if request.method == 'POST':
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, "home_page.html")


@login_required(login_url='home_page')
def dashboard(request):
    return render(request, "dashboard.html")

@login_required(login_url='home_page')
def user_logout(request):
    logout(request)
    return redirect("home_page")

@super_admin_required
def register(request):
    if request.method == "POST":
        form = SimpleUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.password = make_password(form.cleaned_data["password1"])  # save hashed password
            user.save()
            messages.success(request, "User account created successfully.")
            return redirect("dashboard")
    else:
        form = SimpleUserForm()
    return render(request, "register.html", {"form": form})


@super_admin_required
def create_task(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.assigned_by = request.user
            task.save()
            messages.success(request, "Task created successfully!")
            return redirect("dashboard")
    else:
        form = TaskForm()
    return render(request, "create_task.html", {"form": form})



@login_required(login_url="home_page")
def task_list(request):
    user = request.user

    if user.role == "super_admin":
        tasks = Task.objects.all()
    elif user.role == "admin":
        tasks = Task.objects.filter(Q(assigned_by=user) | Q(assigned_to=user))
    else:
        tasks = Task.objects.filter(assigned_to=user)

    title = request.GET.get("title")
    status = request.GET.get("status")
    assigned_by = request.GET.get("assigned_by")
    assigned_to = request.GET.get("assigned_to")
    due_start = request.GET.get("due_start")
    due_end = request.GET.get("due_end")

    if title:
        tasks = tasks.filter(title__icontains=title)
    if status and status != "all":
        tasks = tasks.filter(status=status)
    if assigned_by:
        tasks = tasks.filter(assigned_by__username__icontains=assigned_by)
    if assigned_to:
        tasks = tasks.filter(assigned_to__username__icontains=assigned_to)
    if due_start:
        start_date = parse_date(due_start)
        if start_date:
            tasks = tasks.filter(due_date__gte=start_date)
    if due_end:
        end_date = parse_date(due_end)
        if end_date:
            tasks = tasks.filter(due_date__lte=end_date)

    return render(request, "task_list.html", {"tasks": tasks.order_by('-created_at')})



@admin_or_super_admin_required
def user_list(request):
    user = request.user

    if user.role == "super_admin":
        users = CustomUser.objects.all()
    elif user.role == "admin":
        users = CustomUser.objects.exclude(role="super_admin")  # see admins and users
    else:
        messages.error(request, "You do not have permission to view this page.")
        return redirect("dashboard")

    username = request.GET.get("username")
    role = request.GET.get("role")
    if username:
        users = users.filter(username__icontains=username)
    if role and role != "all":
        users = users.filter(role=role)
    return render(request, "user_list.html", {"users": users})


@login_required(login_url="home_page")
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk)
    user = request.user

    if user.role == "user" and task.assigned_to != user:
        messages.error(request, "You do not have permission to view this task.")
        return redirect("task_list")

    return render(request, "task_detail.html", {"task": task})



@login_required(login_url="home_page")
def edit_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    user = request.user

    if user.role == "user" and task.assigned_to != user:
        messages.error(request, "You cannot edit this task.")
        return redirect("task_list")

    if request.method == "POST":
        form = TaskEditForm(request.POST, instance=task, user=user)
        if form.is_valid():
            updated_task = form.save(commit=False)

            if user.role == "user":
                updated_task.assigned_to = task.assigned_to
                if updated_task.status == "completed":
                    if not updated_task.completion_report or not updated_task.worked_hours:
                        messages.error(request, "Please provide both Worked Hours and Completion Report before marking completed.")
                        return render(request, "task_edit.html", {"form": form, "task": task})

            elif user.role == "admin":
                updated_task.assigned_by = user  # if admin changes assigned_to

            updated_task.save()
            messages.success(request, "Task updated successfully.")
            return redirect("task_detail", pk=task.pk)
    else:
        form = TaskEditForm(instance=task, user=user)
    return render(request, "task_edit.html", {"form": form, "task": task})



@super_admin_required
def delete_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    user = request.user

    if user.role != "super_admin":
        messages.error(request, "Only Super Admin can delete tasks.")
        return redirect("task_detail", pk=task.pk)

    if request.method == "POST":
        task.delete()
        messages.success(request, "Task deleted successfully.")
        return redirect("task_list")

    return render(request, "task_delete_confirm.html", {"task": task})



@admin_or_super_admin_required
def user_detail(request, pk):
    user = request.user
    target_user = get_object_or_404(CustomUser, pk=pk)

    if user.role not in ["admin", "super_admin"]:
        messages.error(request, "You do not have permission to view user details.")
        return redirect("dashboard")

    return render(request, "user_detail.html", {"target_user": target_user})



@super_admin_required
def user_edit(request, pk):
    user = request.user
    target_user = get_object_or_404(CustomUser, pk=pk)

    if user.role != "super_admin":
        messages.error(request, "Only Super Admin can update user details.")
        return redirect("user_detail", pk=target_user.pk)

    if request.method == "POST":
        form = UserEditForm(request.POST, instance=target_user)
        if form.is_valid():
            form.save()
            messages.success(request, "User updated successfully.")
            return redirect("user_detail", pk=target_user.pk)
    else:
        form = UserEditForm(instance=target_user)

    return render(request, "user_edit.html", {"form": form, "target_user": target_user})


@super_admin_required
def user_delete(request, pk):
    user = request.user
    target_user = get_object_or_404(CustomUser, pk=pk)

    if user.role != "super_admin":
        messages.error(request, "Only Super Admin can delete users.")
        return redirect("user_detail", pk=target_user.pk)

    if request.method == "POST":
        target_user.delete()
        messages.success(request, "User deleted successfully.")
        return redirect("user_list")

    return render(request, "user_delete_confirm.html", {"target_user": target_user})


@admin_or_super_admin_required
def completed_tasks(request):
    tasks = Task.objects.filter(status="completed").order_by("-updated_at")
    if request.user.role == "admin":
        tasks = tasks.filter(assigned_by=request.user)
    return render(request, "completed_tasks.html", {"tasks": tasks})



# REST APIs

class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        user = authenticate(username=username, password=password)

        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "role": user.role
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid credentials"},
                            status=status.HTTP_401_UNAUTHORIZED)

class UserTaskListAPIView(generics.ListAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsUser]

    def get_queryset(self):
        user = self.request.user
        return Task.objects.filter(assigned_to=user).order_by("-updated_at")


class TaskUpdateAPIView(generics.UpdateAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskUpdateSerializer
    permission_classes = [IsUser]

    def get_object(self):
        task = super().get_object()
        user = self.request.user

        # Only assigned user can update their task
        if task.assigned_to != user:
            raise PermissionDenied("You can only update tasks assigned to you.")
        return task


class CompletedTaskListAPIView(generics.ListAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.role == "super_admin":
            return Task.objects.filter(status="completed")

        elif user.role == "admin":
            return Task.objects.filter(status="completed").filter(
                Q(assigned_to=user) | Q(assigned_by=user)
            )
        raise PermissionDenied("You are not authorized to view completed tasks.")