from shop.telegram.bot import send_message_to_user
from django.db import Error as DbError
from django.db.transaction import Error as TransactionError

from users.models import UserMessage


def _send_message_to_user(form, user_chat_id, manager=None, everyone=False) -> tuple:
    if 'disable_notification' in form:
        disable_notification = True
    else:
        disable_notification = False

    try:
        print(form)
        if form['message'] and not everyone:
            UserMessage.objects.create(user=user_chat_id, manager=manager, message=form['message'],
                                       checked=True)
            user_chat_id = user_chat_id.chat_id
        if type(form['message']) == list:
            form['message'] = form['message'][0]
        result, text = send_message_to_user(chat_id=user_chat_id, message=form['message'],
                                            disable_notification=disable_notification)

        if result == 'ok':
            return 'success', text
        else:
            return 'error', f'Сообщение не отправлено пользователю ид {user_chat_id}, {text}. Обратитесь к администратору'
    except (DbError, TransactionError) as error:
        return 'error', f'Возникла ошибка ид пользователя {user_chat_id}, {error}. Обратитесь к администратору'
