<template>
    <div class="telegram-app_telegram_app__6iz4V">
        <div class="stack-navigation_screen___5WKf screen-0">
            <div class="checkout-next_checkout_page__QByc_">
                <div class="checkout-next_form__XiskP">
                    <div class="">
                        <div class="how-to-receive_title__ckftj">Как получать</div>
                        <div class="selector_selector__FIbjw how-to-receive_selector__O0K0i">
                            <div @click="delivery = false"
                                 class="selector_item__HELzt"
                                 :class="{ 'selector_active__IjaYo': !delivery }">
                                В&nbsp;магазине&nbsp;(СПБ Прачечный 3)
                            </div>

                            <div @click="delivery = true"
                                 class="selector_item__HELzt"
                                 :class="{ 'selector_active__IjaYo': delivery }">
                                Доставка
                            </div>
                        </div>
                        <div class="">
                            <div v-if="delivery">
                                <div v-if="user.user_data.delivery_street === null"
                                     class="phone-input_phone_input__1gFbW shop_phone__Mf6wI react-tel-input ">
                                    <input class="form-control " placeholder="Укажие адрес доставки" type="text"
                                           required="" value="" v-model="new_delivery_street">
                                    <div class="flag-dropdown ">
                                        <div class="selected-flag" title="" tabindex="0" role="button"
                                             aria-haspopup="listbox">
                                            <div class="flag 0">
                                                <div class="arrow"></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <a v-else @click="editLink" class="shop_address__KrvpM" href="">
                                <span class="shop_icon__QVYKr">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"
                                         fill="currentColor" stroke="none"
                                         class="tabler-icon tabler-icon-map-pin-filled ">
                                        <path d="M18.364 4.636a9 9 0 0 1 .203 12.519l-.203 .21l-4.243 4.242a3 3 0 0 1 -4.097 .135l-.144 -.135l-4.244 -4.243a9 9 0 0 1 12.728 -12.728zm-6.364 3.364a3 3 0 1 0 0 6a3 3 0 0 0 0 -6z"></path>
                                    </svg>
                                </span>
                                    <span> {{ user.user_data.delivery_street  }} </span>
                                    <svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="none"
                                         viewBox="0 0 10 18">
                                        <path stroke="#000" stroke-linecap="square" stroke-width="2.167"
                                              d="m1.652 15.5 6.5-6.5-6.5-6.5"></path>
                                    </svg>
                                </a>
                            </div>


                            <div v-if="user.user_data.phone === null"
                                 class="phone-input_phone_input__1gFbW shop_phone__Mf6wI react-tel-input ">
                                <input class="form-control " placeholder="Укажите номер телефона" type="number"
                                       autocomplete="tel" required="" value="" v-model="new_phone">
                                <div class="flag-dropdown ">
                                    <div class="selected-flag" title="" tabindex="0" role="button"
                                         aria-haspopup="listbox">
                                        <div class="flag 0">
                                            <div class="arrow"></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <!--                    <div class="">-->
                    <!--                        <div class="checkout-cashback_text__G_Fqm">text-->
                    <!--                        </div>-->
                    <!--                    </div>-->

                    <!--                    <div class="promo-code_promo_code__ccc2y">-->
                    <!--                        <div class="promo-code_controls__ZzZOO"><input type="text" class="promo-code_input__cc4kw"-->
                    <!--                                                                       placeholder="Введите промокод" value="">-->
                    <!--                            <button class="promo-code_button__Wz_9C">Применить</button>-->
                    <!--                        </div>-->
                    <!--                    </div>-->
                    <div class="">
                        <div class="how-to-receive_title__ckftj">Как оплатить?</div>
                        <div class="selector_selector__FIbjw how-to-receive_selector__O0K0i">
                            <div @click="payment = 2"
                                 class="selector_item__HELzt "
                                 :class="{ 'selector_active__IjaYo': payment === 2 }">Через банковское приложение (СБП)
                            </div>
                            <div @click="payment = 1"
                                 class="selector_item__HELzt"
                                 :class="{ 'selector_active__IjaYo': payment === 1 }">Ввести реквизиты карты
                            </div>
                        </div>
                    </div>
                    <div class="" v-if="cartPreorder === 'both' && user.user_data.preorder">
                        <div class="how-to-receive_title__ckftj">Как разделить в наличии и предзаказ?</div>
                        <div class="selector_selector__FIbjw how-to-receive_selector__O0K0i" style="margin-bottom:5px">
                            <div @click="preorderSelector = 'split'"
                                 class="selector_item__HELzt"
                                 :class="{ 'selector_active__IjaYo': preorderSelector === 'split' }">Разделить на 2
                                зказа
                            </div>
                            <div @click="preorderSelector = 'part-order'"
                                 class="selector_item__HELzt "
                                 :class="{ 'selector_active__IjaYo': preorderSelector === 'part-order' }">Только в наличии
                            </div>
                        </div>
                        <div class="selector_selector__FIbjw how-to-receive_selector__O0K0i">
                            <div @click="preorderSelector = 'part-preorder'"
                                 class="selector_item__HELzt"
                                 :class="{ 'selector_active__IjaYo': preorderSelector === 'part-preorder' }">Только
                                предзаказ
                            </div>
                            <div @click="preorderSelector = 'preorder'"
                                 class="selector_item__HELzt"
                                 :class="{ 'selector_active__IjaYo': preorderSelector === 'preorder' }">Все в предзаказ
                            </div>
                        </div>
                    </div>
                </div>
                <hr>
                <div v-if="cartPreorder !== 'preorder'" class="checkout-price_checkout_price__VkrsP">
                    <div class="checkout-price_item__ZN9st checkout-price_sale___0caE">
                        <div class="checkout-price_left__a71WQ">
                            <div>Всего</div>
                            <div class="checkout-price_description__zO_ho"></div>
                        </div>
                        <div class="checkout-price_right__uabtm">
                            <div>{{ totalSum }}&nbsp;₽</div>
                        </div>
                    </div>
                    <div class="checkout-price_item__ZN9st checkout-price_sale___0caE">
                        <div class="checkout-price_left__a71WQ">
                            <div>Скидка</div>
                            <div class="checkout-price_description__zO_ho"></div>
                        </div>
                        <div class="checkout-price_right__uabtm">
                            <div>{{ totalSum - totalDiscountSum }}&nbsp;₽</div>
                        </div>
                    </div>
                    <div class="checkout-price_item__ZN9st">
                        <div class="checkout-price_left__a71WQ">
                            <div>Итого</div>
                            <div class="checkout-price_description__zO_ho"></div>
                        </div>
                        <div class="checkout-price_right__uabtm">
                            <div><b>{{ totalDiscountSum }}&nbsp;₽</b></div>
                        </div>
                    </div>
                </div>
                <div @click="createOrder()" class="button_button__AjjDz">
                    <span v-if="cartPreorder === 'preorder'">Отправить предзаказ</span>
                    <span v-else>Отправить заказ</span>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { useAuthStore, getCSRFToken } from '../users/auth.js'
import { useRouter } from 'vue-router'

import jsonData from '../response.json' // Import the data

export default {
    name: 'OrderView',
    data() {
        return {
            user: {
                    user_id: '',
                    user_data: []
                },
            cartItems: [],
            new_phone: null,
            new_delivery_street: null,
            delivery: false,
            preorder: false,
            preorderSelector: 'split',
            payment: 2,
            totalCount: 0,
            totalSum: 0,
            totalDiscountSum: 0,
            cartPreorder: 'order'
        }
    },

    async created() {
        await this.fetchProfile();
        await this.fetchCart();
    },

    async mounted() {
        const options = {
            root: null,
            rootMargin: '0px',
            threshold: 1.0
        };

        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && !this.isLoading) {
                this.fetchCart();
            }
        }, options);

        if (this.$refs.observerPoint) {
            observer.observe(this.$refs.observerPoint);
        }
    },

    methods: {
        async fetchProfile() {
                try {
                    // jsonData window.Telegram.WebApp.initDataUnsafe?.user
                    const tg_user = jsonData
                    this.user.user_id = tg_user.user.id
                    // const response = await fetch(`https://refactored-fishstick-jj7qgwww9x94cq4r6-8000.app.github.dev/api/main/${tg_user.id}`)
                    // const data = await response.json()

                    const response = await fetch(`http://localhost:8000/api/profile/${this.user.user_id}`)
                    this.user.user_data = await response.json()
                    console.log(this.user)

                  } catch (error) {
                    console.log(error);
                }
            },

        async fetchCart() {
            try {
                const url = `http://localhost:8000/api/cart?chat_id=${this.user.user_id}`;
                const response = await fetch(url);

                if (response.ok) {
                    const data = await response.json();
                    this.cartItems = data.results || [];
                    this.totalCount = this.cartItems.length;
                    this.totalSum = data.total_carts_sum;

                    const hasPreorders = this.cartItems.some(item => item.preorder === true);
                    const hasRegulars = this.cartItems.some(item => item.preorder === false);

                    if (hasPreorders && hasRegulars) {
                        this.cartPreorder = 'both';
                    } else if (hasPreorders) {
                        this.cartPreorder = 'preorder';
                    } else {
                        this.cartPreorder = 'order';
                    }
                    this.preorder = hasPreorders;


                    const firstItem = this.cartItems[0];
                    const globalDiscountType = firstItem?.product?.rests?.[0]?.shop_active_discount;
                    this.discount = globalDiscountType;

                    const total = this.cartItems.reduce((acc, item) => {
                        if (item.preorder) return acc;

                        const price = Number(item.price) || 0;
                        const qty = Number(item.amount) || 0;
                        const group = item.product?.discount_group;

                        let factor = 1;
                        if (globalDiscountType === 'regular' && group?.regular_value) {
                            factor = Number(group.regular_value);
                        } else if (globalDiscountType === 'extra' && group?.extra_value) {
                            factor = Number(group.extra_value);
                        }

                        return acc + Math.round(price * factor * qty);
                    }, 0);

                    this.totalDiscountSum = total;
                }
            } catch (error) {
                console.error("Ошибка при загрузке корзины:", error);
            }
        },

        async updateProfile() {
            try {
                const payload = {
                    chat_id: this.user.user_id
                };

                if (!this.user.user_data.phone) {
                    payload.phone = this.new_phone;
                }

                if (!this.user.user_data.delivery_street && this.delivery === true) {
                    payload.delivery_street = this.new_delivery_street;
                }

                const response = await fetch('http://localhost:8000/api/profile/update/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken(),
                    },
                    body: JSON.stringify(payload),
                    credentials: 'include',
                });

                const data = await response.json();
                if (response.ok) {
                    this.user.user_data = data;
                    console.log("Профиль обновлен");
                } else {
                    console.error("Ошибка:", data);
                }
            } catch (error) {
                console.error("Ошибка сети:", error);
            }
        },

        async createOrder() {
            try {
                if (this.new_phone || this.new_delivery_street) {
                    await this.updateProfile();
                }

                const payload = {
                    chat_id: this.user.user_id,
                    order_price: this.totalDiscountSum,
                    deliver: this.delivery,
                    payment: this.payment,
                    sale_type: this.discount
                };

                if (this.user.user_data.preorder) {
                    if (this.cartPreorder === 'both') {
                        // Если в корзине и то, и другое — берем выбор из селектора
                        payload.preorder = this.preorderSelector;
                    } else if (this.cartPreorder === 'preorder') {
                        // Если только предзаказы
                        payload.preorder = 'part-preorder';
                    } else {
                        // Если только обычные товары (cartPreorder === 'order')
                        payload.preorder = 'part-order';
                    }
                }


                if (this.delivery) {
                    payload.delivery_info = this.new_delivery_street || this.user.user_data.delivery_street || "СПБ пер. Прачечный 3";
                }


                const response = await fetch('http://localhost:8000/api/orders/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken()
                    },
                    body: JSON.stringify(payload),
                    credentials: 'include',
                });

                if (response.ok) {
                    console.log("Заказ успешно создан");
                    this.$router.push({ path: '/orders_history' });
                } else {
                    const errorData = await response.json();
                    console.error("Ошибка сервера:", errorData);
                }
            } catch (error) {
                console.error("Ошибка при выполнении createOrder:", error);
            }
        },

        async editLink() {
            this.$router.push({
            path: '/edit_profile'
            });
        }
    }
}
</script>
