from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
import json
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login, logout

from api.utils import verify_telegram_data  # импортируй функцию проверки
from django.conf import settings
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


@require_http_methods(['GET', 'POST'])
def user(request, pk=None):
    # 1. Попытка достать пользователя через Telegram initData (безопасно)
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('twa '):
        init_data = auth_header.replace('twa ', '')
        tg_user = verify_telegram_data(init_data, settings.BOT_TOKEN)
        if tg_user:
            pk = tg_user.get('id')  # Берем ID прямо из проверенных данных Telegram

    # 2. Если ID все еще нет (зашли не через Mini App)
    if pk is None:
        return JsonResponse({'error': 'ID не указан'}, status=400)

    # 3. Ищем или создаем профиль
    user_profile, created = Profile.objects.get_or_create(chat_id=pk)

    return JsonResponse({
        'id': user_profile.chat_id,
        'first_name': user_profile.first_name or tg_user.get('first_name') if 'tg_user' in locals() else '',
        'telegram_name': user_profile.telegram_name,
        'result': 'created' if created else 'returned'
    }, status=200)


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
