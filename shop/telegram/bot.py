import logging
import math
import re

from django.db import close_old_connections, connection
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, error
from telegram.ext import Updater, CallbackContext, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, \
    filters
from telegram.error import TelegramError

from django_telegram_bot.settings import BASE_DIR
from shop.models import Category, Shop, Product
from shop.telegram.banking.banking import avangard_invoice
from shop.telegram.settings import TOKEN, ORDERS_CHAT_ID
from users.models import Profile, UserMessage, Carts, Orders, OrderStatus
import shop.telegram.bot_texts as text

LOG_FILENAME = 'bot_log.txt'
logger = logging.getLogger(__name__)

updater = Updater(token=TOKEN)
dispatcher = updater.dispatcher

ADMIN_TG = '@Ottuda_SPB_help'
PRODUCTS_PAGINATION_NUM = 5
BUTTONS_IN_ROW_CATEGORY = 2


def connection_decorator(func):
    def inner(*args, **kwargs):
        close_old_connections()
        connection.ensure_connection()
        return func(*args, **kwargs)
    return inner


# ДЛЯ ПОЛЬЗОВАТЕЛЕЙ

@connection_decorator
def main_keyboard(update: Update, context: CallbackContext):
    """Основаня клавиатура снизу"""
    user = update.message.from_user
    chat_id = update.message.chat_id
    user_profile = Profile.objects.filter(chat_id=chat_id)

    if not user_profile:
        try:
            Profile.objects.create(first_name=user.first_name, last_name=user.last_name, telegram_name=user.username,
                                   chat_id=chat_id, discussion_status='phone_main')
            no_phone_message = f'\n\nДобро пожаловать {user.first_name}, для оформления заказов нужно указать номер телефона. Отправьте в чат номер телефона (формат +7** или 8**).'
            message_text = text.start_message_new + no_phone_message
        except Exception as err:
            message_text = f'''Извините {user.first_name} произошла ошибка, попробуйте еще раз нажать 👉 /start.
        Если ошибка повторяется, обратитесь за помощью в канал {ADMIN_TG}'''
    else:
        user_profile = user_profile[0]
        if not user_profile.phone:
            message_text = f'Добро пожаловать {user.first_name}, нужно указать номер телефона. Отправьте в чат номер телефона. (формат +7*** или 8***)'
            user_profile.discussion_status = 'phone_main'
        else:
            message_text = f'Добро пожаловать {user.first_name}.'
    message = context.bot.send_message(chat_id=update.effective_chat.id, text=message_text, parse_mode='HTML')
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message.message_id - 1)


start_handler = CommandHandler('start', main_keyboard)
dispatcher.add_handler(start_handler)


@connection_decorator
def phone_check(update: Update, context: CallbackContext, phone, trace_back) -> bool:
    """Проверка номера телефона"""
    chat_id = update.message.chat_id
    result = re.match(r'^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$',
                      phone)
    if bool(result):
        user_profile = Profile.objects.get(chat_id=chat_id)
        user_profile.phone = phone
        user_profile.discussion_status = 'messaging'
        user_profile.save()

        message = context.bot.send_message(chat_id=update.message.chat_id,
                                           text=f'Спасибо, номер телефона принят. \nНажмите еще раз "оформить заказ"')
        context.bot.delete_message(chat_id=update.effective_chat.id,
                                   message_id=message.message_id - 2)
        if trace_back == 'phone_profile':
            profile_menu(update, context)
        elif trace_back == 'phone_main':
            main_keyboard(update, context)
        else:
            pass
    else:
        message = context.bot.send_message(chat_id=update.message.chat_id,
                                           text=f"""К сожалению номер {phone}, некоректный повторите ввод или обратитесь к канал помощи {ADMIN_TG} (r1)""")
        context.bot.delete_message(chat_id=update.effective_chat.id,
                                   message_id=message.message_id - 1)
    if trace_back == 'phone_profile' and bool(result):
        context.bot.delete_message(chat_id=update.effective_chat.id,
                                   message_id=message.message_id - 4)
    return bool(result)


@connection_decorator
def profile_update(update: Update, context: CallbackContext, first_name: str = None, last_name: str = None,
                   address: str = None):
    """Основаня клавиатура снизу"""

    chat_id = update.message.chat_id
    user_profile = Profile.objects.get(chat_id=chat_id)
    break_flag = False
    text = 'Произошла ошибка при изменении профиля, попробуйте еще раз. Или напишите в чат для помощи'

    if first_name:
        value = first_name[:20]
        text = "Имя было изменено"
        field = 'first_name'
    elif last_name:
        value = last_name[:20]
        field = 'last_name'
        text = "Фамилия была изменена"
    elif address:
        value = address[:200]
        field = 'delivery_street'
        text = "Адрес был изменен"
    else:
        break_flag = True

    if not break_flag:
        user_profile.discussion_status = 'messaging'
        setattr(user_profile, field, value)
        user_profile.save()

    message = context.bot.send_message(chat_id=update.message.chat_id, text=text, disable_notification=True)
    context.bot.delete_message(chat_id=update.effective_chat.id,
                               message_id=message.message_id - 2)
    profile_menu(update, context)


@connection_decorator
def catalog(update: Update, context: CallbackContext):
    """Вызов каталога по группам"""
    buttons = [[]]
    row = 0
    flag_prew_category = True
    prew_category_id = None
    if update.callback_query:
        call = update.callback_query
        chosen_category = call.data.split('_')
        if chosen_category[1] != 'None':
            this_category = Category.objects.select_related('parent_category').get(id=int(chosen_category[1]))
            categories = Category.objects.select_related('parent_category').filter(parent_category=this_category)
        else:
            categories = Category.objects.select_related('parent_category').filter(parent_category=None)
            flag_prew_category = False
    else:
        categories = Category.objects.select_related('parent_category').filter(parent_category=None)
    if categories:
        for index, category in enumerate(categories):
            parent_category = category.parent_category
            parent_category_id = None
            if parent_category:
                parent_category_id = parent_category.id
            button = (InlineKeyboardButton(text=category.command,
                                           callback_data=f'category_{category.id}_{parent_category_id}'))
            if index % BUTTONS_IN_ROW_CATEGORY == 0:
                buttons.append([])
                row += 1
            buttons[row].append(button)

        if update.callback_query and flag_prew_category:
            if this_category.parent_category:
                prew_category_id = this_category.parent_category.id
            text = f'Категория: {this_category.command}'
            buttons.append(
                [InlineKeyboardButton(text='Назад', callback_data=f'category_{prew_category_id}_{prew_category_id}')])
        else:
            text = 'Каталог'
        keyboard = InlineKeyboardMarkup([button for button in buttons])
        message = context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=text, reply_markup=keyboard, disable_notification=True)
        context.bot.delete_message(chat_id=update.effective_chat.id,
                                   message_id=message.message_id - 1)
    else:
        products_catalog(update, context, chosen_category[1])


menu_handler = CommandHandler('catalog', catalog)
dispatcher.add_handler(menu_handler)

catalog_handler = CallbackQueryHandler(catalog, pattern="^" + str('category_'))
dispatcher.add_handler(catalog_handler)


@connection_decorator
def products_catalog(update: Update, context: CallbackContext, chosen_category=False):
    """Вызов каталога товаров"""
    page = 0
    pagination = False
    pages = None
    call = update.callback_query
    sale_type = Shop.objects.values("sale_type").get(id=1)['sale_type']
    if '#' in str(update.callback_query.data) and not chosen_category:
        chosen_category = update.callback_query.data.split('_')[1]
        chosen_category, page = chosen_category.split('#')
        page = int(page)

    products = Product.objects.order_by('name').select_related('discount_group', 'image', 'category').filter(
        category=chosen_category, rests__amount__gt=0)
    if products.count() > PRODUCTS_PAGINATION_NUM:
        count_pages = (len(products) - 1) // PRODUCTS_PAGINATION_NUM
        start = page * PRODUCTS_PAGINATION_NUM
        end = start + PRODUCTS_PAGINATION_NUM
        pagination = True
        products = products[start: end]
        pages = count_pages

    if products:
        context.bot.delete_message(chat_id=call.message.chat.id,
                                   message_id=call.message.message_id)
        for product in products:
            if product.image:
                product_img = [product.image.name]
            else:
                product_img = ['no-image.jpg']

            try:
                img_reversed = product_img[0].replace('.', '@rev.')
                open(f'{BASE_DIR}/static/products/{img_reversed}')
                product_img.append(f'{img_reversed}')
            except FileNotFoundError:
                pass

            if len(product_img) > 1:
                compounds_url = f'{BASE_DIR}/static/products/{product_img[1]}'
                buttons[0].append(InlineKeyboardButton(text='Состав', callback_data=f'roll_{compounds_url}'))

            try:
                product_photo = open(f'{BASE_DIR}/static/products/{product_img[0]}', 'rb')
            except FileNotFoundError:
                product_photo = open(f'{BASE_DIR}/static/products/no-image.jpg', 'rb')
            rests = product.rests_set.values('amount').all()[0]['amount']

            if sale_type != 'no_sale':
                discount = getattr(product.discount_group, f'{sale_type}_value')
                product_info = f'''{product.name}  \n <b>Цена: <s>{product.price}</s> {round(product.price * discount)}.00 р.</b>\n Скидка: {(1 - discount) * 100}% \n <i>В наличии: {int(rests)} шт.</i> '''
            else:
                product_info = f'''{product.name}  \n <b>Цена: {product.price} р.</b> \n <i>В наличии: {int(rests)} шт.</i>'''

            buttons = ([InlineKeyboardButton(text='Добавить  🟢', callback_data=f'add_{product.id}'),
                        InlineKeyboardButton(text='Убрать 🔴', callback_data=f'remove_{product.id}')],)
            keyboard = InlineKeyboardMarkup([button for button in buttons])
            context.bot.send_photo(chat_id=update.effective_chat.id,
                                   photo=product_photo,
                                   disable_notification=True)
            context.bot.send_message(chat_id=update.effective_chat.id, text=product_info,
                                     reply_markup=keyboard,
                                     parse_mode='HTML', disable_notification=True)

        product_parent_category = products[0].category.parent_category
        parent_category_id = None
        if product_parent_category:
            parent_category_id = product_parent_category.id
        buttons = ([[InlineKeyboardButton(text='Назад',
                                          callback_data=f'category_{parent_category_id}_{parent_category_id}')]])

        header_text = f'Вернуться в категории?'
        if pagination and page < pages:
            buttons.insert(0, [
                InlineKeyboardButton(text='Еще товары', callback_data=f'product_{chosen_category}#{page + 1}')])
            header_text = f'Страница <b>{page + 1}</b> из {pages + 1}'
        keyboard = InlineKeyboardMarkup([button for button in buttons])
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=header_text,
                                 disable_notification=True,
                                 reply_markup=keyboard, parse_mode='HTML')

    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'В данной категории не нашлось товаров 😨',
                                 disable_notification=True)


catalog_handler = CallbackQueryHandler(products_catalog, pattern="^" + str('product_'))
dispatcher.add_handler(catalog_handler)


@connection_decorator
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
        context.bot.send_message(call.message.chat.id, "Состава не оказалось 😨", disable_notification=True)


roll_photo_handler = CallbackQueryHandler(roll_photo, pattern="^" + str('roll_'))
dispatcher.add_handler(roll_photo_handler)


@connection_decorator
def _cart_edit(chat_id, product_id, command):
    cart_info = Carts.objects.select_related('product').filter(profile__chat_id=chat_id, product__id=product_id,
                                                               order__isnull=True)
    product_info = Product.objects.only('name', 'price').get(id=product_id)
    product_rests = product_info.rests_set.values('amount').all()[0]['amount']
    if not cart_info and command in ['add', 'add-cart']:
        profile = Profile.objects.get(chat_id=chat_id)
        Carts.objects.create(profile=profile, product_id=product_id, amount=1, price=product_info.price)
        amount = 1
    elif not cart_info and command == 'remove':
        amount = 0
    else:
        cart_info = cart_info[0]
        amount = cart_info.amount
        if command in ['add', 'add-cart']:
            if amount < product_rests:
                amount += + 1
        elif command in ['remove', 'remove-cart']:
            amount -= 1
        else:
            amount = 0
        if amount == 0:
            cart_info.delete()
        else:
            cart_info.amount = amount
            cart_info.save()
    return product_info.name, amount, product_rests


@connection_decorator
def edit(update: Update, context: CallbackContext):
    """Добавить/Удаить товар в корзине"""

    call = update.callback_query
    chat_id = call.from_user.id
    command, product_id = call.data.split('_')
    product_name, amount, product_rests = _cart_edit(chat_id, product_id, command)

    context.bot.answer_callback_query(callback_query_id=call.id,
                                      text=f'В корзине {product_name[:20]}... {amount} шт.')


catalog_handler = CallbackQueryHandler(edit, pattern="^" + str('add_'))
dispatcher.add_handler(catalog_handler)

catalog_handler = CallbackQueryHandler(edit, pattern="^" + str('remove_'))
dispatcher.add_handler(catalog_handler)


@connection_decorator
def cart(update: Update, context: CallbackContext, call_func=False):
    """Показать корзину покупателя/ Отмена удаления корзины"""
    profile = Profile.objects.only('cart_message_id').get(chat_id=update.effective_chat.id)
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
        try:
            if profile.cart_message_id != 0:
                context.bot.delete_message(chat_id=chat_id, message_id=profile.cart_message_id)
        except error.BadRequest:
            pass
    sale_type = Shop.objects.values('sale_type').get(id=1)['sale_type']
    carts = Carts.objects.select_related('product', 'product__discount_group').filter(order__isnull=True,
                                                                                      profile__chat_id=chat_id,
                                                                                      soft_delete=False)
    cart_price = 0
    cart_message = ''
    cart_discount = 0

    if len(carts) > 0:
        for num, cart_info in enumerate(carts):
            if sale_type != 'no_sale':
                discount = getattr(cart_info.product.discount_group, f'{sale_type}_value')
                price_count = round(round(cart_info.price * discount), 2)
                cart_discount += (cart_info.price - price_count) * cart_info.amount
            else:
                price_count = cart_info.price
            cart_price += round(int(price_count) * cart_info.amount)
            cart_message += f'{num + 1}. {cart_info.product.name} - {int(cart_info.amount)} шт. по {cart_info.price} р.\n'
        else:
            if sale_type == 'no_sale':
                cart_message += f'Итого: {cart_price}.00 р.'
            else:
                cart_message += f'Ваша скидка: {round(cart_discount, 2)} р.\n Итого co скидкой: {cart_price}.00 р.'
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
                                                        reply_markup=keyboard,
                                                        parse_mode='HTML')
            except error.BadRequest:
                pass
            else:
                profile.cart_message_id = 0
                profile.save()

        else:
            message = context.bot.send_message(chat_id=update.effective_chat.id,
                                               text=cart_message,
                                               reply_markup=keyboard,
                                               parse_mode='HTML',
                                               disable_notification=True)
            if not call_func:
                context.bot.delete_message(chat_id=update.effective_chat.id,
                                           message_id=message.message_id - 1)

    else:
        message = context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='Корзина пустая', disable_notification=True)
        if not call_func:
            context.bot.delete_message(chat_id=update.effective_chat.id,
                                       message_id=message.message_id - 1)
    try:
        profile.cart_message_id = message.message_id
        profile.save()
    except ReferenceError:
        pass


cart_handler = CommandHandler('cart', cart)
dispatcher.add_handler(cart_handler)

cancel_cart_handler = CallbackQueryHandler(cart, pattern=str('cancel-delete-cart'))
dispatcher.add_handler(cancel_cart_handler)

return_cart_handler = CallbackQueryHandler(cart, pattern="^" + str('return-to-cart_'))
dispatcher.add_handler(return_cart_handler)


@connection_decorator
def get_offer_settings(update: Update, context: CallbackContext, settings_stage=None, answer=None):
    """Настройки заказа (доставка, вид оплаты, магазин)"""
    call = update.callback_query
    chat_id = update.effective_chat.id
    call_func = False
    profile = Profile.objects.get(chat_id=chat_id)
    if settings_stage and answer:
        call_func = True
    else:
        message_id = call.message.message_id
        _, settings_stage, answer = call.data.split('_')

    user_orders = Orders.objects.filter(profile=profile, status__title='0')

    if not profile.phone:
        profile.discussion_status = 'phone'
        profile.save()
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Для оформления заказа требуется ваш номер телефона, напишите его в чат. Формат (+7** или 8**)')
    elif user_orders and answer == 'none' and settings_stage == '1':
        buttons = []
        for user_order in user_orders:
            buttons.append([InlineKeyboardButton(text=f'Добавить в заказ № {user_order.id}',
                                                 callback_data=f'add-to-offer_{user_order.id}')])
        buttons.append([InlineKeyboardButton(text=f'Сделать новый заказ', callback_data='offer-stage_1_new')])
        keyboard = InlineKeyboardMarkup(buttons)
        context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                      message_id=message_id,
                                      text=f'У вас имеются заказы в обработке, хотите добавить в имеющийся или сделать новый заказ?',
                                      reply_markup=keyboard)
    else:
        if settings_stage == '1':
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Да', callback_data='offer-stage_2_yes'),
                                              InlineKeyboardButton(text='Нет', callback_data='offer-stage_2_no')]])
            context.bot.edit_message_text(chat_id=chat_id,
                                          message_id=message_id,
                                          text=f'Вам доставить? 🚚 (доставка будет рассчитана после оформления заказа)',
                                          reply_markup=keyboard)
        elif settings_stage == '2' and answer == 'yes':
            profile.discussion_status = 'offer_address'
            profile.delivery = 1
            profile.save()

            if not profile.delivery_street:
                profile.discussion_status = 'offer_address'
                keyboard = None
                text = 'Отправьте сообщение в чат с адресом доставки:'
            else:
                text = f'Отправьте сообщение с адресом доставки, а затем нажмите кнопку в этом сообщении "Изменить адрес  📝" или  выберите последний адрес доставки'
                buttons = [[InlineKeyboardButton(text='Изменить адрес 📝', callback_data='offer-stage_3_none')]]
                if profile.delivery_street:
                    buttons.insert(0, [
                        InlineKeyboardButton(text=profile.delivery_street, callback_data=f'offer-stage_3_street')])
                keyboard = InlineKeyboardMarkup(buttons)
            context.bot.edit_message_text(chat_id=chat_id,
                                          message_id=message_id,
                                          text=text,
                                          reply_markup=keyboard)
        elif settings_stage == '2' and answer == 'no':
            profile.delivery = 0
            profile.save()
            buttons = []
            shops = Shop.objects.all()
            for shop in shops:
                buttons.append(InlineKeyboardButton(text=shop.name, callback_data=f'offer-stage_3_{shop.id}'))
            keyboard = InlineKeyboardMarkup([buttons])
            context.bot.edit_message_text(chat_id=chat_id,
                                          message_id=message_id,
                                          text=f'Выберите предпочтительный магазин:',
                                          reply_markup=keyboard)
        elif settings_stage == '3':
            break_flag = False
            if answer == 'none':
                buttons = [[InlineKeyboardButton(text='Изменить адрес 📝', callback_data='offer-stage_3_none')]]
                keyboard = InlineKeyboardMarkup(buttons)
                if profile.delivery_street:
                    buttons.insert(0, [
                        InlineKeyboardButton(text=profile.delivery_street, callback_data=f'offer-stage_3_street')])
                context.bot.edit_message_text(chat_id=chat_id,
                                              message_id=message_id,
                                              text=f'Нужно указать адрес. Для этого отправьте в чат сообщение с адресом а потом нажмите "Изменить адрес 📝"',
                                              reply_markup=keyboard)
                break_flag = True

            elif answer == 'street':
                profile.delivery = 1
            else:
                profile.main_shop = Shop.objects.get(id=int(answer))
                profile.delivery = 0
            profile.save()

            if not break_flag:
                # Оплата: 2 - qr код, 1 - ввод карты
                keyboard = InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text='Через банковское приложение', callback_data=f'offer-stage_4_2')],
                     [InlineKeyboardButton(text='Ввести реквизиты карты', callback_data=f'offer-stage_4_1')]])
                if call_func:
                    message = context.bot.send_message(chat_id=chat_id,
                                                       text=f'''Выберите вид оплаты:''',
                                                       reply_markup=keyboard,
                                                       disable_notification=True)
                    context.bot.delete_message(chat_id=update.effective_chat.id,
                                               message_id=message.message_id - 2)
                    context.bot.delete_message(chat_id=update.effective_chat.id,
                                               message_id=message.message_id - 1)
                else:
                    context.bot.edit_message_text(chat_id=chat_id,
                                                  message_id=message_id,
                                                  text=f'''Выберите вид оплаты:''',
                                                  reply_markup=keyboard)

        elif settings_stage == '4':

            if profile.delivery:
                text = f'Доставка по адресу {profile.delivery_street}'
            else:
                text = f'Пункт выдачи - магазин {profile.main_shop} '

            cart_price = 0
            carts = Carts.objects.filter(order__isnull=True, profile__chat_id=chat_id, soft_delete=False)
            sale_type = Shop.objects.values('sale_type').get(id=1)['sale_type']

            for cart in carts:
                product_price = round(cart.product.price * cart.amount, 2)
                if sale_type != 'no_sale':
                    discount = getattr(cart.product.discount_group, f'{sale_type}_value')
                    product_price = round(product_price * discount, 2)
                cart_price += product_price

            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(text='Заказать 🛍', callback_data=f'order_{cart_price}_{answer}')],
                 [InlineKeyboardButton(text='Редктировать 📝',
                                       callback_data=f'offer-stage_1_none')]])

            context.bot.edit_message_text(chat_id=chat_id,
                                          message_id=message_id,
                                          text=f'{text}',
                                          reply_markup=keyboard)


offer_settings = CallbackQueryHandler(get_offer_settings, pattern=str('offer-stage'))
dispatcher.add_handler(offer_settings)


@connection_decorator
def add_to_offer(update: Update, context: CallbackContext):
    """Объеденить корзину с имеющимся заказом"""
    call = update.callback_query
    chat_id = update.effective_chat.id
    user = update.effective_user.username
    message_id = call.message.message_id
    _, add_to_order = call.data.split('_')
    order_main = Orders.objects.get(profile__chat_id=chat_id, id=int(add_to_order))
    if order_main.status.title == '0':
        Carts.objects.filter(profile__chat_id=chat_id, order__isnull=True).update(order=order_main)
        orders_carts = Carts.objects.select_related('product', 'product__discount_group').filter(order=order_main)
        text_products = ''
        order_sum = 0
        for order_data in orders_carts:
            product_price = order_data.price
            if order_main.sale_type != 'no_sale':
                discount = getattr(order_data.product.discount_group, f'{order_main.sale_type}_value')
                product_price = round(product_price * discount)
            text_products += f'\n{order_data.product.name} - {int(order_data.amount)} шт.'
            order_sum += round(product_price * order_data.amount, 2)

        order_message = f'<b><u>Заказ №: {order_main.id}</u></b> \n{text_products} \n{order_main.delivery_info} \n<b>на сумму: {math.ceil(order_sum) + order_main.delivery_price}</b>'
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Закрыть', callback_data='remove-message')]])
        context.bot.send_message(chat_id=chat_id,
                                 text=f'Товары были добавлены в заказ {add_to_order}',
                                 parse_mode='HTML', reply_markup=keyboard, disable_notification=True)
        orders_history(update, context)
        try:
            updater.bot.edit_message_text(chat_id=ORDERS_CHAT_ID, message_id=order_main.manager_message_id,
                                          text=f'Клиент: {user}\n{order_message}', parse_mode='HTML')
            updater.bot.send_message(chat_id=ORDERS_CHAT_ID,
                                     text=f'Заказ № {add_to_order} был отредактирован пользователем', parse_mode='HTML')
            return 'Заявка изменена в канале менеджеров'
        except Exception as err:
            return f'Неудалось изменить заявку в канале менеджеров по причине: {err}'
    else:
        context.bot.delete_message(chat_id=update.effective_chat.id,
                                   message_id=message_id)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Закрыть', callback_data='remove-message')]])
        context.bot.send_message(chat_id=chat_id,
                                 text='Не удалось добавить товары в заказ. Статус заказа, в который вы пытаетесь добавить, не "Заявка обрабатывается".',
                                 parse_mode='HTML', reply_markup=keyboard, disable_notification=True)


add_to_offer_handler = CallbackQueryHandler(add_to_offer, pattern=str('add-to-offer'))
dispatcher.add_handler(add_to_offer_handler)


@connection_decorator
def start_edit(update: Update, context: CallbackContext):
    """Список товаров для редактирования и выход из редактирования"""
    messages_ids = ''
    chat_id = update.callback_query.message.chat_id
    cart_info = Carts.objects.prefetch_related('product').only('amount').filter(profile__chat_id=chat_id,
                                                                                soft_delete=False,
                                                                                order__isnull=True)
    message_id = update.callback_query.message.message_id
    context.bot.delete_message(chat_id=chat_id,
                               message_id=message_id)
    if len(cart_info) > 0:
        for cart in cart_info:
            product_info = cart.product
            product_rests = product_info.rests_set.values('amount').all()[0]['amount']

            if cart.amount == product_rests:
                keyboard_edit = InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text='Убрать 🔴', callback_data=f'remove-cart_{product_info.id}')]])

            else:
                buttons = ([InlineKeyboardButton(text='Добавить  🟢', callback_data=f'add-cart_{product_info.id}'),
                            InlineKeyboardButton(text='Убрать 🔴', callback_data=f'remove-cart_{product_info.id}')],)
                keyboard_edit = InlineKeyboardMarkup([button for button in buttons])

            message = f'{product_info.name} - {int(cart.amount)} шт.\n'
            message = context.bot.send_message(chat_id=chat_id,
                                               text=message,
                                               reply_markup=keyboard_edit,
                                               disable_notification=True)

            messages_ids += f'{message.message_id}-'

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text='Обновить', callback_data=f'return-to-cart_{messages_ids}')]])

        context.bot.send_message(chat_id=chat_id,
                                 text=f'Для посчета суммы нажмите обновить',
                                 reply_markup=keyboard, disable_notification=True)


cart_list_handler = CallbackQueryHandler(start_edit, pattern=str('correct-cart'))
dispatcher.add_handler(cart_list_handler)


@connection_decorator
def edit_cart(update: Update, context: CallbackContext):
    """Редактирование товаров в корзине"""
    call = update.callback_query
    chat_id = call.message.chat_id
    message_id = call.message.message_id
    command, product_id = call.data.split('_')
    product_name, amount, product_rests = _cart_edit(chat_id, product_id, command)

    message = f'{product_name} - {amount} шт.'
    if amount == 0:
        keyboard_edit = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text='Добавить  🟢', callback_data=f'add-cart_{product_id}')]])
        context.bot.edit_message_text(chat_id=chat_id,
                                      message_id=message_id,
                                      text=message,
                                      reply_markup=keyboard_edit)
    elif amount == product_rests:
        keyboard_edit = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text='Убрать 🔴', callback_data=f'remove-cart_{product_id}')]])
        context.bot.edit_message_text(chat_id=chat_id,
                                      message_id=message_id,
                                      text=message,
                                      reply_markup=keyboard_edit)
    else:
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


edit_cart_handler = CallbackQueryHandler(edit_cart, pattern="^" + str('add-cart_'))
dispatcher.add_handler(edit_cart_handler)

catalog_handler = CallbackQueryHandler(edit_cart, pattern="^" + str('remove-cart_'))
dispatcher.add_handler(catalog_handler)


@connection_decorator
def order(update: Update, context: CallbackContext):
    """Оформить заявку (переслать в канал менеджеров)"""
    call = update.callback_query
    chat_id = call.message.chat_id
    user = call.message.chat.username
    command, cart_price, payment_type = call.data.split('_')
    deliver = False
    if call.message.text.split(' ')[0] == 'Доставка':
        deliver = True
    sale_type = Shop.objects.get(id=1).sale_type
    profile = Profile.objects.get(chat_id=chat_id)
    order_status = OrderStatus.objects.get(title='0')
    user_order = Orders.objects.create(profile=profile, delivery_info=call.message.text, deliver=deliver,
                                       order_price=cart_price, payment_id=int(payment_type), sale_type=sale_type,
                                       status=order_status)
    order_products = Carts.objects.filter(profile=profile, order__isnull=True)

    text_products, sum_message, full_discount, order_sum = '', '', 0, 0

    for order_product in order_products:
        if sale_type != 'no_sale':
            discount = getattr(order_product.product.discount_group, f"{sale_type}_value")
            new_price = round(order_product.product.price * discount)
            full_discount += round((order_product.product.price - new_price) * order_product.amount, 2)
            order_product.product.price = new_price
        order_sum += round(order_product.product.price * order_product.amount, 2)
        text_products += f'\n{order_product.product.name} - {order_product.amount} шт.'
    if sale_type != 'no_sale':
        sum_message = f'Cкидка: {full_discount} р.\nИТОГО со скидкой: {order_sum} р.'
    else:
        sum_message = f'ИТОГО: {order_sum} р.'

    order_message = f'<b><u>Заказ №: {user_order.id}</u></b> \n{text_products} \n{call.message.text} \n<b>{sum_message}</b>'
    context.bot.answer_callback_query(callback_query_id=call.id,
                                      text=f'Ваш заказ принят')
    message = context.bot.send_message(text=f'Клиент: {user} \n{order_message}', chat_id=ORDERS_CHAT_ID,
                                       parse_mode='HTML')
    context.bot.edit_message_text(
        text=f'Ваш {order_message} \n\nОжидайте ссылку на оплату, после оплаты товары будут зарезервированы...',
        chat_id=call.message.chat.id,
        message_id=call.message.message_id, parse_mode='HTML')
    order_products.update(order=user_order)
    user_order.manager_message_id = message.message_id
    user_order.save()


order_cart_handler = CallbackQueryHandler(order, pattern=str('order_'))
dispatcher.add_handler(order_cart_handler)


@connection_decorator
def delete_cart(update: Update, context: CallbackContext):
    """Очистить корзину"""
    call = update.callback_query

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Вернуться ❌', callback_data='cancel-delete-cart'),
                                      InlineKeyboardButton(text='Удалить ✔️', callback_data='accept-delete-cart')]])

    message = context.bot.edit_message_text(chat_id=call.message.chat.id,
                                            message_id=call.message.message_id,
                                            text='⚠️Вы уверены что хотите удалить корзину ⚠️',
                                            reply_markup=keyboard)
    Profile.objects.only('cart_message_id').get(chat_id=message.chat_id).update(cart_message_id=message.message_id)


delete_cart_handler = CallbackQueryHandler(delete_cart, pattern=str('delete-cart'))
dispatcher.add_handler(delete_cart_handler)


@connection_decorator
def accept_delete_cart(update: Update, context: CallbackContext):
    """Подтвердить удаление корзины"""

    call = update.callback_query
    chat_id = call.message.chat_id
    Carts.objects.filter(profile__chat_id=chat_id, order__isnull=True).delete()
    context.bot.delete_message(chat_id=call.message.chat.id,
                               message_id=call.message.message_id)
    context.bot.answer_callback_query(callback_query_id=call.id, text=f'Корзина очищена')


accept_cart_handler = CallbackQueryHandler(accept_delete_cart, pattern=str('accept-delete-cart'))
dispatcher.add_handler(accept_cart_handler)


@connection_decorator
def orders_history(update: Update, context: CallbackContext):
    """Вызов истории покупок (в статусе кроме исполненно или отменено) версия 1"""
    chat_id = update.effective_chat.id
    orders = Orders.objects.prefetch_related('carts_set').filter(profile__chat_id=chat_id).exclude(
        status__in=[6, 7]).order_by('id')
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Закрыть', callback_data='remove-message')]])

    if not orders:
        message = context.bot.send_message(chat_id=chat_id,
                                           text='У вас нет заказов',
                                           reply_markup=keyboard, disable_notification=True)
    else:

        orders_text = ''
        for order in orders:
            payment_urls_text, text_products, tracing_text = '', '', ''
            full_price, product_price_sum, position = 0, 0, 1
            for cart in order.carts_set.filter(soft_delete=False):
                if order.sale_type != 'no_sale':
                    discount = getattr(cart.product.discount_group, f'{order.sale_type}_value')
                    calc_price = round(cart.price * discount) * cart.amount
                else:
                    calc_price = cart.price * cart.amount
                product_price_sum += calc_price
                full_price += cart.product.price * cart.amount
                text_products += f'<i>{position}.</i> {cart.product.name} - {cart.amount} шт. по {cart.price} р.\n'
                position += 1
            else:
                if order.delivery_price > 0:
                    delivery_price_text = f'\nСтоимость доставки {order.delivery_price} р.'
                else:
                    delivery_price_text = ''
                if order.sale_type != 'no_sale' and full_price != product_price_sum:
                    discount_text = f'''\nВаша скидка {round(full_price - product_price_sum, 2)} р.
<b>ИТОГО со скидкой: {round(product_price_sum + order.delivery_price, 2)} р.</b>'''
                else:
                    discount_text = ''
                if order.status == '1':
                    payment_urls_text += f'\n ссылка на оплату товаров (чек): {order.payment_url}'
                    if order.extra_payment_url:
                        payment_urls_text += f'\n ссылка на оплату доставки (чек): {order.extra_payment_url}'
                elif order.status == '3':
                    if order.tracing_num:
                        tracing_text = f'👉🏻<b> Трек номер: {order.tracing_num} </b>👈🏻\n'
                    else:
                        tracing_text = '<b> Трек номер: нет </b>\n'

                orders_text += f'''<b><u>Заказ № {order.id}</u></b>
<u>Статус заказа: {order.status}</u>
{tracing_text}{text_products}{delivery_price_text}
ИТОГО: {round(full_price + order.delivery_price, 2)} р.{discount_text}{payment_urls_text}'''
                orders_text += f'\n {"_" * 20} \n'

        if update.callback_query:
            context.bot.edit_message_text(chat_id=chat_id,
                                          text=orders_text,
                                          reply_markup=keyboard, parse_mode='HTML',
                                          message_id=update.callback_query.message.message_id, )
        else:
            message = context.bot.send_message(chat_id=chat_id,
                                               text=orders_text,
                                               reply_markup=keyboard, parse_mode='HTML', disable_notification=True)
    if not update.callback_query:
        context.bot.delete_message(chat_id=chat_id,
                                   message_id=message.message_id - 1)


orders_history_handler = CommandHandler('orders', orders_history)
dispatcher.add_handler(orders_history_handler)

accept_cart_handler = CallbackQueryHandler(accept_delete_cart, pattern=str('history_orders'))
dispatcher.add_handler(accept_cart_handler)


# Информация
@connection_decorator
def profile_menu(update: Update, context: CallbackContext):
    """Меню информации"""

    if update.callback_query:
        call = update.callback_query
        chat_id = call.message.chat_id
        _, action, field = call.data.split('_')
    else:
        chat_id = update.message.chat_id
    user_profile = Profile.objects.get(chat_id=chat_id)
    if user_profile.discussion_status != 'messaging':
        user_profile.discussion_status = 'messaging'
        user_profile.save()

    menu = InlineKeyboardMarkup([[InlineKeyboardButton(text='Изменить имя', callback_data='edit_firstname')],
                                 [InlineKeyboardButton(text='Изменить фамилию', callback_data='edit_lastname')],
                                 [InlineKeyboardButton(text='Изменить номер телефона', callback_data='edit_phone')],
                                 [InlineKeyboardButton(text='Изменить адрес доставки', callback_data='edit_address')],
                                 [InlineKeyboardButton(text='Закрыть', callback_data='remove-message')]])

    profile_message = f"Профиль: \n Имя: <b>{user_profile.first_name or 'нет'}</b> \n Фамилия: <b>{user_profile.last_name or 'нет'}</b> \n Телефон №: <b>{user_profile.phone or 'нет'}</b> \n Адрес доставки: <b>{user_profile.delivery_street or 'нет'}</b>"
    if update.callback_query:
        context.bot.edit_message_text(chat_id=update.effective_chat.id, text=profile_message, reply_markup=menu,
                                      parse_mode='HTML', message_id=update.callback_query.message.message_id)
    else:
        message = context.bot.send_message(chat_id=update.effective_chat.id, text=profile_message, reply_markup=menu,
                                           parse_mode='HTML', disable_notification=True)
        context.bot.delete_message(chat_id=update.effective_chat.id,
                                   message_id=message.message_id - 1)


dispatcher.add_handler(CommandHandler('profile', profile_menu))

dispatcher.add_handler(CallbackQueryHandler(profile_menu, pattern=str('profile_roll-back_firstname')))
dispatcher.add_handler(CallbackQueryHandler(profile_menu, pattern=str('profile_roll-back_lastname')))
dispatcher.add_handler(CallbackQueryHandler(profile_menu, pattern=str('profile_roll-back_phone')))
dispatcher.add_handler(CallbackQueryHandler(profile_menu, pattern=str('profile_roll-back_address')))


@connection_decorator
def message_edit_profile(update: Update, context: CallbackContext):
    """Профиль: Изменить имя"""
    call = update.callback_query
    chat_id = call.message.chat_id
    user_profile = Profile.objects.get(chat_id=chat_id)
    _, select = call.data.split('_')

    if select == 'firstname':
        field = 'имя'
        new_field = 'новым именем'
        restrictions = '* не более 20 символов'
        user_profile.discussion_status = 'first_name'
    elif select == 'lastname':
        field = 'фамилия'
        new_field = 'новой фамилией'
        restrictions = '* не более 20 символов'
        user_profile.discussion_status = 'last_name'
    elif select == 'phone':
        field = 'номер телефона'
        new_field = 'новым номером'
        restrictions = '* формат ввода +7** или 8**'
        user_profile.discussion_status = 'phone_profile'
    elif select == 'address':
        field = 'фдрес доставки'
        new_field = 'новым адресом'
        restrictions = '* не более 200 символов'
        user_profile.discussion_status = 'address'
    else:
        field = 'ПАРМЕТР НЕИЗВЕСТЕН'
        new_field = 'ПАРМЕТР НЕИЗВЕСТЕН'
        restrictions = 'ПАРМЕТР НЕИЗВЕСТЕН'
    user_profile.save()

    text = f'''Редактируется <b>{field}</b>. Отправьте сообщение с {new_field}. Для отмены нажмите "Отменить"

{restrictions}'''

    menu = InlineKeyboardMarkup([[InlineKeyboardButton(text='Отменить', callback_data=f'profile_roll-back_{select}')]])

    context.bot.edit_message_text(chat_id=update.effective_chat.id, text=text, parse_mode='HTML',
                                  message_id=update.callback_query.message.message_id, reply_markup=menu)


dispatcher.add_handler(CallbackQueryHandler(message_edit_profile, pattern=str('edit_firstname')))
dispatcher.add_handler(CallbackQueryHandler(message_edit_profile, pattern=str('edit_lastname')))
dispatcher.add_handler(CallbackQueryHandler(message_edit_profile, pattern=str('edit_phone')))
dispatcher.add_handler(CallbackQueryHandler(message_edit_profile, pattern=str('edit_address')))


@connection_decorator
def info_main_menu(update: Update, context: CallbackContext):
    """Меню информации"""
    menu = InlineKeyboardMarkup([[InlineKeyboardButton(text='Адреса магазинов', callback_data='info_address')],
                                 [InlineKeyboardButton(text='Функции меню', callback_data='info_menu')],
                                 [InlineKeyboardButton(text='Меню: «Каталог товаров»', callback_data='info_catalog')],
                                 [InlineKeyboardButton(text='Меню: «Корзина / Оформление заказа»',
                                                       callback_data='info_cart')],
                                 [InlineKeyboardButton(text='Меню:  «Статусы заказов»', callback_data='info_orders')],
                                 [InlineKeyboardButton(text='Об оплате', callback_data='info_payment_menu')],
                                 [InlineKeyboardButton(text='Закрыть', callback_data='remove-message')]])
    text = "Выберите раздел справочной информации:"
    if update.callback_query:
        context.bot.edit_message_text(chat_id=update.effective_chat.id, text=text, reply_markup=menu,
                                      message_id=update.callback_query.message.message_id)
    else:
        message = context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=menu,
                                           disable_notification=True)
        context.bot.delete_message(chat_id=update.effective_chat.id,
                                   message_id=message.message_id - 1)


info_handler = CommandHandler('info', info_main_menu)
dispatcher.add_handler(info_handler)

info_query_handler = CallbackQueryHandler(info_main_menu, pattern=str('info_main_menu'))
dispatcher.add_handler(info_query_handler)


@connection_decorator
def info_address(update: Update, context: CallbackContext):
    """Информация об адресе"""
    if update.callback_query:
        context.bot.edit_message_text(chat_id=update.effective_chat.id, text=text.text_address, parse_mode='HTML',
                                      message_id=update.callback_query.message.message_id)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=text.text_address, parse_mode='HTML',
                                 disable_notification=True)
    img_1 = open(f'{BASE_DIR}/static/img/bot_info/map.png', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_1,
                           disable_notification=True)


info_address_handlers = [CommandHandler('map', info_address),
                         CallbackQueryHandler(info_address, pattern=str('info_address'))]
for handler in info_address_handlers:
    dispatcher.add_handler(handler)


@connection_decorator
def info_menu(update: Update, context: CallbackContext):
    """Информация о меню"""

    context.bot.edit_message_text(chat_id=update.effective_chat.id, text=text.text_menu_1, parse_mode='HTML',
                                  message_id=update.callback_query.message.message_id)
    img_1 = open(f'{BASE_DIR}/static/img/bot_info/23b4eb4b4b.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_1,
                           disable_notification=True)

    context.bot.send_message(chat_id=update.effective_chat.id, text=text.text_menu_2, parse_mode='HTML',
                             disable_notification=True)


info_menu_handler = CallbackQueryHandler(info_menu, pattern=str('info_menu'))
dispatcher.add_handler(info_menu_handler)


@connection_decorator
def info_menu_catalog(update: Update, context: CallbackContext):
    """Информация о каталоге"""

    context.bot.edit_message_text(chat_id=update.effective_chat.id, text=text.text_catalog_1, parse_mode='HTML',
                                  message_id=update.callback_query.message.message_id)
    img_1 = open(f'{BASE_DIR}/static/img/bot_info/photo_2023-08-22_10-44-02.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_1,
                           disable_notification=True)


info_menu_catalog_handler = CallbackQueryHandler(info_menu_catalog, pattern=str('info_catalog'))
dispatcher.add_handler(info_menu_catalog_handler)


@connection_decorator
def info_menu_cart(update: Update, context: CallbackContext):
    """Информация о корзине"""

    context.bot.edit_message_text(chat_id=update.effective_chat.id, text=text.text_cart_1, parse_mode='HTML',
                                  message_id=update.callback_query.message.message_id)
    img_1 = open(f'{BASE_DIR}/static/img/bot_info/98f1613ad4.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_1,
                           disable_notification=True)

    context.bot.send_message(chat_id=update.effective_chat.id, text=text.text_cart_2, parse_mode='HTML',
                             disable_notification=True)

    img_2 = open(f'{BASE_DIR}/static/img/bot_info/ba2772b058.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_2,
                           disable_notification=True)

    context.bot.send_message(chat_id=update.effective_chat.id, text=text.text_cart_3, parse_mode='HTML',
                             disable_notification=True)
    img_3 = open(f'{BASE_DIR}/static/img/bot_info/98f1613ad4.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_3,
                           disable_notification=True)

    context.bot.send_message(chat_id=update.effective_chat.id, text=text.text_cart_4, parse_mode='HTML',
                             disable_notification=True)
    img_4 = open(f'{BASE_DIR}/static/img/bot_info/48e8a35e69.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_4,
                           disable_notification=True)

    context.bot.send_message(chat_id=update.effective_chat.id, text=text.text_cart_5, parse_mode='HTML',
                             disable_notification=True)

    img_5 = open(f'{BASE_DIR}/static/img/bot_info/3bcd2b3173.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_5,
                           disable_notification=True)

    context.bot.send_message(chat_id=update.effective_chat.id, text=text.text_cart_6, parse_mode='HTML',
                             disable_notification=True)

    img_6 = open(f'{BASE_DIR}/static/img/bot_info/50b4bfd232.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_6,
                           disable_notification=True)


info_menu_cart_handler = CallbackQueryHandler(info_menu_cart, pattern=str('info_cart'))
dispatcher.add_handler(info_menu_cart_handler)


@connection_decorator
def info_menu_orders(update: Update, context: CallbackContext):
    """Информация о заказах"""

    context.bot.edit_message_text(chat_id=update.effective_chat.id, text=text.text_orders_1, parse_mode='HTML',
                                  message_id=update.callback_query.message.message_id)
    img_1 = open(f'{BASE_DIR}/static/img/bot_info/4d0846a4fe.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_1,
                           disable_notification=True)

    context.bot.send_message(chat_id=update.effective_chat.id, text=text.text_orders_2, parse_mode='HTML',
                             disable_notification=True)

    img_2 = open(f'{BASE_DIR}/static/img/bot_info/5b8b3884e3.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_2,
                           disable_notification=True)


info_menu_orders_handler = CallbackQueryHandler(info_menu_orders, pattern=str('info_orders'))
dispatcher.add_handler(info_menu_orders_handler)


@connection_decorator
def info_payment_menu(update: Update, context: CallbackContext):
    """Меню информации об оплате"""
    menu = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text='Оплата: «Через банковское приложение»', callback_data='info_payment_qr')],
         [InlineKeyboardButton(text='Оплата: «Ввод реквизитов»', callback_data='info_payment_card')],
         [InlineKeyboardButton(text='Назад', callback_data='info_main_menu')],
         [InlineKeyboardButton(text='Закрыть', callback_data='remove-message')]])

    context.bot.edit_message_text(chat_id=update.effective_chat.id, text=text.text_payment_1, reply_markup=menu,
                                  message_id=update.callback_query.message.message_id)


info_payment_menu_handler = CallbackQueryHandler(info_payment_menu, pattern=str('info_payment_menu'))
dispatcher.add_handler(info_payment_menu_handler)


@connection_decorator
def info_payment_qr(update: Update, context: CallbackContext):
    """Информация об оплате по qr"""

    context.bot.edit_message_text(chat_id=update.effective_chat.id, text=text.text_payment_qr_1, parse_mode='HTML',
                                  message_id=update.callback_query.message.message_id)
    img_1 = open(f'{BASE_DIR}/static/img/bot_info/photo_2023-08-22_11-45-18.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_1,
                           disable_notification=True)

    context.bot.send_message(chat_id=update.effective_chat.id, text=text.text_payment_qr_2, parse_mode='HTML',
                             disable_notification=True)

    img_2 = open(f'{BASE_DIR}/static/img/bot_info/photo_2023-08-22_11-59-12.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_2,
                           disable_notification=True)

    context.bot.send_message(chat_id=update.effective_chat.id, text=text.text_payment_qr_3, parse_mode='HTML',
                             disable_notification=True)

    img_3 = open(f'{BASE_DIR}/static/img/bot_info/photo_2023-08-22_11-59-16.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_3,
                           disable_notification=True)

    context.bot.send_message(chat_id=update.effective_chat.id, text=text.text_payment_qr_4, parse_mode='HTML',
                             disable_notification=True)

    img_4 = open(f'{BASE_DIR}/static/img/bot_info/photo_2023-08-22_11-59-19.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_4,
                           disable_notification=True)


info_payment_qr_handler = CallbackQueryHandler(info_payment_qr, pattern=str('info_payment_qr'))
dispatcher.add_handler(info_payment_qr_handler)


@connection_decorator
def info_payment_card(update: Update, context: CallbackContext):
    """Информация об оплате по карте"""

    context.bot.edit_message_text(chat_id=update.effective_chat.id, text=text.text_payment_card_1, parse_mode='HTML',
                                  message_id=update.callback_query.message.message_id)
    img_1 = open(f'{BASE_DIR}/static/img/bot_info/photo_2023-08-22_12-10-00.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_1,
                           disable_notification=True)


info_payment_card_handler = CallbackQueryHandler(info_payment_card, pattern=str('info_payment_card'))
dispatcher.add_handler(info_payment_card_handler)


# АДМИНИСТРАТИВНЫЕ
@connection_decorator
def manager_remove_order(user_order: object) -> str or bool:
    try:
        updater.bot.delete_message(chat_id=ORDERS_CHAT_ID, message_id=int(user_order.manager_message_id))
    except Exception as err:
        raise err


@connection_decorator
def manager_edit_order(user_order: object) -> str:
    """Изменить сообщение в канале менеджеров"""
    text_products = ''
    order_sum = 0
    carts = user_order.carts_set.filter(soft_delete=False).select_related('product')
    sale_type = user_order.sale_type
    fix = ''

    for cart in carts:
        if sale_type != 'no_sale':
            discount = getattr(cart.product.discount_group, f"{sale_type}_value")
            product_price = round(cart.product.price * discount)
        else:
            product_price = cart.product.price
        text_products += f'\n{cart.product.name} - {int(cart.amount)} шт.'
        order_sum += round(product_price * cart.amount, 2)
    order_message = f'{fix}\n<b><u>Заказ №: {user_order.id}</u></b> \n{text_products} \n{user_order.delivery_info} \n<b>на сумму: {math.ceil(order_sum) + user_order.delivery_price}</b>'
    try:
        updater.bot.edit_message_text(chat_id=ORDERS_CHAT_ID, message_id=user_order.manager_message_id,
                                      text=order_message, parse_mode='HTML')
        return 'Заявка изменена в канале менеджеров'
    except Exception as err:
        return f'Неудалось изменить заявку в канале менеджеров по причине: {err}'


@connection_decorator
def ready_order_message(chat_id: int, order_id: int, status: str, deliver: bool, order_sum: int = None,
                        delivery_price: int = 0,
                        pay_type: int = 1, tracing_num: str = 'нет', payment_url: str = None, bot_action: bool = False):
    """Сообщение о готовности заказа"""
    message = ''
    if status == '1':
        if deliver and delivery_price == 0 and payment_url:
            return 'error', 'Сумма к оплате 0'
        if payment_url:
            field = 'extra_payment_url'
            invoice_num, link = avangard_invoice(
                title=f'(Оплата доставки по заказу OttudaSPB № {order_id}, стоимость доставки {delivery_price} р.)',
                price=delivery_price,
                customer=f'{chat_id}',
                shop_order_num=order_id,
                pay_type=pay_type)
        else:
            field = 'payment_url'
            invoice_num, link = avangard_invoice(
                title=f'(Заказ в магазине OttudaSPB № {order_id}, сумма {order_sum} р.)',
                price=order_sum,
                customer=f'{chat_id}',
                shop_order_num=order_id,
                pay_type=pay_type)

        edit_order = Orders.objects.get(id=order_id)
        setattr(edit_order, field, link)
        edit_order.save()

        if not deliver:
            message = f'''<u> ожидает оплаты </u>\nваша ссылка на оплату: {link}'''
        elif payment_url:
            message = f''',в том числе доставка на сумму {delivery_price} р., \n<u> ожидает оплаты </u> доставки \nваша ссылка на оплату: {link}'''
        elif delivery_price == 0 and deliver:
            message = f'''\nдля резервирования товаров <u> требуется оплатить </u> по ссылке: {link} \nсчет на оплату транспортных мы вышлем позже, нам потребуется время для расчета стоимости\n спасибо за понимание'''
        else:
            message = f''',в том числе доставка на сумму {delivery_price} р., <u> ожидает оплаты </u> \nваша ссылка на оплату: {link}'''

    elif status == '2':
        updater.bot.send_message(chat_id=chat_id,
                                 text=f'Оплата по заказу № {order_id} поступила. Ваш заказ собирают...',
                                 parse_mode='HTML', disable_notification=True)
        updater.bot.send_message(chat_id=ORDERS_CHAT_ID, text=f'Поступила оплата по заказу № {order_id}')

        return
    elif status == '3':
        delivery_text = ''
        if delivery_price == 0:
            delivery_text = '(оплата доставки наложенным платежом)'
        message = f'поступил в доставку {delivery_text}. \n<b>Трек номер: {tracing_num or "нет"}</b>'
    elif status == '4':
        order_shop = Orders.objects.values('delivery_info').get(id=order_id)['delivery_info']
        message = f'ожидает вас в магазине по адресу: {" ".join(order_shop.split(" ")[-2:])}\nбольше информации о магазине по ссылке /map'
        if bot_action:
            updater.bot.send_message(chat_id=ORDERS_CHAT_ID, text=f'Поступила оплата по заказу № {order_id}')
    elif status == '6':
        message = 'был отменен'
    try:
        updater.bot.send_message(chat_id=chat_id,
                                 text=f'Ваш заказ № {order_id} на сумму {order_sum} р. {message}\nотслеживать свои заявки можно перейдя "Меню" -> "Статусы заказов"',
                                 parse_mode='HTML')
    except Exception as error:
        return 'error', error
    return 'ok', f'Ваш заказ № {order_id} на сумму {order_sum} р. {message}\nотслеживать свои заявки можно перейдя "Меню" -> "Статусы заказов"'


@connection_decorator
def message_to_manager(message=str):
    updater.bot.send_message(chat_id=ORDERS_CHAT_ID, text=message)


@connection_decorator
def send_message_to_user(chat_id: int, message: str, disable_notification: bool = True) -> tuple:
    try:
        updater.bot.send_message(chat_id=chat_id,
                                 text=f'''{message}''',
                                 parse_mode='HTML',
                                 disable_notification=disable_notification)
        return 'ok', 'Сообщение отправлено'
    except TelegramError as error:
        return 'error', error


# Утилиты
@connection_decorator
def unknown(update: Update, context: CallbackContext):
    """Неизветсные команды"""
    context.bot.send_message(chat_id=update.effective_chat.id, text="Извините, я не знаю такой команды")


unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler)


@connection_decorator
def user_message(update: Update, context: CallbackContext):
    """Принять сообщение пользователя (телефон, адрес, имя, фамилию)"""
    chat_id = update.message.chat_id
    user_profile = Profile.objects.get(chat_id=chat_id)
    status = user_profile.discussion_status

    if status == 'messaging':
        get_message_from_user(update, context)
    elif status in ['phone_main', 'phone_profile', 'phone']:
        check_result = phone_check(update=update, context=context, phone=update.message.text, trace_back=status)
        if check_result and status == 'phone':
            cart(update, context, call_func=True)
    elif status == 'first_name':
        profile_update(update=update, context=context, first_name=update.message.text)
    elif status == 'last_name':
        profile_update(update=update, context=context, last_name=update.message.text)
    elif status == 'address':
        profile_update(update=update, context=context, address=update.message.text)
    elif status == 'offer_address':
        Profile.objects.filter(chat_id=chat_id).update(discussion_status='messaging',
                                                       delivery_street=update.message.text)
        get_offer_settings(update=update, context=context, settings_stage='3', answer='street')


get_user_message = MessageHandler(Filters.text, user_message)
dispatcher.add_handler(get_user_message)


@connection_decorator
def remove_bot_message(update: Update, context: CallbackContext):
    """Закрыть сообщение бота"""
    call = update.callback_query
    context.bot.delete_message(chat_id=call.message.chat.id,
                               message_id=call.message.message_id)


remove_message = CallbackQueryHandler(remove_bot_message, pattern=str('remove-message'))
dispatcher.add_handler(remove_message)


@connection_decorator
def get_message_from_user(update: Update, context: CallbackContext):
    """ Получить сообщение от пользователя"""
    messages = UserMessage.objects.filter(checked=False)
    if len(messages) < 2:
        user_profile = Profile.objects.get(chat_id=update.message.chat_id)
        UserMessage.objects.create(user=user_profile, message=update.message.text)
        message = 'Мы получили ваше сообщение.В ближайшее время менеджер c вами свяжется...'
    else:
        message = 'Мы уже получили от вас сообщение, подождите пока менеджер вам ответит...'
    update.message.reply_text(message)


dispatcher.add_handler(MessageHandler(filters.Filters.text, get_message_from_user))

if __name__ == '__main__':
    updater.start_polling()
