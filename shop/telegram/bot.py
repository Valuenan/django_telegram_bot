import re

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, error
from telegram.ext import Updater, CallbackContext, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from shop.telegram.banking import avangard_invoice
from shop.telegram.db_connection import load_last_order, get_category, get_products, \
    save_order, get_user_orders, edit_to_cart, show_cart, db_delete_cart, get_product_id, start_user, \
    old_cart_message, save_cart_message_id, old_cart_message_to_none, check_user_is_staff, \
    save_delivery_settings, get_delivery_settings, get_user_address, \
    get_shops, user_add_phone, ADMIN_TG, get_user_phone, get_delivery_shop, save_payment_link
from shop.telegram.settings import TOKEN, ORDERS_CHAT_ID
from users.models import ORDER_STATUS
from django_telegram_bot.settings import BASE_DIR, env

LOG_FILENAME = 'bot_log.txt'

updater = Updater(token=TOKEN)
dispatcher = updater.dispatcher

BUTTONS_IN_ROW_CATEGORY = 2
users_message = {}

""" ДЛЯ ПОЛЬЗОВАТЕЛЕЙ """


def main_keyboard(update: Update, context: CallbackContext):
    """Основаня клавиатура снизу"""
    user = update.message.from_user
    text, err = start_user(username=user.username, first_name=user.first_name, last_name=user.last_name,
                           chat_id=update.message.chat_id, cart_message_id=0, discount=1)
    if err == 'ok':
        check = check_user_is_staff(update.message.chat_id)
    elif err == 'no-phone':
        users_message[user.id] = 'phone'

    message = context.bot.send_message(chat_id=update.effective_chat.id, text=text)
    if err != 'ok':
        context.bot.delete_message(chat_id=update.effective_chat.id,
                                   message_id=message.message_id - 1)


start_handler = CommandHandler('start', main_keyboard)
dispatcher.add_handler(start_handler)


def phone_check(update: Update, context: CallbackContext, phone):
    """Основаня клавиатура снизу"""
    user = update.message.from_user

    result = re.match(r'^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$',
                      phone)
    if bool(result):
        user_add_phone(user.id, phone)
        del users_message[user.id]
        message = context.bot.send_message(chat_id=update.message.chat_id,
                                           text=f"""Спасибо, номер телефона принят""")
        context.bot.delete_message(chat_id=update.effective_chat.id,
                                   message_id=message.message_id - 2)
        main_keyboard(update, context)
    else:
        message = context.bot.send_message(chat_id=update.message.chat_id,
                                           text=f"""К сожалению номер {phone}, некоректный повторите ввод или обратитесь к менеджеру {ADMIN_TG} (r1)""")
        context.bot.delete_message(chat_id=update.effective_chat.id,
                                   message_id=message.message_id - 2)


def catalog(update: Update, context: CallbackContext):
    """Вызов каталога по группам"""

    buttons = [[]]
    row = 0
    if update.callback_query:
        call = update.callback_query
        chosen_category = call.data.split('_')

        categories, self_category_name = get_category(int(chosen_category[1]))

    else:
        categories = get_category()
    if categories:
        for index, category in enumerate(categories):
            button = (InlineKeyboardButton(text=category[0], callback_data=f'category_{category[1]}_{category[2]}'))
            if index % BUTTONS_IN_ROW_CATEGORY == 0:
                buttons.append([])
                row += 1
            buttons[row].append(button)
        keyboard = InlineKeyboardMarkup([button for button in buttons])

        if update.callback_query:
            text = f'Категория: {self_category_name[0]}'
        else:
            text = 'Каталог'
        message = context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=text,
                                           reply_markup=keyboard)
        context.bot.delete_message(chat_id=update.effective_chat.id,
                                   message_id=message.message_id - 1)
    else:
        products_catalog(update, context, chosen_category[1])


menu_handler = CommandHandler('catalog', catalog)
dispatcher.add_handler(menu_handler)

catalog_handler = CallbackQueryHandler(catalog, pattern="^" + str('category_'))
dispatcher.add_handler(catalog_handler)


def products_catalog(update: Update, context: CallbackContext, chosen_category=False):
    """Вызов каталога товаров"""
    page = 0
    pagination = False
    call = update.callback_query
    if '#' in str(update.callback_query.data) and not chosen_category:
        chosen_category = update.callback_query.data.split('_')[1]
        chosen_category, page = chosen_category.split('#')
        page = int(page)
    products, pages = get_products(int(chosen_category), page)
    if pages:
        pagination = True
    if products:
        context.bot.delete_message(chat_id=call.message.chat.id,
                                   message_id=call.message.message_id)
        for product in products:
            product_id, product_name, product_img, price, category_id, rests = product
            buttons = ([InlineKeyboardButton(text='Добавить  🟢', callback_data=f'add_{product_id}'),
                        InlineKeyboardButton(text='Убрать 🔴', callback_data=f'remove_{product_id}')],)
            imgs = [product_img]
            try:
                img_reversed = product_img.replace('.', '@rev.')
                open(f'{BASE_DIR}/static/products/{img_reversed}')
                imgs.append(f'{img_reversed}')
            except FileNotFoundError:
                pass

            if len(imgs) > 1:
                compounds_url = f'{BASE_DIR}/static/products/{imgs[1]}'
                buttons[0].append(InlineKeyboardButton(text='Состав', callback_data=f'roll_{compounds_url}'))
            keyboard = InlineKeyboardMarkup([button for button in buttons])

            try:
                product_photo = open(f'{BASE_DIR}/static/products/{imgs[0]}', 'rb')
            except FileNotFoundError:
                product_photo = open(f'{BASE_DIR}/static/products/no-image.jpg', 'rb')
            context.bot.send_photo(chat_id=update.effective_chat.id,
                                   photo=product_photo,
                                   disable_notification=True)
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'{product_name} '
                                                                            f'\n <b>Цена: {price} р.</b>'
                                                                            f'\n <i>Количество: {int(rests)} шт.</i>',
                                     reply_markup=keyboard,
                                     parse_mode='HTML')
        if pagination and page < pages:
            keyboard_next = InlineKeyboardMarkup(
                [[InlineKeyboardButton(text='Еще товары', callback_data=f'product_{chosen_category}#{page + 1}')]])
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f'Страница <b>{page + 1}</b> из {pages + 1}',
                                     disable_notification=True,
                                     reply_markup=keyboard_next, parse_mode='HTML')


    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'В данной категории ненашлось товаров 😨')


catalog_handler = CallbackQueryHandler(products_catalog, pattern="^" + str('product_'))
dispatcher.add_handler(catalog_handler)


def roll_photo(update: Update, context: CallbackContext):
    """Показать фото с составом и обратно"""
    call = update.callback_query

    photo_url = call.data.split('_')[1]
    turn_photo = open(photo_url, 'rb')

    main_inline_kb = call.message.reply_markup.inline_keyboard

    if '@rev' in photo_url:
        main_photo = photo_url.replace('@rev', '')
    else:
        main_photo = photo_url.replace('.', '@rev.')

    buttons = ([[InlineKeyboardButton(text='Добавить  🟢', callback_data=main_inline_kb[0][0]['callback_data']),
                 InlineKeyboardButton(text='Убрать 🔴', callback_data=main_inline_kb[0][1]['callback_data']),
                 InlineKeyboardButton(text='Повернуть', callback_data=f'roll_{main_photo}')]])
    keyboard = InlineKeyboardMarkup([button for button in buttons])
    try:
        context.bot.edit_message_media(
            media=InputMediaPhoto(media=turn_photo),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard)
    except:
        context.bot.send_message(call.message.chat.id, "Состава не оказалось 😨")


roll_photo_handler = CallbackQueryHandler(roll_photo, pattern="^" + str('roll_'))
dispatcher.add_handler(roll_photo_handler)


def edit(update: Update, context: CallbackContext):
    """Добавить/Удаить товар в корзине"""

    call = update.callback_query
    user = call.from_user.id
    command, product_id = call.data.split('_')

    product_amount, product = edit_to_cart(command, user, product_id)
    context.bot.answer_callback_query(callback_query_id=call.id,
                                      text=f'В корзине {product[0]} - {int(product_amount)} шт.')


catalog_handler = CallbackQueryHandler(edit, pattern="^" + str('add_'))
dispatcher.add_handler(catalog_handler)

catalog_handler = CallbackQueryHandler(edit, pattern="^" + str('remove_'))
dispatcher.add_handler(catalog_handler)


def cart(update: Update, context: CallbackContext):
    """Показать корзину покупателя/ Отмена удаления корзины"""
    if update.callback_query:
        call = update.callback_query
        chat_id = call.from_user.id
        if 'return-to-cart_' in call.data:
            messages = call.data.split('_')[1]
            messages = messages.split('-')[0:-1]
            for message_id in messages:
                context.bot.delete_message(chat_id=call.message.chat_id,
                                           message_id=int(message_id))

    else:
        chat_id = update.message.chat_id
        old_cart_message_id = old_cart_message(chat_id)
        try:
            if old_cart_message_id != 0:
                context.bot.delete_message(chat_id=chat_id, message_id=old_cart_message_id)
        except error.BadRequest:
            pass
    cart_info = show_cart(chat_id)
    cart_price = 0

    cart_message = ''
    if len(cart_info) > 0:
        for num, product in enumerate(cart_info):
            product_name, amount, price = product
            cart_price += round(price * amount, 2)
            cart_message += f'{num + 1}. {product_name} - {int(amount)} шт. по {price} р.\n'
        else:
            cart_message += f'Итого: {cart_price} р.'

        buttons = ([InlineKeyboardButton(text='Оформить заказ 📝', callback_data='offer-stage_1_none')],
                   [InlineKeyboardButton(text='Очистить 🗑️', callback_data='delete-cart'),
                    InlineKeyboardButton(text='Редактировать 📋', callback_data='correct-cart')])

        keyboard = InlineKeyboardMarkup([button for button in buttons])

        if update.callback_query:
            chat_id = update.callback_query.message.chat_id
            message_id = update.callback_query.message.message_id
            try:
                message = context.bot.edit_message_text(chat_id=chat_id,
                                                        message_id=message_id,
                                                        text=cart_message,
                                                        reply_markup=keyboard)
            except error.BadRequest:
                pass
            else:
                old_cart_message_to_none(chat_id)


        else:
            message = context.bot.send_message(chat_id=update.effective_chat.id,
                                               text=cart_message,
                                               reply_markup=keyboard)
            context.bot.delete_message(chat_id=update.effective_chat.id,
                                       message_id=message.message_id - 1)

    else:

        message = context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='Корзина пустая')

        context.bot.delete_message(chat_id=update.effective_chat.id,
                                   message_id=message.message_id - 1)
    try:
        save_cart_message_id(message.chat_id, message.message_id)
    except ReferenceError:
        pass


cart_handler = CommandHandler('cart', cart)
dispatcher.add_handler(cart_handler)

cancel_cart_handler = CallbackQueryHandler(cart, pattern=str('cancel-delete-cart'))
dispatcher.add_handler(cancel_cart_handler)

return_cart_handler = CallbackQueryHandler(cart, pattern="^" + str('return-to-cart_'))
dispatcher.add_handler(return_cart_handler)


def get_offer_settings(update: Update, context: CallbackContext):
    """Настройки заказа (доставка, вид оплаты, магазин)"""
    global users_message
    call = update.callback_query
    chat_id = update.effective_chat.id
    message_id = call.message.message_id
    _, settings_stage, answer = call.data.split('_')


    if not get_user_phone(chat_id):
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Для оформления заказа требуется ваш номер телефона, напишите его в чат')
    else:
        if settings_stage == '1':
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Да', callback_data='offer-stage_2_yes'),
                                              InlineKeyboardButton(text='Нет', callback_data='offer-stage_2_no')]])
            context.bot.edit_message_text(chat_id=chat_id,
                                          message_id=message_id,
                                          text=f'Вам доставить? 🚚 (доставка будет расчитана после оформления заказа)',
                                          reply_markup=keyboard)
        elif settings_stage == '2' and answer == 'yes':
            save_delivery_settings(value='1', field='delivery', chat_id=chat_id)
            users_message[chat_id] = ''
            street = get_user_address(chat_id)
            buttons = [[InlineKeyboardButton(text='Сохранить адрес 📝', callback_data='offer-stage_3_none')]]
            if street:
                buttons.insert(0, [InlineKeyboardButton(text=street, callback_data=f'offer-stage_3_street')])
            keyboard = InlineKeyboardMarkup(buttons)
            context.bot.edit_message_text(chat_id=chat_id,
                                          message_id=message_id,
                                          text=f'Отправьте сообщение с адресом доставки, а затем нажмите кнопку в этом сообщении "Сохранить адрес  📝"'
                                               f' или выберите последний адрес доставки',
                                          reply_markup=keyboard)
        elif settings_stage == '2' and answer == 'no':
            save_delivery_settings(value='0', field='delivery', chat_id=chat_id)
            buttons = []
            for shop in get_shops():
                shop_id, shop_name = shop
                buttons.append(InlineKeyboardButton(text=shop_name, callback_data=f'offer-stage_3_{shop_id}'))
            keyboard = InlineKeyboardMarkup([buttons])
            context.bot.edit_message_text(chat_id=chat_id,
                                          message_id=message_id,
                                          text=f'Выберите предпочтительный магазин',
                                          reply_markup=keyboard)

        elif settings_stage == '3':
            break_flag = False
            if answer == 'none':
                if users_message[chat_id]:
                    save_delivery_settings(value=users_message[chat_id], field='delivery_street', chat_id=chat_id)
                    save_delivery_settings(value='1', field='delivery', chat_id=chat_id)
                    users_message.pop(chat_id)
                else:
                    street = get_user_address(chat_id)
                    buttons = [[InlineKeyboardButton(text='Сохранить адрес 📝', callback_data='offer-stage_3_none')]]
                    keyboard = InlineKeyboardMarkup(buttons)
                    if street:
                        buttons.insert(0, [InlineKeyboardButton(text=street, callback_data=f'offer-stage_3_street')])
                    context.bot.edit_message_text(chat_id=chat_id,
                                                  message_id=message_id,
                                                  text=f'Нужно указать адрес. Для этого отправьте в чат сообщение с адресом а потом нажмите "Сохранить адрес 📝"',
                                                  reply_markup=keyboard)
                    break_flag = True

            elif answer == 'street':
                save_delivery_settings(value='1', field='delivery', chat_id=chat_id)
            else:
                answer = int(answer)
                save_delivery_settings(value=answer, field='main_shop_id', chat_id=chat_id)
                save_delivery_settings(value='0', field='delivery', chat_id=chat_id)

            if not break_flag:
                # Оплата: 2 - qr код, 1 - ввод карты
                keyboard = InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text='Через банковское приложение', callback_data=f'offer-stage_4_2')],
                     [InlineKeyboardButton(text='Ввести реквизиты карты', callback_data=f'offer-stage_4_1')]])

                context.bot.edit_message_text(chat_id=chat_id,
                                              message_id=message_id,
                                              text=f'''Выберите вид оплаты:''',
                                              reply_markup=keyboard)

        elif settings_stage == '4':
            delivery_settings = _user_settings_from_db(chat_id)

            cart_price = 0
            cart_info = show_cart(chat_id)

            for num, product in enumerate(cart_info):
                product_name, amount, price = product
                cart_price += round(price * amount, 2)

            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(text='Заказать 🛍', callback_data=f'order_{cart_price}_{answer}')],
                 [InlineKeyboardButton(text='Редктировать 📝',
                                       callback_data=f'offer-stage_1_none')]])

            context.bot.edit_message_text(chat_id=chat_id,
                                          message_id=message_id,
                                          text=f'{delivery_settings}',
                                          reply_markup=keyboard)


offer_settings = CallbackQueryHandler(get_offer_settings, pattern=str('offer-stage'))
dispatcher.add_handler(offer_settings)


def _user_settings_from_db(chat_id: int) -> str:
    """ Настроки заказа """

    delivery, delivery_street = get_delivery_settings(chat_id)

    if delivery:
        text = f'Доставка по адресу {delivery_street}'
    else:
        shop_name = get_delivery_shop(chat_id)
        text = f'Товары зарезервированы в магазине {shop_name} '

    return text


def edit_cart(update: Update, context: CallbackContext):
    """Редактирование товаров в корзине"""
    call = update.callback_query
    chat_id = call.message.chat_id
    message_id = call.message.message_id
    command, product_id = call.data.split('_')
    amount, product = edit_to_cart(command, chat_id, product_id)
    message = f'{product[0]} - {int(amount)} шт.'
    if amount > 0:
        buttons = ([InlineKeyboardButton(text='Добавить  🟢', callback_data=f'add-cart_{product_id}'),
                    InlineKeyboardButton(text='Убрать 🔴', callback_data=f'remove-cart_{product_id}')],)
        keyboard_edit = InlineKeyboardMarkup([button for button in buttons])
        try:
            context.bot.edit_message_text(chat_id=chat_id,
                                          message_id=message_id,
                                          text=message,
                                          reply_markup=keyboard_edit)
        except error.BadRequest:
            pass
    else:
        keyboard_edit = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text='Добавить  🟢', callback_data=f'add-cart_{product_id}')]])
        context.bot.edit_message_text(chat_id=chat_id,
                                      message_id=message_id,
                                      text=message,
                                      reply_markup=keyboard_edit)


edit_cart_handler = CallbackQueryHandler(edit_cart, pattern="^" + str('add-cart_'))
dispatcher.add_handler(edit_cart_handler)

catalog_handler = CallbackQueryHandler(edit_cart, pattern="^" + str('remove-cart_'))
dispatcher.add_handler(catalog_handler)


def start_edit(update: Update, context: CallbackContext):
    """Список товаров для редактирования и выход из редактирования"""
    messages_ids = ''
    chat_id = update.callback_query.message.chat_id
    cart_info = show_cart(chat_id)
    message_id = update.callback_query.message.message_id
    context.bot.delete_message(chat_id=chat_id,
                               message_id=message_id)
    if len(cart_info) > 0:
        for product in cart_info:
            product_name, amount, price = product
            product_id = get_product_id(product_name)[0]
            buttons = ([InlineKeyboardButton(text='Добавить  🟢', callback_data=f'add-cart_{product_id}'),
                        InlineKeyboardButton(text='Убрать 🔴', callback_data=f'remove-cart_{product_id}')],)
            keyboard_edit = InlineKeyboardMarkup([button for button in buttons])
            message = f'{product_name} - {int(amount)} шт. по {price} р.\n'
            message = context.bot.send_message(chat_id=chat_id,
                                               text=message,
                                               reply_markup=keyboard_edit)
            messages_ids += f'{message.message_id}-'

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text='Обновить', callback_data=f'return-to-cart_{messages_ids}')]])

        context.bot.send_message(chat_id=chat_id,
                                 text=f'Для посчета суммы нажмите обновить',
                                 reply_markup=keyboard)


cart_list_handler = CallbackQueryHandler(start_edit, pattern=str('correct-cart'))
dispatcher.add_handler(cart_list_handler)


def order(update: Update, context: CallbackContext):
    """Оформить заявку (переслать в канал менеджеров)"""
    call = update.callback_query
    chat_id = call.message.chat_id
    user = call.message.chat.username
    order_num = load_last_order()
    command, cart_price, payment_type = call.data.split('_')
    order_products, order_price = save_order(chat_id, call.message.text, cart_price, int(payment_type))
    text_products = ''
    for product_name, product_amount in order_products:
        text_products += f'\n{product_name[0]} - {int(product_amount)} шт.'
    order_message = f'<b><u>Заказ №: {order_num}</u></b> \n {text_products} \n {call.message.text} \n <b>на сумму: {cart_price}</b>'
    context.bot.answer_callback_query(callback_query_id=call.id,
                                      text=f'Ваш заказ принят')
    context.bot.edit_message_text(text=f'Клиент: {user} \n{order_message}',
                                  chat_id=call.message.chat.id,
                                  message_id=call.message.message_id, parse_mode='HTML')
    context.bot.forward_message(chat_id=ORDERS_CHAT_ID,
                                from_chat_id=call.message.chat_id,
                                message_id=call.message.message_id)
    context.bot.edit_message_text(text=f'Ваш {order_message}',
                                  chat_id=call.message.chat.id,
                                  message_id=call.message.message_id, parse_mode='HTML')


order_cart_handler = CallbackQueryHandler(order, pattern=str('order_'))
dispatcher.add_handler(order_cart_handler)


def delete_cart(update: Update, context: CallbackContext):
    """Очистить корзину"""
    call = update.callback_query

    buttons = ([InlineKeyboardButton(text='Вернуться ❌', callback_data='cancel-delete-cart'),
                InlineKeyboardButton(text='Удалить ✔️', callback_data='accept-delete-cart')],)

    keyboard = InlineKeyboardMarkup([button for button in buttons])

    message = context.bot.edit_message_text(chat_id=call.message.chat.id,
                                            message_id=call.message.message_id,
                                            text='⚠️Вы уверены что хотите удалить корзину ⚠️',
                                            reply_markup=keyboard)
    save_cart_message_id(message.chat_id, message.message_id)


delete_cart_handler = CallbackQueryHandler(delete_cart, pattern=str('delete-cart'))
dispatcher.add_handler(delete_cart_handler)


def accept_delete_cart(update: Update, context: CallbackContext):
    """Подтвердить удаление корзины"""

    call = update.callback_query
    chat_id = call.message.chat_id
    db_delete_cart(chat_id)
    context.bot.delete_message(chat_id=call.message.chat.id,
                               message_id=call.message.message_id)
    context.bot.answer_callback_query(callback_query_id=call.id, text=f'Корзина очищена')


accept_cart_handler = CallbackQueryHandler(accept_delete_cart, pattern=str('accept-delete-cart'))
dispatcher.add_handler(accept_cart_handler)


def orders_history(update: Update, context: CallbackContext):
    """Вызов истории покупок (в статусе кроме исполненно или отменено)"""
    chat_id = update.effective_chat.id

    orders = get_user_orders(chat_id, 'AND orders.status_id NOT IN (6,7)')
    orders.sort()

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Закрыть', callback_data='remove-message')]])

    if not orders:
        message = context.bot.send_message(chat_id=chat_id,
                                           text='У вас нет заказов',
                                           reply_markup=keyboard)
    else:
        prev_id = None
        text = ''
        url_list = {}

        for order in orders:
            order_id, product_name, product_price, product_amount, order_sum, order_status, payment_url = order
            url_list[order_id] = payment_url

            if not prev_id:
                position = 1
                prev_id, prev_sum, prev_status = order_id, order_sum, order_status
                order_products = [f'<i>{position}.</i> {product_name} - {int(product_amount)} шт. по {product_price}р.']
            elif prev_id == order_id:
                order_products.append(
                    f'<i>{position}.</i> {product_name} - {int(product_amount)} шт. по {product_price}р.')
            position += 1

            if prev_id != order_id:
                position = 1
                text_products = '\n'.join(order_products)
                text += f'''<b><u>Заказ № {prev_id}</u></b>\n <u>Статус заказа: {ORDER_STATUS[int(prev_status)][1]}</u> \n {text_products} \n <b>на сумму:{prev_sum} р.</b>'''
                if prev_status == '1' and url_list and prev_id in url_list:
                    text += f'\n ссылка на оплату (чек): {url_list[prev_id]}'
                text += f'\n {"_" * 20} \n'

                order_products = [f'<i>{position}.</i> {product_name} - {int(product_amount)} шт. по {product_price}р.']
                prev_id, prev_sum, prev_status = order_id, order_sum, order_status


        else:
            text_products = '\n'.join(order_products)
            text += f'''<b><u>Заказ № {order_id}</u></b> \n <u>Статус заказа: {ORDER_STATUS[int(order_status)][1]}</u> \n {text_products} \n <b>на сумму: {order_sum} р.</b>'''
            if order_status == '1' and url_list and order_id in url_list:
                text += f'\n ссылка на оплату (чек): {url_list[order_id]}'
            text += f'\n {"_" * 20} \n'

        if update.callback_query:
            context.bot.edit_message_text(chat_id=chat_id,
                                          text=text,
                                          reply_markup=keyboard, parse_mode='HTML',
                                          message_id=update.callback_query.message.message_id, )
        else:
            message = context.bot.send_message(chat_id=chat_id,
                                               text=text,
                                               reply_markup=keyboard, parse_mode='HTML')
    if not update.callback_query:
        context.bot.delete_message(chat_id=chat_id,
                                   message_id=message.message_id - 1)


orders_history_handler = CommandHandler('orders', orders_history)
dispatcher.add_handler(orders_history_handler)

accept_cart_handler = CallbackQueryHandler(accept_delete_cart, pattern=str('history_orders'))
dispatcher.add_handler(accept_cart_handler)


def unknown(update: Update, context: CallbackContext):
    """Неизветсные команды"""
    context.bot.send_message(chat_id=update.effective_chat.id, text="Извините, я не знаю такой команды")


unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler)

""" АДМИНИСТРАТИВНЫЕ """


def ready_order_message(chat_id: int, order_id: int, order_sum: int, status: str, delivery_price: int = 0, pay_type: int = 1,tracing_num: str = 'нет'):
    """Сообщение о готовности заказа"""
    message = ''
    if status == '1':
        invoice_num, link = avangard_invoice(title=f'(Заказ в магазине OttudaSPB № {order_id}, сумма {order_sum} р.)',
                                             price=order_sum,
                                             customer=f'{chat_id}',
                                             shop_order_num=order_id,
                                             pay_type=pay_type)
        save_payment_link(order_id, link)
        if delivery_price == 0:
            message = f'''ожидает оплаты
ваша ссылка на оплату: {link}'''
        else:
            message = f''',в том числе доставка на сумму {delivery_price} р., <u> ожидает оплаты </u>
ваша ссылка на оплату: {link}'''
    elif status == '3':
        message = f'поступил в доставку, трек номер: {tracing_num}'
    elif status == '4':
        message = 'ожидает вас в магазине'
    elif status == '6':
        message = 'был отменен'
    updater.bot.send_message(chat_id=chat_id,
                             text=f'Ваш заказ № {order_id} на сумму {order_sum} р. {message}',
                             parse_mode='HTML')


# Оплата интегрированными средставми телеграм

# def buy_invoice(label, amount, chat_id):
#     prices = [LabeledPrice(label=label, amount=amount)]
#     provider_token = settings.PAYMENTS_TOKEN
#     if provider_token.split(':')[1] == 'TEST':
#         updater.bot.send_message(chat_id=chat_id, text=f'ТЕСТОВЫЙ ПЛАТЕЖ!!!')
#
#     updater.bot.send_invoice(chat_id=chat_id,
#                              title=label,
#                              description='Описание',
#                              payload='Finshop_3',
#                              provider_token=provider_token,
#                              currency='RUB',
#                              prices=prices,
#                              is_flexible=False,
#                              start_parameter='start_parameter',
#                              )
#
#
# def precheckout_callback(update: Update, context: CallbackContext):
#     query = update.pre_checkout_query
#     if query.invoice_payload != "Finshop_3":
#         query.answer(ok=False, error_message="Something went wrong...")
#     else:
#         query.answer(ok=True)
#
#
# dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))
#
#
# def successful_payment_callback(update: Update, context: CallbackContext):
#     chat_id = update.message.chat_id
#     order_sum = int(update.message.successful_payment.total_amount / 100)
#     order_payed(chat_id=chat_id, order_sum=order_sum)
#     update.message.reply_text("Оплата успешно принята")

#
# dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))

""" Утилиты """


def user_message(update: Update, context: CallbackContext):
    """Принять сообщение пользователя (телефон, адрес)"""
    chat_id = update.message.chat_id
    if chat_id in users_message:
        if users_message[chat_id] == 'phone':
            phone_check(update=update, context=context, phone=update.message.text)
        elif users_message[chat_id] == '':
            users_message[chat_id] = update.message.text
    else:
        pass


get_user_message = MessageHandler(Filters.text, user_message)
dispatcher.add_handler(get_user_message)


def remove_bot_message(update: Update, context: CallbackContext):
    """Закрыть сообщение бота"""
    call = update.callback_query
    context.bot.delete_message(chat_id=call.message.chat.id,
                               message_id=call.message.message_id)


remove_message = CallbackQueryHandler(remove_bot_message, pattern=str('remove-message'))
dispatcher.add_handler(remove_message)

if __name__ == '__main__':
    updater.start_polling()
