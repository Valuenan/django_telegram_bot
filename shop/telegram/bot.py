import logging

import telegram
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, InputMediaPhoto, \
    KeyboardButton
from telegram.ext import Updater, CallbackContext, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, \
    PollAnswerHandler

from shop.telegram.db_connection import load_last_order, get_category, get_products, \
    save_order, get_user_orders, edit_to_cart, show_cart, db_delete_cart, get_product_id, start_user, \
    old_cart_message, save_cart_message_id, old_cart_message_to_none, check_user_is_staff, get_waiting_orders, \
    get_user_id_chat, soft_delete_confirmed_order, save_delivery_settings, get_delivery_settings, get_user_address, \
    get_shops
from shop.telegram.settings import TOKEN, ORDERS_CHAT_ID
from django_telegram_bot.settings import BASE_DIR

users_message = {}

updater = Updater(token=TOKEN)
dispatcher = updater.dispatcher

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

""" ДЛЯ ПОЛЬЗОВАТЕЛЕЙ """


def main_keyboard(update: Update, context: CallbackContext):
    """Основаня клавиатура снизу"""
    user = update.message.from_user
    button_column = [[KeyboardButton(text='Меню'), KeyboardButton(text='Корзина')], [KeyboardButton(text='Мои заказы')]]
    check = check_user_is_staff(update.message.chat_id)
    if check is not None and check[0]:
        button_column.append([KeyboardButton(text='Подтвердить заказ'), KeyboardButton(text='Отменить заказ')])
    main_kb = ReplyKeyboardMarkup([button for button in button_column], resize_keyboard=True)
    text, err = start_user(user.first_name, user.last_name, user.username,
                           update.message.chat_id, cart_message_id=0, discount=1)
    if err != 'ok':
        logger.info(f"User %s 'start' {update.message.chat_id},{user.username}. error - {err}")
    message = context.bot.send_message(chat_id=update.effective_chat.id, text=text,
                                       reply_markup=main_kb)
    context.bot.delete_message(chat_id=update.effective_chat.id,
                               message_id=message.message_id - 1)


start_handler = CommandHandler('start', main_keyboard)
dispatcher.add_handler(start_handler)


def catalog(update: Update, context: CallbackContext):
    """Вызов каталога по группам"""
    user = update.message.from_user
    logger.info("User %s open catalog", user.first_name)
    buttons_in_row = 3
    buttons = [[]]
    row = 0
    for category in get_category():
        button = (InlineKeyboardButton(text=category[1], callback_data=f'category_{category[0]}'))
        if category[0] % buttons_in_row == 0:
            buttons.append([])
            row += 1
        buttons[row].append(button)
    keyboard = InlineKeyboardMarkup([button for button in buttons])
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='Каталог',
                             reply_markup=keyboard)


menu_handler = MessageHandler(Filters.text('Меню'), catalog)
dispatcher.add_handler(menu_handler)


def products_catalog(update: Update, context: CallbackContext):
    """Вызов каталога товаров"""
    chosen_category = update.callback_query.data.split('_')[1]
    page = 0
    pagination = False
    call = update.callback_query
    context.bot.delete_message(chat_id=call.message.chat.id,
                               message_id=call.message.message_id)
    if '#' in chosen_category:
        chosen_category, page = chosen_category.split('#')
        page = int(page)
    category = get_category(chosen_category)
    products, pages = get_products(chosen_category, page)
    if pages:
        pagination = True
    if products:
        for product in products:
            product_id, product_name, product_img, price, category_id, rests = product
            buttons = ([InlineKeyboardButton(text='Добавить', callback_data=f'add_{product_id}'),
                        InlineKeyboardButton(text='Убрать', callback_data=f'remove_{product_id}')],)
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
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'{product_name} '
                                                                            f'\n Цена: {price}'
                                                                            f'\n Количество: - {rests} шт.')

            context.bot.send_photo(chat_id=update.effective_chat.id,
                                   photo=open(f'{BASE_DIR}/static/products/{imgs[0]}', 'rb'),
                                   disable_notification=True,
                                   reply_markup=keyboard)
        if pagination:
            keyboard_next = InlineKeyboardMarkup(
                [[InlineKeyboardButton(text='Еще товары', callback_data=f'category_{chosen_category}#{page + 1}')]])
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f'Страница {page} из {pages}',
                                     disable_notification=True,
                                     reply_markup=keyboard_next)

    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'Товаров из {category} нет')


catalog_handler = CallbackQueryHandler(products_catalog, pattern="^" + str('category_'))
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

    buttons = ([[InlineKeyboardButton(text='Добавить', callback_data=main_inline_kb[0][0]['callback_data']),
                 InlineKeyboardButton(text='Убрать', callback_data=main_inline_kb[0][1]['callback_data']),
                 InlineKeyboardButton(text='Повернуть', callback_data=f'roll_{main_photo}')]])
    keyboard = InlineKeyboardMarkup([button for button in buttons])
    try:
        context.bot.edit_message_media(
            media=InputMediaPhoto(media=turn_photo),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard)
    except:
        context.bot.send_message(call.message.chat.id, "Хм... состава не оказалось")


roll_photo_handler = CallbackQueryHandler(roll_photo, pattern="^" + str('roll_'))
dispatcher.add_handler(roll_photo_handler)


def edit(update: Update, context: CallbackContext):
    """Добавить/Удаить товар в корзине"""

    call = update.callback_query
    user = call.from_user.id
    command, product_id = call.data.split('_')

    product_amount, product = edit_to_cart(command, user, product_id)
    context.bot.answer_callback_query(callback_query_id=call.id, text=f'В корзине {product[0]} - {product_amount} шт.')


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
        except telegram.error.BadRequest:
            return
    cart_info = show_cart(chat_id)
    cart_price = 0

    cart_message = ''
    if len(cart_info) > 0:
        for num, product in enumerate(cart_info):
            product_name, amount, price = product
            cart_price += price * amount
            cart_message += f'{num + 1}. {product_name} - {amount} шт. по {price} р.\n'
        else:
            cart_message += f'Итого: {cart_price} р.'

        buttons = ([InlineKeyboardButton(text='Оформить заказ', callback_data='offer-stage_1_none')],
                   [InlineKeyboardButton(text='Очистить', callback_data='delete-cart'),
                    InlineKeyboardButton(text='Редактировать', callback_data='correct-cart')])

        keyboard = InlineKeyboardMarkup([button for button in buttons])

        if update.callback_query:
            chat_id = update.callback_query.message.chat_id
            message_id = update.callback_query.message.message_id
            try:
                message = context.bot.edit_message_text(chat_id=chat_id,
                                                        message_id=message_id,
                                                        text=cart_message,
                                                        reply_markup=keyboard)
            except telegram.error.BadRequest:
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


cart_handler = MessageHandler(Filters.text('Корзина'), cart)
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

    if settings_stage == '1':
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Да', callback_data='offer-stage_2_yes'),
                                          InlineKeyboardButton(text='Нет', callback_data='offer-stage_2_no')]])
        context.bot.edit_message_text(chat_id=chat_id,
                                      message_id=message_id,
                                      text=f'Вам доставить?',
                                      reply_markup=keyboard)
    if settings_stage == '2' and answer == 'yes':
        save_delivery_settings(value=True, field='delivery', chat_id=chat_id)
        users_message[chat_id] = ''
        street = get_user_address(chat_id)
        buttons = [[InlineKeyboardButton(text='Сохранить адрес', callback_data='offer-stage_3_none')]]
        if street:
            buttons.insert(0, [InlineKeyboardButton(text=street, callback_data=f'offer-stage_3_street')])
        keyboard = InlineKeyboardMarkup(buttons)
        context.bot.edit_message_text(chat_id=chat_id,
                                      message_id=message_id,
                                      text=f'Отправьте сообщение с адресом доставки, а затем нажмите кнопку в этом сообщении "Сохранить адрес'
                                           f'или выберите последний адрес доставки"',
                                      reply_markup=keyboard)
    if settings_stage == '2' and answer == 'no':
        save_delivery_settings(value=False, field='delivery', chat_id=chat_id)
        buttons =[]
        for shop in get_shops():
            shop_id, shop_name = shop
            buttons.append(InlineKeyboardButton(text=shop_name, callback_data=f'offer-stage_4_{shop_id}'))
        keyboard = InlineKeyboardMarkup([buttons])
        context.bot.edit_message_text(chat_id=chat_id,
                                      message_id=message_id,
                                      text=f'Выберите предпочтительный магазин',
                                      reply_markup=keyboard)
    if settings_stage == '3':
        if answer == "none":
            save_delivery_settings(value=users_message[chat_id], field='delivery_street', chat_id=chat_id)
        save_delivery_settings(value=True, field='delivery', chat_id=chat_id)
        users_message.pop(chat_id)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Наличными', callback_data='offer-stage_4_cash'),
                                          InlineKeyboardButton(text='Безналично',
                                                               callback_data='offer-stage_4_cashless')]])
        context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                      message_id=message_id,
                                      text=f'Выберите вид оплаты',
                                      reply_markup=keyboard)

    if settings_stage == '4':
        try:
            answer = int(answer)
            save_delivery_settings(value=answer, field='main_shop_id', chat_id=chat_id)
        except ValueError:
            if answer == 'cashless':
                save_delivery_settings(value=False, field='payment_cash', chat_id=chat_id)
            elif answer == 'cash':
                save_delivery_settings(value=True, field='payment_cash', chat_id=chat_id)
        delivery_settings = _user_settings_from_db(get_delivery_settings(chat_id))

        cart_price = 0
        cart_info = show_cart(chat_id)

        for num, product in enumerate(cart_info):
            product_name, amount, price = product
            cart_price += price * amount

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Заказать', callback_data=f'order_{cart_price}')],
                                         [InlineKeyboardButton(text='Редктировать',
                                                               callback_data=f'offer-stage_1_none')]])

        context.bot.edit_message_text(chat_id=chat_id,
                                      message_id=message_id,
                                      text=f'Мы доставим {delivery_settings}',
                                      reply_markup=keyboard)


offer_settings = CallbackQueryHandler(get_offer_settings, pattern=str('offer-stage'))
dispatcher.add_handler(offer_settings)


def _user_settings_from_db(data: tuple) -> str:
    """ Нсастроки заказа """
    delivery, main_shop_id, payment_cash, delivery_street = data
    text = ''
    if delivery:
        if payment_cash == 'True':
            text = f'по адресу {delivery_street}, оплата наличными'
        else:
            text = f'по адресу {delivery_street}, оплата по карте'
    else:
        if main_shop_id == 2:
            text = 'в магазин пер. Прачечный 3 '
        if main_shop_id == 1:
            text = 'в магазин ул. Киевская 3'
    return text


def edit_cart(update: Update, context: CallbackContext):
    """Редактирование товаров в корзине"""
    call = update.callback_query
    chat_id = call.message.chat_id
    message_id = call.message.message_id
    command, product_id = call.data.split('_')
    amount, product = edit_to_cart(command, chat_id, product_id)
    message = f'{product} - {amount} шт.'
    if amount > 0:
        buttons = ([InlineKeyboardButton(text='Добавить', callback_data=f'add-cart_{product_id}'),
                    InlineKeyboardButton(text='Убрать', callback_data=f'remove-cart_{product_id}')],)
        keyboard_edit = InlineKeyboardMarkup([button for button in buttons])
        try:
            context.bot.edit_message_text(chat_id=chat_id,
                                          message_id=message_id,
                                          text=message,
                                          reply_markup=keyboard_edit)
        except telegram.error.BadRequest:
            pass
    else:
        keyboard_edit = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text='Добавить', callback_data=f'add-cart_{product_id}')]])
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
            buttons = ([InlineKeyboardButton(text='Добавить', callback_data=f'add-cart_{product_id}'),
                        InlineKeyboardButton(text='Убрать', callback_data=f'remove-cart_{product_id}')],)
            keyboard_edit = InlineKeyboardMarkup([button for button in buttons])
            message = f'{product_name} - {amount} шт. по {price} р.\n'
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
    command, cart_price = call.data.split('_')
    order_products, order_price = save_order(chat_id, call.message.text, cart_price)
    text_products = ''
    for product_name, product_amount in order_products:
        text_products += f'\n{product_name[0]} - {product_amount} шт.'
    order_message = f'Заказ №: {order_num} \n {text_products} \n {call.message.text} \n на сумму: {order_price}'
    context.bot.answer_callback_query(callback_query_id=call.id,
                                      text=f'Ваш заказ номер {order_num} принят')
    context.bot.edit_message_text(text=f'Клиент: {user} \n{order_message}',
                                  chat_id=call.message.chat.id,
                                  message_id=call.message.message_id)
    context.bot.forward_message(chat_id=ORDERS_CHAT_ID,
                                from_chat_id=call.message.chat_id,
                                message_id=call.message.message_id)
    context.bot.edit_message_text(text=f'Ваш {order_message}',
                                  chat_id=call.message.chat.id,
                                  message_id=call.message.message_id)


order_cart_handler = CallbackQueryHandler(order, pattern=str('order_'))
dispatcher.add_handler(order_cart_handler)


def delete_cart(update: Update, context: CallbackContext):
    """Очистить корзину"""
    call = update.callback_query

    buttons = ([InlineKeyboardButton(text='Вернуться', callback_data='cancel-delete-cart'),
                InlineKeyboardButton(text='Удалить', callback_data='accept-delete-cart')],)

    keyboard = InlineKeyboardMarkup([button for button in buttons])

    message = context.bot.edit_message_text(chat_id=call.message.chat.id,
                                            message_id=call.message.message_id,
                                            text='Вы уверены что хотите удалить корзину',
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
    """Вызов истории покупок"""
    chat_id = update.effective_chat.id
    orders = get_user_orders(chat_id)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Закрыть', callback_data='remove-message')]])

    if not orders:
        message = context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='Вы еще ничего не покупали :(',
                                           reply_markup=keyboard)
    else:
        prev_id, prev_sum = None, None
        text = ''
        len_orders = len(orders) - 1
        for index, order in enumerate(orders):
            order_id, product_name, product_price, product_amount, order_sum = order

            if not prev_id:
                prev_id, prev_sum = order_id, order_sum
                order_products = [f'{product_name} - {product_amount} шт. по {product_price}р.']
            elif prev_id == order_id:
                order_products.append(f'{product_name} - {product_amount} шт. по {product_price}р.')
            if prev_id != order_id:
                text_products = '\n'.join(order_products)
                text += f'''Заказ № {prev_id} \n {text_products} \n на сумму:{prev_sum} \n {"_" * 20} \n'''
                order_products = [f'{product_name} - {product_amount} шт. по {product_price}р.']
                prev_id, prev_sum = order_id, order_sum
            if index == len_orders:
                text_products = '\n'.join(order_products)
                text += f'''Заказ № {order_id} \n {text_products} \n на сумму: {order_sum} \n {"_" * 20} \n'''
                break

        message = context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=text,
                                           reply_markup=keyboard)

    context.bot.delete_message(chat_id=update.effective_chat.id,
                               message_id=message.message_id - 1)


orders_history_handler = MessageHandler(Filters.text('Мои заказы'), orders_history)
dispatcher.add_handler(orders_history_handler)


def unknown(update: Update, context: CallbackContext):
    """Неизветсные команды"""
    context.bot.send_message(chat_id=update.effective_chat.id, text="Извините, я не знаю такой команды")


unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler)

""" АДМИНИСТРАТИВНЫЕ """


def poll_orders(update: Update, context: CallbackContext):
    """Выводит опрос по заказам для подтверждения/ отмены"""
    if check_user_is_staff(update.message.chat_id)[0]:
        if update.message.text == 'Подтвердить заказ':
            poll_type = 'approve'
        elif update.message.text == 'Отменить заказ':
            poll_type = 'refuse'
        user = update.message.from_user.username
        orders = get_waiting_orders()
        # не более 10 варианов ответа в опросе
        options_list = []
        options = [('Отмена')]
        for index, order in enumerate(orders):
            if (index + 1) % 10 == 0:
                options_list.append(options)
                options = [('Отмена')]
            options.append(f'Ордер №{order[0]} - клиент {order[1]} - стоимость {order[2]}р.')
        if len(options) > 1:
            options_list.append(options)

        for options in options_list:
            message = context.bot.send_poll(chat_id=update.effective_chat.id,
                                            question=f'Опрос {update.message.text} создан пользователем {user}',
                                            options=options,
                                            is_anonymous=False,
                                            allows_multiple_answers=True)
        if not options_list:
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Закрыть', callback_data='remove-message')]])
            message = context.bot.send_message(chat_id=update.effective_chat.id,
                                               text='Нет заявок',
                                               reply_markup=keyboard)
            context.bot.delete_message(chat_id=update.effective_chat.id,
                                       message_id=message.message_id - 1)
            return
        poll = {
            message.poll.id: {
                "admin_username": user,
                "orders": orders,
                "message_id": message.message_id,
                "chat_id": update.effective_chat.id,
                "poll_type": poll_type
            }
        }
        context.bot_data.update(poll)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='Извините, я не знаю такой команды')


poll_orders_handler = MessageHandler(Filters.text('Подтвердить заказ'), poll_orders)
dispatcher.add_handler(poll_orders_handler)

poll_orders_handler = MessageHandler(Filters.text('Отменить заказ'), poll_orders)
dispatcher.add_handler(poll_orders_handler)


def poll_orders_answer(update: Update, context: CallbackContext):
    """Ответ на опрос по заказам"""
    answer = update.poll_answer
    poll_id = answer.poll_id

    try:
        orders = context.bot_data[poll_id]["orders"]
        admin_username = context.bot_data[poll_id]['admin_username']
    except KeyError:
        context.bot.send_message(chat_id=update.poll_answer.user.id,
                                 text=f'Не получилось отправить пуши по заказам. Попробуйте еще раз.'
                                      f'Если ошибка повторится обратитесь к администратору @Vesselii')

        return
    selected_options = answer.option_ids

    if 0 in selected_options:
        return

    for order_index in selected_options:
        confirm_order = orders[order_index - 1]
        chat_id = get_user_id_chat(confirm_order[1])
        if context.bot_data[poll_id]['poll_type'] == 'approve':
            context.bot.send_message(chat_id=chat_id,
                                     text=f'Ваш заказ №{confirm_order[0]} на сумму {confirm_order[2]} ожидает вас в магазине')
            soft_delete_confirmed_order(order_id=confirm_order[0], admin_username=admin_username)
        if context.bot_data[poll_id]['poll_type'] == 'refuse':
            context.bot.send_message(chat_id=chat_id,
                                     text=f'Ваш заказ №{confirm_order[0]} отменен')
            soft_delete_confirmed_order(order_id=confirm_order[0], admin_username=admin_username)


poll_answer_handler = PollAnswerHandler(poll_orders_answer)
dispatcher.add_handler(poll_answer_handler)

""" Утилиты """


def user_message(update: Update, context: CallbackContext):
    """Принять сообщение пользователя (адрес)"""
    global users_message
    chat_id = update.message.chat_id
    if chat_id in users_message:
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
