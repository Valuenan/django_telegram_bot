from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
import json

from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from .forms import CreateUserForm

from users.models import Profile


@ensure_csrf_cookie
@require_http_methods(['GET'])
def set_csrf_token(request):
    """
    We set the CSRF cookie on the frontend.
    """
    return JsonResponse({'message': 'CSRF cookie set'})


@require_http_methods(['POST'])
def login_user(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        email = data['email']
        password = data['password']
    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'message': 'Invalid JSON'}, status=400
        )

    user = authenticate(request, username=email, password=password)

    if user:
        login(request, user)
        return JsonResponse({'success': True})
    return JsonResponse(
        {'success': False, 'message': 'Invalid credentials'}, status=401
    )


def logout_view(request):
    logout(request)
    return JsonResponse({'message': 'Logged out'})


@require_http_methods(['GET'])
def user(request, pk):
    user_profile = Profile.objects.filter(chat_id=pk)

    if user_profile:
        user_profile = user_profile[0]
        return JsonResponse(
            {'telegram_name': user_profile.telegram_name, 'first_name': user_profile.first_name,
             'last_name': user_profile.last_name, 'phone': user_profile.phone, 'result': 'returned'}, status=200
        )
    else:
        user_profile = Profile.objects.create(chat_id=pk)
        return JsonResponse(
            {'telegram_name': user_profile.telegram_name, 'first_name': user_profile.first_name,
             'last_name': user_profile.last_name, 'phone': user_profile.phone, 'result': 'crated'}, status=200
        )


@require_http_methods(['GET'])
def catalog(request):

    return JsonResponse({'success': 'ok'}, status=200)


@require_http_methods(['POST'])
def user_edit(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        tg_user = data
        user_profile = Profile.objects.get(chat_id=tg_user['chat_id'])
        for key, value in data.items():
            setattr(user_profile, key, value)
        user_profile.save()

        return JsonResponse(
            {'success': True, 'message': 'Successfully changed'}, status=200
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'message': 'Invalid JSON'}, status=400
        )


@require_http_methods(['POST'])
def profile(request):
    data = json.loads(request.body.decode('utf-8'))
    print(data)
    user_profile = Profile.objects.filter(chat_id=data.id)
    print(user_profile)

    return JsonResponse({'success': 'Returning user profile...'}, status=200)
    # if form.is_valid():
    #     form.save()
    #     return JsonResponse({'success': 'Returning user profile...'}, status=200)
    # else:
    #     errors = form.errors.as_json()
    #     return JsonResponse({'error': errors}, status=400)
