import datetime

from bs4 import BeautifulSoup
import logging
import http.client

from shop.telegram import settings
from shop.telegram.http_adapter import get_legacy_session

TEST = False
user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36'


def avangard_invoice(title: str, price: int, customer: str, shop_order_num: int, pay_type: int = 1) -> (int, str):
    http.client.HTTPConnection.debuglevel = 0

    logging.basicConfig(filename='banking.log')
    logging.getLogger().setLevel(logging.DEBUG)
    # requests_log = logging.getLogger("requests.packages.urllib3")
    # requests_log.setLevel(logging.DEBUG)
    # requests_log.propagate = True

    base_url = 'https://shop.avangard.ru/v5_iacq/faces/links/'
    login_url = base_url + 'login.xhtml'
    orders_url = base_url + 'orders.xhtml'

    # открытие сессии
    session = get_legacy_session()

    # обновление headers сессии
    session.headers.update({'User-Agent': user_agent})

    # автооризация
    session.post(login_url, settings.BANKING_CREDENTIALS)

    resp = session.get(orders_url)

    bs = BeautifulSoup(resp.text, 'html.parser')
    view_state = bs.find(id='j_id1:javax.faces.ViewState:0')['value']
    order_num = bs.find(id='order_form:num')['value']
    date_today = datetime.date.today()
    date_to = date_today + datetime.timedelta(days=2)

    order_form = {'javax.faces.partial.ajax': 'true',
                  'javax.faces.source': 'order_form:j_idt59',
                  'javax.faces.partial.execute': 'order_form:add_panel order_form:orders_panel order_form:dialog_contents',
                  'javax.faces.partial.render': 'order_form:add_panel order_form:orders_panel order_form:dialog_contents order_form:main_msg',
                  'order_form:j_idt59': 'order_form: j_idt59',
                  'order_form': 'order_form',
                  'order_form:num': order_num,
                  'order_form:products': {title},
                  'order_form:price_input': f'{price},00',
                  'order_form:price_hinput': f'{price}',
                  'order_form:customer': customer,
                  'order_form:deliveryDateFrom_input': date_today.strftime('%d.%m.%Y'),
                  'order_form:deliveryDateTo_input': date_to.strftime('%d.%m.%Y'),
                  'order_form:pay_type': pay_type,
                  'order_form:comments': shop_order_num,
                  'order_form:timeLimitType': 'LIMIT_TYPE_WHILE',
                  'order_form:periodType': 'PERIOD_TYPE_DAY',
                  'order_form:j_idt52_input': 1,
                  'order_form:rowCountCombo': 100,
                  'javax.faces.ViewState': view_state}

    # запоняем форму для получения ссылки на оплату
    session.post(orders_url, data=order_form, allow_redirects=False)

    resp = session.get(orders_url)

    bs = BeautifulSoup(resp.text, 'html.parser')

    my_order = ''
    order_raw = bs.find(class_='row sol_t')
    search = order_raw.find('div', string={order_num})
    if search:
        my_order = order_raw

    if not my_order:
        order_list = bs.find_all(class_='row sol_t')

        for order in order_list:
            search = order.find('div', string={order_num})
            if search:
                my_order = order
                break

    # полчаем ссылку
    payment_link = my_order.find_all('a')[1].text

    session.close()
    return order_num, payment_link


def avangard_check(orders: dict):
    http.client.HTTPConnection.debuglevel = 0

    logging.basicConfig(filename='banking.log')
    logging.getLogger().setLevel(logging.DEBUG)
    # requests_log = logging.getLogger("requests.packages.urllib3")
    # requests_log.setLevel(logging.DEBUG)
    # requests_log.propagate = True

    base_url = 'https://shop.avangard.ru/v5_iacq/faces/links/'
    login_url = base_url + 'login.xhtml'
    orders_url = base_url + 'orders.xhtml'
    checked = {}

    # открытие сессии
    with get_legacy_session() as session:
        if TEST:
            with open('test_payment.html', encoding="UTF-8", ) as html:
                bs = BeautifulSoup(html, 'html.parser')
        else:
            print('here')
            # обновление headers сессии
            session.headers.update({'User-Agent': user_agent})
            # автооризация

            session.post(login_url, settings.BANKING_CREDENTIALS)

            resp = session.get(orders_url)
            bs = BeautifulSoup(resp.text, 'html.parser')

        raw_payment_orders = bs.find_all(class_='row sol_t')
        for payment_order in raw_payment_orders:
            check_id = payment_order.find(class_='comment_button check')
            if payment_order.find(class_='status_PAYED') is not None:
                payed = int(payment_order.find(class_='col-3').string.strip().split(',')[0].replace(' ', ''))
                checked[orders.filter(id=check_id.string.strip())] = payed
        return checked
