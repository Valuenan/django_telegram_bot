import logging
import math
import re
import json
import os

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import close_old_connections, connection, utils
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, error, Bot, WebAppInfo
from telegram.ext import Updater, CallbackContext, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, \
    filters
from telegram.error import TelegramError

from django_telegram_bot.settings import BASE_DIR, MINI_APP_URL
from shop.models import Category, Shop, Product, BotSettings, Rests
from shop.telegram.banking.banking import avangard_invoice
from shop.telegram.settings import TOKEN, ORDERS_CHAT_ID, SUPPORT_CHAT_ID, WEBHOOK_PORT
from users.models import Profile, UserMessage, Carts, Orders, OrderStatus
import shop.telegram.bot_texts as text

LOG_FILENAME = 'bot_log.txt'
logger = logging.getLogger(__name__)
bot = Bot(token=TOKEN)
updater = Updater(token=TOKEN)
dispatcher = updater.dispatcher
PORT = int(os.environ.get('PORT', WEBHOOK_PORT))
MAX_LEN_MESSAGE = 3800


@csrf_exempt
def webhook(request):
    if request.method == 'POST':
        update = Update.de_json(json.loads(request.body), bot)
        dispatcher.process_update(update)

    return HttpResponse(request.body, status=200)


def connection_decorator(func):
    def inner(*args, **kwargs):
        close_old_connections()
        connection.ensure_connection()
        return func(*args, **kwargs)

    return inner


bot_settings = BotSettings.objects.all()
try:
    bot_settings = bot_settings[0]
    ADMIN_TG = bot_settings.tg_help
    PRODUCTS_PAGINATION_NUM = bot_settings.products_pagination
    BUTTONS_IN_ROW_CATEGORY = bot_settings.buttons_in_row
except IndexError:
    logger.error("Отсутствуют насройки для бота. Зайдите в админку и укажите настройки в 'Настройки бота'")


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
        except utils.OperationalError:
            Profile.objects.create(first_name='', last_name='', telegram_name=user.username,
                                   chat_id=chat_id, discussion_status='phone_main')
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
def app(update: Update, context: CallbackContext):
    """Miniapp телеграмм"""
    user = update.message.from_user
    chat_id = update.message.chat_id
    caption_text = f"<b>Добро пожаловать, {user.first_name}!</b>\nОткройте приложение по кнопке ниже"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Открыть приложение", web_app=WebAppInfo(url=MINI_APP_URL))]
    ])
    img_path = os.path.join(os.path.dirname(__file__), 'main.png')
    with open(img_path, 'rb') as photo:
        context.bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=caption_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )


app_handler = CommandHandler('app', app)
dispatcher.add_handler(app_handler)


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
    chat_id = update.effective_chat.id
    if update.callback_query:
        call = update.callback_query
        chosen_category = call.data.split('_')
        if chosen_category[1] != 'None':
            this_category = Category.objects.select_related('parent_category').get(id=int(chosen_category[1]))
            categories = Category.objects.select_related('parent_category').filter(parent_category=this_category,
                                                                                   hide=False)
        else:
            categories = Category.objects.select_related('parent_category').filter(parent_category=None, hide=False)
            flag_prew_category = False
    else:
        categories = Category.objects.select_related('parent_category').filter(parent_category=None, hide=False)

    user_profile = Profile.objects.get(chat_id=chat_id)
    if categories:
        for category in categories:
            parent_category = category.parent_category
            parent_category_id = None

            have_products = Rests.objects.filter(product__category=category, amount__gt=0)
            have_child_category = Category.objects.filter(parent_category=category, hide=False)
            if not have_child_category and not have_products and not user_profile.preorder:
                continue

            if parent_category:
                parent_category_id = parent_category.id
            button = (InlineKeyboardButton(text=category.command,
                                           callback_data=f'category_{category.id}_{parent_category_id}'))
            if len(buttons[-1]) % BUTTONS_IN_ROW_CATEGORY == 0:
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
            get_pre_order = lambda user_profile: 'ВКЛЮЧЕН' if user_profile.preorder else 'ОТКЛЮЧЕН'
            text = f'Каталог: <b>ПРЕДЗАКАЗ {get_pre_order(user_profile)}</b>'
        keyboard = InlineKeyboardMarkup([button for button in buttons])
        message = context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=text, reply_markup=keyboard, disable_notification=True,
                                           parse_mode='HTML')
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
    chat_id = update.effective_chat.id
    discount = 1

    if '#' in str(update.callback_query.data) and not chosen_category:
        chosen_category = update.callback_query.data.split('_')[1]
        chosen_category, page = chosen_category.split('#')
        page = int(page)

    user_profile = Profile.objects.get(chat_id=chat_id)
    products = Product.objects.order_by('name').select_related('discount_group', 'image', 'category').filter(
        category=chosen_category)
    if user_profile.preorder is False:
        products = products.filter(rests__amount__gt=0, price__gt=0)
    if products.count() > PRODUCTS_PAGINATION_NUM:
        pages = (len(products) - 1) // PRODUCTS_PAGINATION_NUM
        start = page * PRODUCTS_PAGINATION_NUM
        end = start + PRODUCTS_PAGINATION_NUM
        pagination = True
        products = products[start: end]

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

            if discount == 1 or product.price == 0 or rests == 0:
                if product.price == 0:
                    text_price = 'неизвестна'
                else:
                    text_price = str(product.price) + ' р.'
                product_info = f'''{product.name}  \n <b>Цена: {text_price}</b> \n <i>В наличии: {int(rests)} шт.</i>'''
            else:
                product_info = f'''{product.name}  \n <b>Цена: <s>{product.price}</s> {round(product.price * discount)}.00 р.</b>\n Скидка: {(1 - discount) * 100}% \n <i>В наличии: {int(rests)} шт.</i> '''

            if int(rests) > 0:
                add_button = InlineKeyboardButton(text='🟢 Добавить', callback_data=f'add_{product.id}')
            else:
                add_button = InlineKeyboardButton(text='🟡 Заказать', callback_data=f'preorder_{product.id}')

            if product.description != '':
                description_button = [
                    InlineKeyboardButton(text='📄 Описание', callback_data=f'description_{product.id}')]
            else:
                description_button = []

            buttons = (
                [add_button, InlineKeyboardButton(text='🧡', callback_data=f'track_{product.id}')], description_button)
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
def add_to_track(update: Update, context: CallbackContext):
    """Показать фото с составом и обратно"""
    call = update.callback_query
    chat_id = update.effective_chat.id
    _, product_id = call.data.split('_')
    profile = Profile.objects.only('track').get(chat_id=chat_id)
    if profile.track.filter(id=product_id).exists():
        profile.track.remove(product_id)
        context.bot.answer_callback_query(callback_query_id=call.id, text=f'Товар убран из избранного')
    else:
        profile.track.add(product_id)
        context.bot.answer_callback_query(callback_query_id=call.id, text=f'Товар добавлен в избранное')


add_to_track_handler = CallbackQueryHandler(add_to_track, pattern="^" + str('track_'))
dispatcher.add_handler(add_to_track_handler)


@connection_decorator
def product_description(update: Update, context: CallbackContext):
    """Показать описание товара"""
    call = update.callback_query

    side, product_id = call.data.split('_')

    product = Product.objects.get(id=product_id)

    rests = product.rests_set.values('amount').all()[0]['amount']
    discount = 1
    if side == 'description':
        description_button = InlineKeyboardButton(text='🏷️ Ценник', callback_data=f'product-info_{product.id}')
        product_info = product.description
    else:
        description_button = InlineKeyboardButton(text='📄 Описание', callback_data=f'description_{product.id}')
        sale_type = Shop.objects.values("sale_type").get(id=1)['sale_type']
        if sale_type != 'no_sale':
            discount = getattr(product.discount_group, f'{sale_type}_value')

        if discount == 1 or product.price == 0 or rests == 0:
            if product.price == 0:
                text_price = 'неизвестна'
            else:
                text_price = str(product.price) + ' р.'
            product_info = f'''{product.name}  \n <b>Цена: {text_price}</b> \n <i>В наличии: {int(rests)} шт.</i>'''
        else:

            product_info = f'''{product.name}  \n <b>Цена: <s>{product.price}</s> {round(product.price * discount)}.00 р.</b>\n Скидка: {(1 - discount) * 100}% \n <i>В наличии: {int(rests)} шт.</i> '''

    if int(rests) > 0:
        add_button = InlineKeyboardButton(text='🟢 Добавить', callback_data=f'add_{product.id}')
    else:
        add_button = InlineKeyboardButton(text='🟡 Заказать', callback_data=f'preorder_{product.id}')

    buttons = ([add_button, InlineKeyboardButton(text='🧡', callback_data=f'track_{product.id}')], [description_button])
    keyboard = InlineKeyboardMarkup([button for button in buttons])

    try:
        context.bot.edit_message_text(text=product_info, chat_id=call.message.chat.id,
                                      message_id=call.message.message_id, reply_markup=keyboard, parse_mode='HTML')
    except:
        context.bot.send_message(call.message.chat.id, "Описания не оказалось 😨", disable_notification=True)


product_description_handler = CallbackQueryHandler(product_description, pattern="^" + str('description_'))
dispatcher.add_handler(product_description_handler)

product_description_handler = CallbackQueryHandler(product_description, pattern="^" + str('product-info_'))
dispatcher.add_handler(product_description_handler)


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
    if not cart_info and command in ['add', 'add-cart', 'preorder', 'preorder-cart']:
        profile = Profile.objects.get(chat_id=chat_id)
        cart_info = Carts.objects.create(profile=profile, product_id=product_id, amount=1, price=product_info.price)
        amount = 1
        if command in ['preorder', 'preorder-cart']:
            cart_info.preorder = True
            cart_info.save()
    elif not cart_info and command == 'remove':
        amount = 0
    else:
        cart_info = cart_info[0]
        amount = cart_info.amount
        if command in ['add', 'add-cart']:
            if amount < product_rests:
                amount += 1
        elif command in ['preorder', 'preorder-cart']:
            amount += 1
        elif command in ['remove', 'remove-cart']:
            amount -= 1
        else:
            amount = 0
        if amount == 0:
            cart_info.delete()
        else:
            cart_info.amount = amount
            cart_info.save()

    return product_info.name, amount, product_rests, cart_info


@connection_decorator
def edit(update: Update, context: CallbackContext):
    """Добавить/Удаить товар в корзине"""

    call = update.callback_query
    chat_id = call.from_user.id
    command, product_id = call.data.split('_')
    product_name, amount, product_rests, _ = _cart_edit(chat_id, product_id, command)

    context.bot.answer_callback_query(callback_query_id=call.id,
                                      text=f'В корзине {product_name[:20]}... {amount} шт.')


catalog_handler = CallbackQueryHandler(edit, pattern="^" + str('add_'))
dispatcher.add_handler(catalog_handler)

catalog_handler = CallbackQueryHandler(edit, pattern="^" + str('preorder_'))
dispatcher.add_handler(catalog_handler)

catalog_handler = CallbackQueryHandler(edit, pattern="^" + str('remove_'))
dispatcher.add_handler(catalog_handler)


def show_cart_(index: int, sale_type: object, cart_info: object, cart_discount: int, cart_price: int,
               cart_message: str) -> (int, str):
    if sale_type != 'no_sale':
        discount = getattr(cart_info.product.discount_group, f'{sale_type}_value')
        price_count = round(round(cart_info.price * discount), 2)
        cart_discount += (cart_info.price - price_count) * cart_info.amount
    else:
        price_count = cart_info.price
    cart_price += round(int(price_count) * cart_info.amount)
    cart_message += f'{index + 1}. {cart_info.product.name} - {int(cart_info.amount)} шт. по {cart_info.price} р.\n'
    return cart_price, cart_message, cart_discount


@connection_decorator
def show_favorite(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    products = Profile.objects.prefetch_related('track').get(chat_id=chat_id).track.all()
    sale_type = Shop.objects.values("sale_type").get(id=1)['sale_type']
    pagination = False
    pages = None
    page = 0
    if update.callback_query:
        call = update.callback_query
        page = call.data.split('_')[1]
        page = int(page)
        pagination = True
        context.bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)

    if products.count() > PRODUCTS_PAGINATION_NUM:
        pages = (len(products) - 1) // PRODUCTS_PAGINATION_NUM
        start = page * PRODUCTS_PAGINATION_NUM
        end = start + PRODUCTS_PAGINATION_NUM
        pagination = True
        products = products[start: end]

    if products:
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

            try:
                product_photo = open(f'{BASE_DIR}/static/products/{product_img[0]}', 'rb')
            except FileNotFoundError:
                product_photo = open(f'{BASE_DIR}/static/products/no-image.jpg', 'rb')
            rests = product.rests_set.values('amount').all()[0]['amount']

            if product.price == 0 or rests == 0 or sale_type == 'no_sale':
                if product.price == 0:
                    text_price = 'неизвестна'
                else:
                    text_price = str(product.price) + ' р.'
                product_info = f'''{product.name}  \n <b>Цена: {text_price} </b> \n <i>В наличии: {int(rests)} шт.</i>'''
            else:
                discount = getattr(product.discount_group, f'{sale_type}_value')
                product_info = f'''{product.name}  \n <b>Цена: <s>{product.price}</s> {round(product.price * discount)}.00 р.</b>\n Скидка: {(1 - discount) * 100}% \n <i>В наличии: {int(rests)} шт.</i> '''

            if int(rests) > 0:
                add_button = InlineKeyboardButton(text='🟢 Добавить', callback_data=f'add_{product.id}')
            else:
                add_button = InlineKeyboardButton(text='🟡 Заказать', callback_data=f'preorder_{product.id}')

            if product.description != '':
                description_button = [
                    InlineKeyboardButton(text='📄 Описание', callback_data=f'description_{product.id}')]
            else:
                description_button = []

            buttons = (
                [add_button, InlineKeyboardButton(text='🧡', callback_data=f'track_{product.id}')], description_button)
            keyboard = InlineKeyboardMarkup([button for button in buttons])

            context.bot.send_photo(chat_id=update.effective_chat.id,
                                   photo=product_photo,
                                   disable_notification=True)
            logger.info(f'{update.effective_chat.id=} \n {product_info=} \n {keyboard=}')
            context.bot.send_message(chat_id=update.effective_chat.id, text=product_info,
                                     reply_markup=keyboard,
                                     parse_mode='HTML', disable_notification=True)

        if pagination and page < pages:
            header_text = f'Страница <b>{page + 1}</b> из {pages + 1}'
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(text='Еще товары', callback_data=f'favorite_{page + 1}')]])
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=header_text,
                                     disable_notification=True,
                                     reply_markup=keyboard, parse_mode='HTML')
    else:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Закрыть', callback_data='remove-message')]])
        message = context.bot.send_message(chat_id=update.effective_chat.id, text=f'Пока что вы ничего не отслеживаете',
                                           disable_notification=True, reply_markup=keyboard)
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message.message_id - 1)


show_favorite_handler = CommandHandler('favorite', show_favorite)
dispatcher.add_handler(show_favorite_handler)

show_favorite_handler = CallbackQueryHandler(show_favorite, pattern="^" + str('favorite_'))
dispatcher.add_handler(show_favorite_handler)


@connection_decorator
def cart(update: Update, context: CallbackContext, call_func=False, call_delete_old=False):
    """Показать корзину покупателя/ Отмена удаления корзины"""
    profile = Profile.objects.only('cart_message_id', 'preorder').get(chat_id=update.effective_chat.id)
    if update.callback_query:
        call = update.callback_query
        chat_id = call.from_user.id
        if 'return-to-cart_' in call.data:
            messages = call.data.split('_')[1]
            messages = messages.split('-')[0:-1]
            for message_id in messages:
                context.bot.delete_message(chat_id=call.message.chat_id,
                                           message_id=int(message_id))
        if 'return-to-cart_' in call.data or (call_delete_old and profile.cart_message_id != 0):
            try:
                context.bot.delete_message(chat_id=chat_id, message_id=profile.cart_message_id)
            except error.BadRequest:
                pass

    else:
        chat_id = update.message.chat_id
        try:
            if profile.cart_message_id != 0:
                context.bot.delete_message(chat_id=chat_id, message_id=profile.cart_message_id)
        except error.BadRequest:
            pass
    sale_type = Shop.objects.values('sale_type').get(id=1)['sale_type']
    carts = Carts.objects.order_by('preorder').select_related('product', 'product__discount_group').filter(
        order__isnull=True, profile__chat_id=chat_id, soft_delete=False)
    cart_price = 0

    cart_discount = 0

    if profile.preorder:
        preorder_carts = []
        cart_message = '<u>Предзаказ включен</u>\n\n<b>В наличии:</b>\n'
    else:
        cart_message = '<u>Предзаказ отключен</u>\n\n<b>В наличии:</b>\n'

    if len(carts) > 0 and (profile.preorder is False and carts.filter(preorder=False) or profile.preorder):
        for index, cart_info in enumerate(carts):
            if profile.preorder and cart_info.preorder:
                preorder_carts.append(cart_info)
                continue
            if not profile.preorder and cart_info.preorder:
                continue
            cart_price, cart_message, cart_discount = show_cart_(index, sale_type, cart_info, cart_discount, cart_price,
                                                                 cart_message)
        else:

            if sale_type == 'no_sale' and cart_price > 0:
                cart_message += f'<b><i>Итого: {cart_price}.00 р.</i></b>\n'
            elif cart_price > 0:
                cart_message += f'Ваша скидка: {round(cart_discount, 2)} р.\n Итого co скидкой: {cart_price}.00 р.\n'
            else:
                cart_message += 'Пусто'
            if profile.preorder and preorder_carts:
                cart_message += '\n\n<b>Предзаказ: \n(Новая цена может отличаться)</b>\n'
                for index, cart_info in enumerate(preorder_carts):
                    _, cart_message, _ = show_cart_(index, sale_type, cart_info, cart_discount, cart_price,
                                                    cart_message)
        buttons = ([InlineKeyboardButton(text='Оформить заказ 📝', callback_data='offer-stage_0_none')],
                   [InlineKeyboardButton(text='Очистить 🗑️', callback_data='delete-cart'),
                    InlineKeyboardButton(text='Редактировать 📋', callback_data='correct-cart')])

        keyboard = InlineKeyboardMarkup([button for button in buttons])

        if update.callback_query and not call_delete_old:
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
    carts_preorder = Carts.objects.filter(profile__chat_id=chat_id, preorder=True, order__isnull=True,
                                          soft_delete=False)
    carts_regular = Carts.objects.filter(profile__chat_id=chat_id, preorder=False, order__isnull=True,
                                         soft_delete=False)

    if not profile.phone:
        profile.discussion_status = 'phone'
        profile.save()
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Для оформления заказа требуется ваш номер телефона, напишите его в чат. Формат (+7** или 8**)')
    else:
        if profile.preorder and settings_stage == '0':
            if carts_preorder and carts_regular:

                buttons = [[InlineKeyboardButton(text=f'Заказать часть - предзаказ',
                                                 callback_data='offer-stage_1_part-preorder')],
                           [InlineKeyboardButton(text=f'Заказать часть - в наличии',
                                                 callback_data='offer-stage_1_part-order')],
                           [InlineKeyboardButton(text=f'Разделить на 2 заказа',
                                                 callback_data='offer-stage_1_split')],
                           [InlineKeyboardButton(text=f'Все товары в предзаказ',
                                                 callback_data='offer-stage_1_preorder')]]

                keyboard = InlineKeyboardMarkup(buttons)
                context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                              message_id=message_id,
                                              text=f'У вас в заказе есть товары в наличии и по предзаказу, хотите:',
                                              reply_markup=keyboard)
            elif carts_preorder:
                settings_stage = '1'
                answer = 'preorder'
            elif carts_regular:
                settings_stage = '1'
                answer = 'part-order'
        elif settings_stage == '0':
            settings_stage = '1'
            answer = 'part-order'
    if user_orders and answer in ['none'] and settings_stage == '1':
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
    elif settings_stage == '1':
        if answer in ['split', 'part-order', 'part-preorder', 'preorder']:
            profile.preorder_selector = answer
            profile.save()
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Да', callback_data='offer-stage_2_yes'),
                                          InlineKeyboardButton(text='Нет', callback_data='offer-stage_2_no')]])
        context.bot.edit_message_text(chat_id=chat_id,
                                      message_id=message_id,
                                      text=f'Вам доставить? 🚚 \n(доставка будет рассчитана после оформления заказа)',
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
            text = f'Выберите последний адрес доставки или отправьте сообщение с новым адресом доставки'
            buttons = []
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
            buttons = []
            keyboard = InlineKeyboardMarkup(buttons)
            if profile.delivery_street:
                buttons.insert(0, [
                    InlineKeyboardButton(text=profile.delivery_street, callback_data=f'offer-stage_3_street')])
            context.bot.edit_message_text(chat_id=chat_id,
                                          message_id=message_id,
                                          text=f'Нужно указать адрес. Для этого отправьте в чат сообщение адресом',
                                          reply_markup=keyboard)
            break_flag = True

        elif answer == 'street':
            profile.delivery = 1
        else:
            profile.main_shop = Shop.objects.get(id=int(answer))
            profile.delivery = 0
        profile.save()

        if not break_flag:
            profile.discussion_status = 'messaging'
            profile.save()
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
                                   callback_data=f'offer-stage_0_none')]])

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
    cart_info = Carts.objects.order_by('preorder').prefetch_related('product').only('amount', 'preorder'). \
        filter(profile__chat_id=chat_id, soft_delete=False, order__isnull=True)
    message_id = update.callback_query.message.message_id
    context.bot.delete_message(chat_id=chat_id,
                               message_id=message_id)
    if len(cart_info) > 0:
        for cart in cart_info:
            product_info = cart.product
            product_rests = product_info.rests_set.values('amount').all()[0]['amount']
            if cart.preorder:
                add_button = InlineKeyboardButton(text='🟡 Заказать',
                                                  callback_data=f'preorder-cart_{product_info.id}')
            else:
                add_button = InlineKeyboardButton(text='🟢 Добавить', callback_data=f'add-cart_{product_info.id}')

            if cart.amount == product_rests:
                keyboard_edit = InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text='🔴 Убрать', callback_data=f'remove-cart_{product_info.id}')]])

            else:
                buttons = ([add_button,
                            InlineKeyboardButton(text='🔴 Убрать', callback_data=f'remove-cart_{product_info.id}')],)
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
    product_name, amount, product_rests, cart_info = _cart_edit(chat_id, product_id, command)
    if cart_info.preorder:
        add_button = InlineKeyboardButton(text='🟡 Заказать', callback_data=f'preorder-cart_{product_id}')
    else:
        add_button = InlineKeyboardButton(text='🟢 Добавить', callback_data=f'add-cart_{product_id}')

    message = f'{product_name} - {amount} шт.'
    if amount == 0:
        keyboard_edit = InlineKeyboardMarkup(
            [[add_button]])
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
        buttons = ([add_button,
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

edit_cart_handler = CallbackQueryHandler(edit_cart, pattern="^" + str('preorder-cart_'))
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
    order_products = Carts.objects.filter(profile=profile, order__isnull=True, preorder=False)
    if profile.preorder is False or profile.preorder_selector in ['split', 'part-order']:
        text_products, sum_message, full_discount, order_sum = '', '', 0, 0
        user_order = Orders.objects.create(profile=profile, delivery_info=call.message.text, deliver=deliver,
                                           order_price=cart_price, payment_id=int(payment_type), sale_type=sale_type,
                                           status=order_status)

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

    if profile.preorder and profile.preorder_selector in ['split', 'part-preorder', 'preorder']:
        text_products = ''

        if profile.preorder_selector == 'preorder':
            preorder_products = Carts.objects.filter(profile=profile, order__isnull=True)
        else:
            preorder_products = Carts.objects.filter(profile=profile, order__isnull=True, preorder=True)
        for preorder_product in preorder_products:
            text_products += f'\n{preorder_product.product.name} - {preorder_product.amount} шт.'
        order_status = OrderStatus.objects.get(title='7')
        user_order = Orders.objects.create(profile=profile, delivery_info=call.message.text, deliver=deliver,
                                           order_price=cart_price, payment_id=int(payment_type), sale_type=sale_type,
                                           status=order_status)

        order_message = f'<b><u>Заказ №: {user_order.id}</u></b> \n{text_products} \n{call.message.text} \n'
        message = context.bot.send_message(text=f'Клиент: {user} \n{order_message}', chat_id=ORDERS_CHAT_ID,
                                           parse_mode='HTML')
        if profile.preorder_selector == 'split':
            context.bot.send_message(
                text=f'Ваш {order_message} \n\nЗаказ принят, ожидйте поступления товара в магазин, после поступления мы направим вам ссылку на оплату.',
                chat_id=call.message.chat.id, parse_mode='HTML')
        else:
            context.bot.edit_message_text(
                text=f'Ваш {order_message} \n\nЗаказ принят, ожидйте поступления товара в магазин, после поступления мы направим вам ссылку на оплату.',
                chat_id=call.message.chat.id,
                message_id=call.message.message_id, parse_mode='HTML')
        preorder_products.update(order=user_order)
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
def orders_history(update: Update, context: CallbackContext, request_chat_id=None):
    """Вызов истории покупок (в статусе кроме исполненно или отменено) версия 1"""
    chat_id = request_chat_id or update.effective_chat.id
    orders = Orders.objects.prefetch_related('carts').filter(profile__chat_id=chat_id).exclude(
        status__in=[6, 7]).order_by('id')
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text='Закрыть', callback_data='remove-message')]])
    # chat_id обязательно update.effective_chat.id, при запросе из чата поддержки что бы отправлялось не клиенту а в поддержку
    if not orders:
        message = context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='У вас нет заказов',
                                           reply_markup=keyboard, disable_notification=True)
    else:
        orders_text = ''
        for order in orders:
            payment_urls_text, text_products, tracing_text = '', '', ''
            full_price, product_price_sum, position = 0, 0, 1
            for cart in order.carts.filter(soft_delete=False):
                if order.sale_type != 'no_sale':
                    discount = getattr(cart.product.discount_group, f'{order.sale_type}_value')
                    calc_price = round(cart.price * discount) * cart.amount
                else:
                    calc_price = cart.price * cart.amount
                product_price_sum += calc_price
                full_price += cart.product.price * cart.amount
                text_products += f'<i>{position}.</i> {cart.product.name} - {cart.amount} шт.'
                if str(order.status) != 'Предзаказ':
                    text_products += f' по {cart.price} р.'
                text_products += '\n'
                position += 1
            else:
                if order.delivery_price > 0:
                    delivery_price_text = f'\nСтоимость доставки {order.delivery_price} р.'
                else:
                    delivery_price_text = ''
                if order.sale_type != 'no_sale' and full_price != product_price_sum and str(
                        order.status) != 'Предзаказ':
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

                orders_text += f'''<b><u>Заказ № {order.id}</u></b> \n <u>Статус заказа: {order.status}</u> \n{tracing_text}{text_products}{delivery_price_text}'''
                if str(order.status) != 'Предзаказ':
                    orders_text += f'ИТОГО: {round(full_price + order.delivery_price, 2)} р.{discount_text}{payment_urls_text}'
                orders_text += f'\n {"_" * 20} \n'
        # chat_id обязательно update.effective_chat.id, при запросе из чата поддержки что бы отправлялось не клиенту а в поддержку

        if len(orders_text) > MAX_LEN_MESSAGE:
            split_long_text = orders_text[MAX_LEN_MESSAGE:].split('\n', 1)
            long_text_parts = [orders_text[:MAX_LEN_MESSAGE] + split_long_text[0]]
            while len(split_long_text[1]) > MAX_LEN_MESSAGE:
                orders_text = split_long_text[1]
                split_long_text = orders_text[MAX_LEN_MESSAGE:].split('\n', 1)
                long_text_parts.append(orders_text[:MAX_LEN_MESSAGE] + split_long_text[0])
            else:
                long_text_parts.append(split_long_text[1])

            for index, text_message in enumerate(long_text_parts):
                if update.callback_query and index == 0:
                    context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                                  text=text_message,
                                                  reply_markup=keyboard, parse_mode='HTML',
                                                  message_id=update.callback_query.message.message_id, )
                else:
                    context.bot.send_message(chat_id=update.effective_chat.id,
                                             text=text_message,
                                             reply_markup=keyboard, parse_mode='HTML',
                                             disable_notification=True)
        else:

            if update.callback_query:
                context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                              text=orders_text,
                                              reply_markup=keyboard, parse_mode='HTML',
                                              message_id=update.callback_query.message.message_id, )
            else:
                message = context.bot.send_message(chat_id=update.effective_chat.id,
                                                   text=orders_text,
                                                   reply_markup=keyboard, parse_mode='HTML', disable_notification=True)
            if not update.callback_query and request_chat_id is None:
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
    pre_order_status = {True: 'Включено', False: 'Отключено'}
    if update.callback_query:
        call = update.callback_query
        data = call.data
        chat_id = call.message.chat_id
        if call.data != 'edit_pre_order':
            _, action, field = call.data.split('_')
    else:
        data = None
        chat_id = update.message.chat_id
    user_profile = Profile.objects.get(chat_id=chat_id)

    if user_profile.discussion_status != 'messaging':
        user_profile.discussion_status = 'messaging'
        user_profile.save()

    if data == 'edit_pre_order':
        status = lambda user_profile: False if user_profile.preorder else True
        user_profile.preorder = status(user_profile)
        user_profile.save()

    get_pre_order = lambda user_profile: True if user_profile.preorder else False
    pre_order_status = pre_order_status[get_pre_order(user_profile)]

    menu = InlineKeyboardMarkup([[InlineKeyboardButton(text='Изменить имя', callback_data='edit_firstname')],
                                 [InlineKeyboardButton(text='Изменить фамилию', callback_data='edit_lastname')],
                                 [InlineKeyboardButton(text='Изменить номер телефона', callback_data='edit_phone')],
                                 [InlineKeyboardButton(text='Изменить адрес доставки', callback_data='edit_address')],
                                 [InlineKeyboardButton(
                                     text=f'Показывать товары для предзаказа',
                                     callback_data='edit_pre_order')],
                                 [InlineKeyboardButton(text='Закрыть', callback_data='remove-message')]])

    profile_message = f"Профиль: \n Имя: <b>{user_profile.first_name or 'нет'}</b> \n Фамилия: <b>{user_profile.last_name or 'нет'}</b> \n Телефон №: <b>{user_profile.phone or 'нет'}</b> \n Адрес доставки: <b>{user_profile.delivery_street or 'нет'}</b> \n Показывать товары для предзаказа: <b>{pre_order_status}</b>"
    if update.callback_query:
        context.bot.edit_message_text(chat_id=update.effective_chat.id, text=profile_message, reply_markup=menu,
                                      parse_mode='HTML', message_id=update.callback_query.message.message_id)
    else:
        message = context.bot.send_message(chat_id=update.effective_chat.id, text=profile_message, reply_markup=menu,
                                           parse_mode='HTML', disable_notification=True)
        context.bot.delete_message(chat_id=update.effective_chat.id,
                                   message_id=message.message_id - 1)
    if data == 'edit_pre_order':
        cart(update, context, call_func=True, call_delete_old=True)


dispatcher.add_handler(CommandHandler('profile', profile_menu))

dispatcher.add_handler(CallbackQueryHandler(profile_menu, pattern=str('profile_roll-back_firstname')))
dispatcher.add_handler(CallbackQueryHandler(profile_menu, pattern=str('profile_roll-back_lastname')))
dispatcher.add_handler(CallbackQueryHandler(profile_menu, pattern=str('profile_roll-back_phone')))
dispatcher.add_handler(CallbackQueryHandler(profile_menu, pattern=str('profile_roll-back_address')))
dispatcher.add_handler(CallbackQueryHandler(profile_menu, pattern=str('edit_pre_order')))


@connection_decorator
def message_edit_profile(update: Update, context: CallbackContext):
    """Профиль: Изменить имя"""
    call = update.callback_query
    chat_id = call.message.chat_id
    user_profile = Profile.objects.get(chat_id=chat_id)
    _, select = call.data.split('_')

    options = {'firstname': {'field': 'имя',
                             'new_field': 'новым именем',
                             'restrictions': '* не более 20 символов',
                             'discussion_status': 'first_name'
                             },
               'lastname': {'field': 'фамилия',
                            'new_field': 'новой фамилией',
                            'restrictions': '* не более 20 символов',
                            'discussion_status': 'last_name'
                            },
               'phone': {'field': 'номер телефона',
                         'new_field': 'новым номером',
                         'restrictions': '* формат ввода +7** или 8**',
                         'discussion_status': 'phone_profile'
                         },
               'address': {'field': 'адрес доставки',
                           'new_field': 'новым адресом',
                           'restrictions': '* не более 200 символов',
                           'discussion_status': 'address'
                           },
               }

    option = options[select]
    user_profile.discussion_status = option['discussion_status']
    user_profile.save()

    text = f'''Редактируется <b>{option['field']}</b>. Отправьте сообщение с {option['new_field']}. Для отмены нажмите "Отменить"

{option['restrictions']}'''

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
                                 [InlineKeyboardButton(text='Меню:  «Избранное»', callback_data='info_favorite_menu')],
                                 [InlineKeyboardButton(text='Об оплате', callback_data='info_payment_menu')],
                                 [InlineKeyboardButton(text='Вкл/откл функции предзаказа',
                                                       callback_data='info_switch_preorder')],
                                 [InlineKeyboardButton(text='Оформление заказа с товарами по предзаказу',
                                                       callback_data='info_preorder_cart')],
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
def info_switch_preorder(update: Update, context: CallbackContext):
    """Информация об включении режима предзаказа"""
    if update.callback_query:
        context.bot.edit_message_text(chat_id=update.effective_chat.id, text=text.text_preorder, parse_mode='HTML',
                                      message_id=update.callback_query.message.message_id)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=text.text_preorder, parse_mode='HTML',
                                 disable_notification=True)
    img_1 = open(f'{BASE_DIR}/static/img/bot_info/6dc518ac4b.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_1,
                           disable_notification=True)
    img_2 = open(f'{BASE_DIR}/static/img/bot_info/4dc1980a8b.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_2,
                           disable_notification=True)


info_switch_preorder_handlers = [CommandHandler('info_switch_preorder', info_switch_preorder),
                                 CallbackQueryHandler(info_switch_preorder, pattern=str('info_switch_preorder'))]
for handler in info_switch_preorder_handlers:
    dispatcher.add_handler(handler)


@connection_decorator
def info_preorder_cart(update: Update, context: CallbackContext):
    """Информация об включении режима предзаказа"""
    if update.callback_query:
        context.bot.edit_message_text(chat_id=update.effective_chat.id, text=text.text_cart_preorder,
                                      message_id=update.callback_query.message.message_id)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=text.text_cart_preorder,
                                 disable_notification=True)
    img_1 = open(f'{BASE_DIR}/static/img/bot_info/2e89385d34.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_1,
                           disable_notification=True)


info_preorder_cart_handlers = [CommandHandler('info_preorder_cart', info_preorder_cart),
                               CallbackQueryHandler(info_preorder_cart, pattern=str('info_preorder_cart'))]
for handler in info_preorder_cart_handlers:
    dispatcher.add_handler(handler)


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
def info_favorite(update: Update, context: CallbackContext):
    """Информация о каталоге избранного"""
    if update.callback_query:
        context.bot.edit_message_text(chat_id=update.effective_chat.id, text=text.text_favorite_1, parse_mode='HTML',
                                      message_id=update.callback_query.message.message_id)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=text.text_favorite_1, parse_mode='HTML',
                                 disable_notification=True)
    img_1 = open(f'{BASE_DIR}/static/img/bot_info/7e98e6b416.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_1,
                           disable_notification=True)
    context.bot.send_message(chat_id=update.effective_chat.id, text=text.text_favorite_2, disable_notification=True)
    img_2 = open(f'{BASE_DIR}/static/img/bot_info/320add2b59.jpg', 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=img_2,
                           disable_notification=True)


info_favorite_handlers = [CommandHandler('info_favorite', info_favorite),
                          CallbackQueryHandler(info_favorite, pattern=str('info_favorite_menu'))]
for handler in info_favorite_handlers:
    dispatcher.add_handler(handler)


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
    carts = user_order.carts.filter(soft_delete=False).select_related('product')
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
                                 text=f'''<b>Ответ службы поддержки:</b>\n{message}''',
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
    if getattr(update, 'channel_post') is None:
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
    else:
        support_answer = update.channel_post.text
        answer_to_message_id = update.channel_post.reply_to_message.message_id
        user_chat_id = UserMessage.objects.values('user__chat_id').get(support_message_id=answer_to_message_id)[
            'user__chat_id']
        if support_answer[0] == '#':
            try:
                SUPPORT_FUNCTIONS[support_answer.strip()](update, context, request_chat_id=user_chat_id)
            except KeyError:
                context.bot.send_message(chat_id=SUPPORT_CHAT_ID,
                                         text='Вы вызвали запрос, поставив "#" в начале предложения. Но по данному запросу нет дейсвий',
                                         parse_mode='HTML')
        else:
            author_signature = update.channel_post.author_signature
            support_text = f'<b>Ответ службы поддержки:</b>\n{support_answer}'
            context.bot.send_message(chat_id=user_chat_id, text=support_text, parse_mode='HTML')
            user_profile = Profile.objects.get(chat_id=user_chat_id)
            UserMessage.objects.create(user=user_profile, message=support_text, checked=True,
                                       manager_signature=author_signature)
            UserMessage.objects.filter(user=user_profile).update(checked=True)


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
        forwarded = update.message.forward(chat_id=SUPPORT_CHAT_ID)
        UserMessage.objects.create(user=user_profile, message=update.message.text,
                                   support_message_id=forwarded.message_id)
        message = 'Мы получили ваше сообщение.В ближайшее время менеджер c вами свяжется...'
    else:
        message = 'Мы уже получили от вас сообщение, подождите пока менеджер вам ответит...'
    update.message.reply_text(message)


dispatcher.add_handler(MessageHandler(filters.Filters.text, get_message_from_user))

SUPPORT_FUNCTIONS = {'#заказы': orders_history,
                     '#заказ': orders_history}
