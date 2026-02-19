<script>
import { ref, onMounted } from 'vue'
import { useAuthStore, getCSRFToken } from '../users/auth.js'
import { useRouter } from 'vue-router'

export default {
    name: 'CartView',
    setup() {
        const authStore = useAuthStore();
        const router = useRouter();
        const isTelegram = ref(false);
        const tg = window.Telegram?.WebApp;

        onMounted(() => {
            if (tg?.initData) {
                isTelegram.value = true;
                tg.ready();
                tg.expand();
            }
        });

        return {
            authStore,
            router,
            isTelegram,
            tg
        }
    },

    data() {
        return {
            user_id: '',
            cartItems: [],
            nextPageUrl: null,
            totalCount: 0,
            loading: false,
            baseUrl: import.meta.env.VITE_API_URL
        }
    },

    async created() {
        const tgUser = this.tg?.initDataUnsafe?.user;
        this.user_id = tgUser?.id;
        await this.fetchCart();
    },

    mounted() {
        const options = {
            root: null,
            rootMargin: '100px',
            threshold: 0.1
        };

        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && !this.loading && this.nextPageUrl) {
                this.fetchCart();
            }
        }, options);

        if (this.$refs.observerPoint) {
            observer.observe(this.$refs.observerPoint);
        }
    },

    computed: {
        finalTotal() {
            if (!this.cartItems || this.cartItems.length === 0) return 0;

            const globalDiscountType = this.cartItems[0].product?.rests[0]?.shop_active_discount;

            return this.cartItems.reduce((acc, item) => {
                if (item.preorder) return acc;

                const price = Number(item.price) || 0;
                const qty = item.amount || 0;
                const group = item.product?.discount_group;

                let factor = 1;
                if (globalDiscountType === 'regular' && group?.regular_value) {
                    factor = Number(group.regular_value);
                } else if (globalDiscountType === 'extra' && group?.extra_value) {
                    factor = Number(group.extra_value);
                }

                return acc + Math.round(price * factor) * qty;
            }, 0);
        }
    },

    methods: {
        async fetchCart() {
            if (this.loading) return;

            this.loading = true;
            try {
                const url = this.nextPageUrl || `${this.baseUrl}/api/cart/?chat_id=${this.user_id}`;
                const response = await fetch(url);

                if (response.ok) {
                    const data = await response.json();
                    const newItems = data.results || [];
                    this.cartItems = this.nextPageUrl ? [...this.cartItems, ...newItems] : newItems;

                    this.nextPageUrl = data.next || null;
                    this.totalCount = data.count || this.cartItems.length;
                }
            } catch (error) {
                console.error("Ошибка загрузки корзины:", error);
            } finally {
                this.loading = false;
            }
        },

        async deleteCart(cart) {
            try {
                const response = await fetch(`${this.baseUrl}/api/cart/${cart.id}/?chat_id=${this.user_id}`, {
                    method: 'DELETE',
                    headers: { 'X-CSRFToken': getCSRFToken() },
                });

                if (response.ok) {
                    this.cartItems = this.cartItems.filter(item => item.id !== cart.id);
                }
            } catch (error) {
                console.error("Ошибка при удалении:", error);
            }
        },

        async toggleTrack(product) {
            try {
                const response = await fetch(`${this.baseUrl}/api/profile/track/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken(),
                    },
                    body: JSON.stringify({
                        chat_id: this.user_id,
                        product_id: product.id
                    }),
                    credentials: 'include',
                });

                if (response.ok) {
                    const data = await response.json();

                    if (product && product.id === product.id) {
                        product.is_tracked = !product.is_tracked;
                    }

                }
            } catch (e) {
                console.error("Ошибка при обновлении трека:", e);
            }
        },

        async changeCount(cart, delta) {
            const maxRest = cart.product?.rests[0]?.amount || 0;
            const nextValue = cart.amount + delta;

            if (!cart.preorder && delta > 0 && nextValue > maxRest) {
                return;
            }

            if (nextValue <= 0) {
                await this.deleteCart(cart);
                return;
            }

            const oldAmount = cart.amount;
            cart.amount = nextValue;

            try {
                const response = await fetch(`${this.baseUrl}/api/cart/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken(),
                    },
                    body: JSON.stringify({
                        chat_id: this.user_id,
                        product: cart.product.id,
                        amount: cart.amount,
                        price: cart.price,
                    }),
                });

                if (!response.ok) throw new Error();

                const data = await response.json();
                cart.id = data.id;
            } catch (error) {
                cart.amount = oldAmount;
                console.error("Ошибка обновления количества");
            }
        },

        handleImageError(event) {
            event.target.src = `${this.baseUrl}/static/products/no-image.jpg`;
        },

        async orderLink(id) {
            this.$router.push({
            path: '/order/'
            });
        },

        productLink(id) {
            this.router.push({
            path: '/product/',
            query: { id: id }
            });
        }
    }
}

</script>

<template>
    <div class="telegram-app_telegram_app__6iz4V">
        <div class="stack-navigation_screen___5WKf">
            <div class="cart-screen_cart_screen__y134H">
                <div class="cart-screen_wrapper__LWL3f">
                    <div class="home-screen_header__yUTVr">
                        <div class="home-screen_content__qET3x">
                            <svg version="1.0" xmlns="http://www.w3.org/2000/svg"
                                 width="800.000000pt" height="400.000000pt"
                                 viewBox="0 0 800.000000 400.000000"
                                 preserveAspectRatio="xMidYMid meet">

                                <g transform="translate(0.000000,400.000000) scale(0.100000,-0.100000)"
                                   fill="#1a75bb" stroke="none">
                                    <path d="M1973 3868 c-11 -13 -28 -37 -37 -55 -30 -59 -74 -207 -80 -270 -4
-38 -19 -87 -40 -130 -32 -67 -33 -71 -39 -238 -4 -113 -10 -182 -20 -205 -8
-19 -17 -77 -21 -129 -3 -52 -8 -96 -9 -98 -12 -12 -153 -53 -181 -53 -41 0
-51 13 -61 85 -8 53 -42 131 -80 180 -12 17 -51 45 -85 63 -60 31 -68 32 -177
32 -122 0 -118 2 -127 -59 -4 -26 5 -54 34 -116 21 -44 41 -99 45 -121 4 -21
14 -61 23 -89 15 -43 17 -103 17 -455 0 -297 -4 -411 -13 -426 -6 -12 -16 -82
-22 -155 -5 -73 -16 -154 -24 -179 -8 -25 -17 -73 -20 -107 -3 -35 -10 -71
-16 -80 -5 -10 -16 -47 -24 -83 -13 -61 -33 -131 -71 -245 -9 -27 -44 -107
-78 -177 -49 -103 -65 -128 -81 -128 -34 1 -200 94 -214 121 -20 38 -11 980
10 1029 11 26 17 84 20 215 l5 180 48 139 c30 88 93 232 175 397 70 142 130
273 132 291 3 18 15 70 27 115 21 79 21 84 5 118 -23 49 -62 79 -169 130 -90
43 -93 44 -202 46 -61 1 -117 -2 -123 -6 -13 -8 -90 -162 -90 -180 0 -6 -16
-48 -35 -92 -19 -45 -35 -86 -35 -93 0 -7 -6 -26 -14 -43 -48 -104 -142 -426
-152 -517 -3 -36 -10 -75 -15 -87 -5 -12 -13 -82 -19 -155 -6 -73 -17 -153
-25 -178 -7 -25 -16 -74 -20 -109 -3 -35 -12 -80 -20 -100 -7 -20 -16 -74 -20
-121 -4 -47 -13 -99 -20 -117 -20 -47 -21 -472 -1 -550 8 -32 17 -97 21 -146
5 -79 34 -192 79 -314 30 -81 105 -182 163 -221 31 -20 74 -49 97 -64 22 -16
84 -42 136 -59 89 -29 105 -31 248 -31 l153 -1 42 32 c47 36 81 52 182 90 88
33 119 72 167 207 51 140 108 345 124 439 4 22 13 54 19 70 7 17 16 59 20 95
4 36 13 79 20 96 7 17 15 83 19 148 4 71 12 126 20 139 9 15 16 76 20 200 5
134 10 184 21 200 23 33 21 283 -2 317 -13 19 -18 46 -18 110 l0 84 43 8 c24
4 54 3 69 -3 l26 -10 -6 -124 c-4 -89 -10 -131 -22 -149 -14 -22 -16 -96 -18
-703 l-2 -678 48 -144 c58 -174 67 -192 113 -228 28 -21 50 -28 98 -31 58 -4
68 -1 151 43 119 62 165 101 222 190 28 43 55 75 65 75 12 0 26 -28 53 -109
20 -61 45 -122 57 -136 30 -38 90 -65 146 -65 61 0 196 66 287 141 66 54 81
59 90 29 3 -11 40 -51 82 -89 98 -91 179 -121 320 -121 141 0 228 31 315 112
69 66 81 84 122 183 45 112 73 175 80 182 13 13 26 -22 26 -70 0 -59 15 -89
73 -145 91 -89 314 -133 410 -82 54 29 65 26 78 -22 39 -143 84 -207 173 -249
54 -26 72 -29 158 -29 126 0 256 40 302 92 29 34 90 155 131 262 42 111 96
219 105 210 5 -5 12 -50 14 -99 11 -181 111 -505 164 -534 22 -12 427 -16 456
-5 9 3 25 22 37 42 12 21 70 108 128 194 58 87 116 176 129 198 13 22 27 38
31 35 5 -2 11 -43 14 -91 7 -103 25 -131 112 -183 51 -31 69 -36 166 -45 76
-6 135 -6 192 1 82 11 82 11 132 65 28 30 69 91 93 135 23 45 49 84 57 87 18
7 40 -25 54 -80 7 -25 30 -62 63 -98 l53 -58 84 -10 c47 -5 114 -7 150 -3 62
6 69 10 113 55 67 69 241 336 304 466 47 98 54 119 54 173 0 58 -1 61 -24 61
-35 0 -57 -10 -49 -23 3 -6 1 -7 -6 -3 -6 4 -25 -4 -43 -19 -17 -14 -47 -34
-67 -45 -20 -10 -71 -51 -114 -90 -43 -39 -82 -68 -88 -65 -15 10 -10 79 11
147 11 34 20 72 20 84 0 11 9 46 19 77 19 55 24 95 22 190 -1 36 -7 54 -24 71
-21 21 -34 23 -183 30 -88 4 -167 4 -176 1 -47 -18 -293 -374 -383 -553 -47
-96 -75 -132 -99 -132 -11 0 -6 55 8 100 8 25 29 101 46 170 18 69 41 148 52
175 11 28 28 73 38 101 28 80 99 217 134 258 36 43 76 55 182 56 84 0 119 20
127 72 7 47 -5 63 -65 85 -131 49 -185 58 -395 61 l-202 3 -39 -50 c-59 -75
-278 -524 -285 -586 -8 -70 -54 -148 -144 -245 -43 -46 -92 -104 -109 -129
-39 -57 -101 -117 -111 -107 -4 4 -9 64 -11 134 -3 81 -9 137 -18 154 -18 35
-18 121 0 156 9 18 16 86 20 197 4 94 13 190 21 215 29 95 55 230 55 286 1
102 38 334 72 449 12 39 35 102 53 140 17 39 35 83 39 99 9 37 130 279 191
381 26 44 86 154 133 245 46 91 99 185 116 210 76 111 94 168 81 265 -6 53 -8
56 -48 75 -95 43 -166 62 -257 69 -56 5 -108 15 -127 24 -42 22 -80 21 -128
-3 -22 -11 -50 -20 -63 -20 -15 0 -21 -4 -16 -12 5 -8 2 -9 -11 -4 -15 5 -42
-17 -130 -107 -94 -96 -118 -127 -152 -198 -54 -111 -213 -583 -213 -631 0
-13 -9 -58 -20 -99 -16 -59 -20 -107 -20 -237 l0 -162 31 -32 c24 -26 29 -38
24 -58 -14 -49 -17 -165 -5 -203 7 -26 8 -42 1 -50 -5 -7 -11 -33 -13 -57 -3
-42 -5 -45 -28 -41 -14 2 -146 6 -294 8 l-269 4 -39 -38 c-102 -99 -282 -421
-337 -603 -76 -248 -74 -242 -126 -300 -27 -30 -72 -75 -99 -98 -53 -48 -66
-45 -66 15 0 18 -8 52 -17 75 -16 37 -18 75 -17 273 1 251 9 297 84 521 16 49
33 113 36 142 l7 52 -94 1 c-52 1 -142 3 -201 4 -68 1 -113 -2 -121 -9 -21
-17 -57 -111 -57 -148 0 -47 -16 -98 -61 -195 -21 -46 -55 -124 -75 -171 -20
-48 -51 -118 -69 -157 -18 -38 -45 -99 -60 -135 -14 -36 -32 -78 -40 -95 -7
-16 -41 -100 -75 -185 -34 -85 -64 -161 -67 -168 -7 -16 -53 -16 -53 1 0 6 7
39 15 72 19 79 62 297 70 360 10 82 74 344 121 500 21 71 42 165 76 330 5 28
27 91 49 142 43 102 48 133 21 133 -9 0 -34 9 -55 20 -33 18 -56 20 -236 20
l-200 0 -19 -27 c-29 -42 -48 -88 -82 -198 -18 -55 -38 -117 -46 -138 -8 -20
-14 -46 -14 -56 0 -10 -23 -88 -51 -172 -83 -250 -100 -317 -114 -454 -8 -71
-18 -148 -24 -170 -6 -22 -13 -51 -15 -65 -4 -18 -24 -37 -65 -64 -33 -20 -85
-60 -116 -87 -107 -93 -120 -72 -112 182 4 142 10 195 21 218 13 23 16 66 17
198 0 162 6 223 28 308 5 22 14 67 20 100 10 65 14 82 73 290 97 344 86 326
210 360 47 14 115 29 150 34 169 24 344 118 364 195 7 31 -16 75 -61 115 -43
38 -92 41 -178 11 -31 -11 -67 -20 -80 -20 -14 0 -53 -9 -87 -20 -85 -27 -146
-27 -153 0 -6 23 6 123 21 173 6 17 13 84 15 149 3 64 11 126 18 140 7 12 16
66 20 118 4 52 15 112 23 132 24 57 21 190 -5 245 -11 24 -25 43 -30 43 -6 0
-7 5 -4 10 3 6 -3 10 -14 10 -11 0 -43 9 -71 20 -41 16 -74 20 -178 20 -87 0
-133 -4 -144 -12 -21 -17 -75 -124 -83 -168 -4 -19 -11 -40 -16 -46 -5 -6 -14
-49 -21 -95 -7 -53 -23 -110 -44 -154 -29 -64 -32 -81 -38 -205 -3 -74 -14
-191 -24 -260 l-18 -125 -32 -9 c-26 -7 -37 -6 -49 6 -14 15 -14 23 2 95 9 43
21 137 26 208 6 72 16 150 24 175 7 25 17 81 20 125 4 44 13 95 21 114 16 38
19 196 5 233 -5 13 -18 33 -29 44 -12 12 -19 24 -16 27 3 2 -14 7 -37 11 -23
4 -51 13 -62 21 -16 11 -54 15 -157 15 -129 0 -138 -1 -157 -22z m4442 -380
c-3 -13 -12 -39 -19 -58 -7 -19 -24 -68 -37 -109 -13 -40 -34 -87 -46 -104
-12 -16 -20 -34 -17 -39 15 -24 -35 -103 -54 -84 -10 11 9 74 28 91 13 12 17
25 14 44 -10 47 92 281 122 281 11 0 14 -6 9 -22z m-4039 -1055 c10 -38 -5
-218 -20 -255 -11 -25 -14 -96 -15 -278 -2 -407 -13 -784 -24 -798 -6 -7 -14
-36 -18 -65 -9 -54 -26 -75 -84 -101 -16 -7 -55 -36 -85 -65 -65 -60 -97 -73
-118 -45 -20 27 -11 394 11 427 10 17 15 74 20 232 3 116 10 222 16 237 6 15
17 67 25 115 19 111 40 192 96 378 10 33 21 78 25 100 12 68 39 108 98 138 37
19 66 11 73 -20z m3064 -756 c0 -36 -47 -143 -109 -247 -38 -63 -109 -196
-159 -295 -50 -99 -102 -196 -115 -216 -22 -32 -81 -139 -128 -231 -10 -20
-23 -40 -29 -43 -15 -9 -12 37 4 60 7 11 16 40 19 65 3 25 36 135 73 245 73
220 147 377 246 525 54 80 71 98 117 122 59 31 81 35 81 15z m2497 -593 c-3
-3 -12 -4 -19 -1 -8 3 -5 6 6 6 11 1 17 -2 13 -5z"/>
                                </g>
                            </svg>
                        </div>
                    </div>
                    <div class="cart-screen_cart__JV4JN">
                        <div v-if="totalCount > 0"> <!-- если есть товары -->
                            <template v-for="(item, index) in cartItems" :key="item.id">
                                <div v-if="index === 0 && !item.preorder"
                                     class="cart-orders">
                                    Заказы
                                </div>
                                <div v-if="item.preorder && (index === 0 || !cartItems[index - 1].preorder)"
                                     class="cart-orders cart-preorder" style="flex-direction:column">
                                    <div>Предзаказы</div>
                                </div>
                                <div class="cart-item_cart_item__CrVBq">
                                    <div @click="productLink(item.product.id)"
                                         class="cart-item_image__s8eu5">
                                        <img
                                                :src="item.product.image.url"
                                                :alt="item.product.name"
                                                @error="handleImageError"
                                        >
                                    </div>
                                    <div class="cart-item_body__1FLl_">
                                        <div class="cart-item_name_and_checkbox__IL5UT">
                                            <div class="cart-item_name__9l_04">{{ item.product.name }}
                                            </div>
                                        </div>
                                        <div>
                                            <div><span>Артикул: {{ item.product.id }}</span></div>
                                        </div>
                                        <div class="cart-item_price__HIS5_">
                                                        <span :class="{'discount-active': item.product?.rests[0]?.shop_active_discount !== 'no_sale' &&
                                                        Number(item.product?.rests[0]?.shop_active_discount === 'extra' ? item.product?.discount_group?.extra_value : item.product?.discount_group?.regular_value) !== 1}">
                                                            {{ item.price * 1 }}&nbsp;₽
                                                        </span>
                                            <span :style="{ display: (item.product?.rests[0]?.shop_active_discount === 'regular' && Number(item.product.discount_group.regular_value) !== 1) ? '' : 'none' }">
                                                            {{ Math.round(item.price * item.product.discount_group.regular_value) }}&nbsp;₽
                                                        </span>
                                            <span :style="{ display: (item.product?.rests[0]?.shop_active_discount === 'extra' && Number(item.product.discount_group.extra_value) !== 1) ? '' : 'none' }">
                                                            {{ Math.round(item.price * item.product.discount_group.extra_value) }}&nbsp;₽
                                                        </span>
                                        </div>
                                        <div class="cart-item_actions__OE4gV">
                                            <div class="cart-item_actions_left__rsL9k">
                                                <button
                                                        @click="toggleTrack(item.product)"
                                                        class="favorite-button_favorite_button__a_ct8 hero-info_heart__hUlWV"
                                                        :class="{'favorite-button_on__2qN_y': item.product?.is_tracked}"
                                                        :aria-label="item.product?.is_tracked ? 'Лайк' : 'Снять лайк'"
                                                >
                                                    <svg xmlns="http://www.w3.org/2000/svg" width="22"
                                                         height="22" viewBox="0 0 24 24" fill="none"
                                                         stroke="currentColor" stroke-width="1"
                                                         stroke-linecap="round" stroke-linejoin="round"
                                                         class="tabler-icon tabler-icon-heart ">
                                                        <path d="M19.5 12.572l-7.5 7.428l-7.5 -7.428a5 5 0 1 1 7.5 -6.566a5 5 0 1 1 7.5 6.572"></path>
                                                    </svg>
                                                </button>
                                                <button @click="deleteCart(item)"
                                                        class="cart-item_remove_button__6vfvx">
                                                    <svg xmlns="http://www.w3.org/2000/svg" width="24"
                                                         height="24" viewBox="0 0 24 24" fill="none"
                                                         stroke="currentColor" stroke-width="1"
                                                         stroke-linecap="round" stroke-linejoin="round"
                                                         class="tabler-icon tabler-icon-x ">
                                                        <path d="M18 6l-12 12"></path>
                                                        <path d="M6 6l12 12"></path>
                                                    </svg>
                                                </button>
                                            </div>
                                            <div data-v-5bff6dd4="" class="cart-item_button__MUAX2">
                                                <div @click.stop="changeCount(item, -1)"
                                                     class="cart-item_change_count__IejK4"
                                                     :class="{ 'hide': (item.amount || 0) <= 0 }">
                                                    -
                                                </div>
                                                {{ item.amount || 0 }}
                                                <div @click.stop="changeCount(item, 1)"
                                                     class="cart-item_change_count__IejK4"
                                                     :class="{ 'hide': (item.amount || 0) >= (item.product?.rests[0].amount || 0) && !item.preorder }">
                                                    +
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </template>
                            <div id="observer-point" ref="observerPoint" style="height: 10px;"></div>
                            <div class="product-actions_product_actions__ng4Ma product-screen_actions__EaCEp">
                                <div class="product-actions_buttons__9Rs_R">
                                    <button @click="orderLink()" class="button_button__AjjDz"
                                            href="">
                                        <span>Оформить: {{ finalTotal.toLocaleString() }}&nbsp;₽</span>
                                    </button>
                                </div>
                            </div>
                        </div>


                        <div v-else class="cart-screen_empty__mDtgG"> <!-- если пусто -->
                            <div class="cart-screen_icon__QKvZs">
                                <div style="width:150px;height:100%;overflow:hidden;margin:0 auto;outline:none"
                                     title="" role="button" aria-label="animation" tabindex="0">
                                    <svg xmlns="http://www.w3.org/2000/svg"
                                         xmlns:xlink="http://www.w3.org/1999/xlink"
                                         viewBox="0 0 512 512"
                                         width="512" height="512" preserveAspectRatio="xMidYMid slice"
                                         style="width: 100%; height: 100%; transform: translate3d(0px, 0px, 0px); content-visibility: visible;">
                                        <g clip-path="url(#__lottie_element_2)">
                                            <g clip-path="url(#__lottie_element_74)"
                                               transform="matrix(1,0,0,1,0,0)" opacity="1"
                                               style="display: none;">
                                                <g clip-path="url(#__lottie_element_137)"
                                                   transform="matrix(1,0,0,1,12,9)" opacity="1"
                                                   style="display: none;">
                                                    <g transform="matrix(1.5022599697113037,0,0,1.5022599697113037,-7.507354736328125,334.35150146484375)"
                                                       opacity="1" style="display: none;">
                                                        <g opacity="1"
                                                           transform="matrix(1,0,0,1,176.4949951171875,64.81999969482422)">
                                                            <path stroke-linecap="round"
                                                                  stroke-linejoin="round"
                                                                  fill-opacity="0"
                                                                  stroke="rgb(3,180,255)"
                                                                  stroke-opacity="1"
                                                                  stroke-width="0"
                                                                  d=" M151.4949951171875,0 C151.4949951171875,21.992000579833984 83.66899871826172,39.81999969482422 0.0010000000474974513,39.81999969482422 C-83.66699981689453,39.81999969482422 -151.49400329589844,21.992000579833984 -151.49400329589844,0 C-151.49400329589844,-21.992000579833984 -83.66699981689453,-39.81999969482422 0.0010000000474974513,-39.81999969482422 C83.66899871826172,-39.81999969482422 151.4949951171875,-21.992000579833984 151.4949951171875,0z"></path>
                                                        </g>
                                                    </g>
                                                </g>
                                                <g clip-path="url(#__lottie_element_130)"
                                                   style="display: block;"
                                                   transform="matrix(1,0,0,1,12,9)"
                                                   opacity="1">
                                                    <g style="display: block;"
                                                       transform="matrix(1.5022599697113037,0,0,1.5022599697113037,-7.507354736328125,334.35150146484375)"
                                                       opacity="1">
                                                        <g opacity="1"
                                                           transform="matrix(1,0,0,1,176.4949951171875,64.81999969482422)">
                                                            <path stroke-linecap="round"
                                                                  stroke-linejoin="round"
                                                                  fill-opacity="0"
                                                                  stroke="rgb(3,180,255)"
                                                                  stroke-opacity="1"
                                                                  stroke-width="0"
                                                                  d=" M151.4949951171875,0 C151.4949951171875,21.992000579833984 83.66899871826172,39.81999969482422 0.0010000000474974513,39.81999969482422 C-83.66699981689453,39.81999969482422 -151.49400329589844,21.992000579833984 -151.49400329589844,0 C-151.49400329589844,-21.992000579833984 -83.66699981689453,-39.81999969482422 0.0010000000474974513,-39.81999969482422 C83.66899871826172,-39.81999969482422 151.4949951171875,-21.992000579833984 151.4949951171875,0z"></path>
                                                        </g>
                                                    </g>
                                                </g>
                                                <g transform="matrix(0.9994161128997803,0.03416689485311508,-0.03416689485311508,0.9994161128997803,61.98320007324219,207.96136474609375)"
                                                   opacity="1" style="display: block;">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,211.84800720214844,148.99600219726562)">
                                                        <path fill="rgb(255,212,39)" fill-opacity="1"
                                                              d=" M-148.48399353027344,73.28600311279297 C-162.2740020751953,57.900001525878906 -168.33999633789062,43.196998596191406 -169.42999267578125,22.95599937438965 C-174.16799926757812,-65.0469970703125 -96.2030029296875,-111.80000305175781 0.8320000171661377,-111.80000305175781 C105.0459976196289,-111.80000305175781 176.1719970703125,-91.49700164794922 169.9239959716797,20.909000396728516 C168.1009979248047,53.70899963378906 158.4199981689453,71.88200378417969 110.90699768066406,88.61399841308594 C60.71200180053711,106.29100036621094 -103.03700256347656,123.99600219726562 -148.48399353027344,73.28600311279297z"></path>
                                                        <path stroke-linecap="butt"
                                                              stroke-linejoin="miter"
                                                              fill-opacity="0" stroke-miterlimit="10"
                                                              stroke="rgb(249,143,22)"
                                                              stroke-opacity="1"
                                                              stroke-width="10"
                                                              d=" M-148.48399353027344,73.28600311279297 C-162.2740020751953,57.900001525878906 -168.33999633789062,43.196998596191406 -169.42999267578125,22.95599937438965 C-174.16799926757812,-65.0469970703125 -96.2030029296875,-111.80000305175781 0.8320000171661377,-111.80000305175781 C105.0459976196289,-111.80000305175781 176.1719970703125,-91.49700164794922 169.9239959716797,20.909000396728516 C168.1009979248047,53.70899963378906 158.4199981689453,71.88200378417969 110.90699768066406,88.61399841308594 C60.71200180053711,106.29100036621094 -103.03700256347656,123.99600219726562 -148.48399353027344,73.28600311279297z"></path>
                                                    </g>
                                                </g>
                                                <g transform="matrix(0.9994161128997803,0.03416689485311508,-0.03416689485311508,0.9994161128997803,87.93304443359375,279.61883544921875)"
                                                   opacity="1" style="display: block;">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,342.5580139160156,59.694000244140625)">
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(251,237,32)"
                                                              stroke-opacity="1" stroke-width="10"
                                                              d=" M-17.04599952697754,-28.517000198364258 C2.5980000495910645,12.35200023651123 -2.7950000762939453,35.3390007019043 -8.9350004196167,51.56800079345703"></path>
                                                    </g>
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,33.013999938964844,46.38600158691406)">
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(255,255,255)"
                                                              stroke-opacity="1" stroke-width="10"
                                                              d=" M12.67199993133545,-9.852999687194824 C-1.2089999914169312,9.888999938964844 -4.255000114440918,21.785999298095703 -2.5510001182556152,37.94499969482422"></path>
                                                    </g>
                                                </g>
                                                <g transform="matrix(0.9994160532951355,0.03416689112782478,-0.03416689112782478,0.9994160532951355,82.82470703125,300.15057373046875)"
                                                   opacity="1" style="display: block;">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,57.97800064086914,81.80899810791016)">
                                                        <path fill="rgb(255,212,39)" fill-opacity="1"
                                                              d=" M32.97800064086914,13.595999717712402 C19.447999954223633,41.91999816894531 -6.072000026702881,56.808998107910156 -18.413000106811523,47.61800003051758 C-30.486000061035156,38.62799835205078 -32.97700119018555,-19.027000427246094 17.448999404907227,-56.808998107910156"></path>
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(249,143,22)"
                                                              stroke-opacity="1" stroke-width="10"
                                                              d=" M32.97800064086914,13.595999717712402 C19.447999954223633,41.91999816894531 -6.072000026702881,56.808998107910156 -18.413000106811523,47.61800003051758 C-30.486000061035156,38.62799835205078 -32.97700119018555,-19.027000427246094 17.448999404907227,-56.808998107910156"></path>
                                                    </g>
                                                </g>
                                                <g transform="matrix(0.9994160532951355,0.03416689112782478,-0.03416689112782478,0.9994160532951355,101.0001220703125,322.10736083984375)"
                                                   opacity="1" style="display: block;">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,39.57600021362305,60.46099853515625)">
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(255,255,255)"
                                                              stroke-opacity="1" stroke-width="10"
                                                              d=" M-12.062000274658203,34.36800003051758 C-18.763999938964844,8.270999908447266 -3.8010001182556152,-20.454999923706055 22.093000411987305,-45.11800003051758"></path>
                                                    </g>
                                                </g>
                                                <g transform="matrix(0.9994160532951355,0.03416689112782478,-0.03416689112782478,0.9994160532951355,341.49420166015625,302.4820251464844)"
                                                   opacity="1" style="display: block;">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,57.97700119018555,82.88200378417969)">
                                                        <path fill="rgb(255,212,39)" fill-opacity="1"
                                                              d=" M-32.97700119018555,12.52299976348877 C-19.44700050354004,40.84700012207031 8.034000396728516,57.88199996948242 19.756000518798828,48.439998626708984 C29.301000595092773,40.75199890136719 32.084999084472656,-0.4950000047683716 4.88700008392334,-35.92399978637695"></path>
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(249,143,22)"
                                                              stroke-opacity="1" stroke-width="10"
                                                              d=" M-32.97700119018555,12.52299976348877 C-19.44700050354004,40.84700012207031 8.034000396728516,57.88199996948242 19.756000518798828,48.439998626708984 C29.301000595092773,40.75199890136719 32.084999084472656,-0.4950000047683716 4.88700008392334,-35.92399978637695"></path>
                                                    </g>
                                                </g>
                                                <g transform="matrix(0.9994160532951355,0.03416689112782478,-0.03416689112782478,0.9994160532951355,368.84429931640625,332.74114990234375)"
                                                   opacity="1" style="display: block;">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,37.183998107910156,57.85100173950195)">
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(251,237,32)"
                                                              stroke-opacity="1" stroke-width="10"
                                                              d=" M2.1760001182556152,32.85100173950195 C5.571000099182129,25.211999893188477 11.862000465393066,9.295999526977539 -10.434000015258789,-29.83300018310547"></path>
                                                    </g>
                                                </g>
                                                <g transform="matrix(0.9994161128997803,0.03416689485311508,-0.03416689485311508,0.9994161128997803,76.92839050292969,9.598175048828125)"
                                                   opacity="1" style="display: block;">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,198.8719940185547,158.7830047607422)">
                                                        <path fill="rgb(255,212,39)" fill-opacity="1"
                                                              d=" M-127.66699981689453,133.7830047607422 C-162.63900756835938,114.08599853515625 -173.8719940185547,72.41500091552734 -173.8719940185547,36.566001892089844 C-173.8719940185547,-49.277000427246094 -96.02799987792969,-133.7830047607422 -0.0010000000474974513,-133.7830047607422 C96.0260009765625,-133.7830047607422 173.8719940185547,-49.277000427246094 173.8719940185547,36.566001892089844 C173.8719940185547,72.78299713134766 160.01600646972656,103.4520034790039 136.78500366210938,126.80799865722656"></path>
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="miter"
                                                              fill-opacity="0" stroke-miterlimit="10"
                                                              stroke="rgb(249,143,22)"
                                                              stroke-opacity="1"
                                                              stroke-width="10"
                                                              d=" M-127.66699981689453,133.7830047607422 C-162.63900756835938,114.08599853515625 -173.8719940185547,72.41500091552734 -173.8719940185547,36.566001892089844 C-173.8719940185547,-49.277000427246094 -96.02799987792969,-133.7830047607422 -0.0010000000474974513,-133.7830047607422 C96.0260009765625,-133.7830047607422 173.8719940185547,-49.277000427246094 173.8719940185547,36.566001892089844 C173.8719940185547,72.78299713134766 160.01600646972656,103.4520034790039 136.78500366210938,126.80799865722656"></path>
                                                    </g>
                                                </g>
                                                <g transform="matrix(0.9994161128997803,0.03416689485311508,-0.03416689485311508,0.9994161128997803,104.83171081542969,39.890228271484375)"
                                                   opacity="1" style="display: block;">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,102.4729995727539,69.81999969482422)">
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(255,255,255)"
                                                              stroke-opacity="1" stroke-width="10"
                                                              d=" M-63.88399887084961,37.06399917602539 C-51.625,12.628999710083008 -31.757999420166016,-8.925000190734863 -7.127999782562256,-23.780000686645508 C14.661999702453613,-36.91999816894531 40.18000030517578,-44.81700134277344 67.45899963378906,-44.81999969482422"></path>
                                                    </g>
                                                </g>
                                                <g transform="matrix(0.9994161128997803,0.03416689485311508,-0.03416689485311508,0.9994161128997803,346.6203918457031,86.84982299804688)"
                                                   opacity="1" style="display: block;">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,48.32400131225586,110.46199798583984)">
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(251,237,32)"
                                                              stroke-opacity="1" stroke-width="10"
                                                              d=" M-16.388999938964844,-78.77100372314453 C8.22599983215332,-53.47600173950195 23.322999954223633,-20.42300033569336 23.322999954223633,12.880000114440918 C23.322999954223633,42.00299835205078 11.777999877929688,66.66500091552734 -7.579999923706055,85.4489974975586"></path>
                                                    </g>
                                                </g>
                                                <g transform="matrix(1.0588505268096924,0.05912478268146515,-0.05190492421388626,0.9295519590377808,136.61312866210938,181.6582794189453)"
                                                   opacity="1" style="display: block;">
                                                    <path stroke-linecap="butt" stroke-linejoin="miter"
                                                          fill-opacity="0" stroke-miterlimit="4"
                                                          stroke="rgb(0,0,0)" stroke-opacity="1"
                                                          stroke-width="0"
                                                          d=" M55.84,41.01 C51.15,57.2 35.95,67.03 21.9,62.96 C7.84,58.89 0.25,42.46 4.94,26.27 C9.63,10.08 24.82,0.25 38.88,4.32 C52.93,8.39 60.53,24.82 55.84,41.01z"></path>
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,30.38800048828125,33.638999938964844)">
                                                        <path fill="rgb(0,0,0)" fill-opacity="1"
                                                              d=" M25.448999404907227,7.369999885559082 C20.760000228881836,23.562000274658203 5.564000129699707,33.388999938964844 -8.491000175476074,29.31800079345703 C-22.54599952697754,25.24799919128418 -30.13800048828125,8.821999549865723 -25.448999404907227,-7.369999885559082 C-20.759000778198242,-23.562000274658203 -5.564000129699707,-33.388999938964844 8.491000175476074,-29.319000244140625 C22.54599952697754,-25.24799919128418 30.13800048828125,-8.821999549865723 25.448999404907227,7.369999885559082z"></path>
                                                    </g>
                                                </g>
                                                <g transform="matrix(0.28980737924575806,0.01618245244026184,-0.01420637872070074,0.25441837310791016,158.71466064453125,205.6740264892578)"
                                                   opacity="1" style="display: block;">
                                                    <g opacity="1"
                                                       transform="matrix(0.7515299916267395,0,0,0.7515299916267395,15.770000457763672,-20.802000045776367)">
                                                        <path fill="rgb(255,255,255)" fill-opacity="1"
                                                              d=" M25.448999404907227,7.369999885559082 C20.760000228881836,23.562000274658203 5.564000129699707,33.388999938964844 -8.491000175476074,29.31800079345703 C-22.54599952697754,25.24799919128418 -30.13800048828125,8.821999549865723 -25.448999404907227,-7.369999885559082 C-20.759000778198242,-23.562000274658203 -5.564000129699707,-33.388999938964844 8.491000175476074,-29.319000244140625 C22.54599952697754,-25.24799919128418 30.13800048828125,-8.821999549865723 25.448999404907227,7.369999885559082z"></path>
                                                    </g>
                                                </g>
                                                <g transform="matrix(1.0588505268096924,0.05912478268146515,-0.05190492421388626,0.9295519590377808,340.62237548828125,193.3258819580078)"
                                                   opacity="1" style="display: block;">
                                                    <path stroke-linecap="butt" stroke-linejoin="miter"
                                                          fill-opacity="0" stroke-miterlimit="4"
                                                          stroke="rgb(0,0,0)" stroke-opacity="1"
                                                          stroke-width="0"
                                                          d=" M53.38,30.01 C54.05,46.7 42.83,60.7 28.34,61.27 C13.85,61.85 1.57,48.78 0.91,32.09 C0.25,15.4 11.46,1.4 25.95,0.82 C40.44,0.25 52.72,13.32 53.38,30.01z"></path>
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,27.14699935913086,31.049999237060547)">
                                                        <path fill="rgb(0,0,0)" fill-opacity="1"
                                                              d=" M26.23699951171875,-1.0399999618530273 C26.898000717163086,15.652999877929688 15.687999725341797,29.650999069213867 1.1979999542236328,30.225000381469727 C-13.291999816894531,30.798999786376953 -25.575000762939453,17.73200035095215 -26.236000061035156,1.0390000343322754 C-26.898000717163086,-15.654000282287598 -15.687999725341797,-29.650999069213867 -1.1979999542236328,-30.225000381469727 C13.291999816894531,-30.798999786376953 25.576000213623047,-17.732999801635742 26.23699951171875,-1.0399999618530273z"></path>
                                                    </g>
                                                </g>
                                                <g transform="matrix(0.19638501107692719,0.01096587348729372,-0.00962680671364069,0.17240400612354279,362.72296142578125,218.1427001953125)"
                                                   opacity="1" style="display: block;">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,-23.78700065612793,-45.98099899291992)">
                                                        <path fill="rgb(255,255,255)" fill-opacity="1"
                                                              d=" M26.23699951171875,-1.0399999618530273 C26.898000717163086,15.652999877929688 15.687999725341797,29.650999069213867 1.1979999542236328,30.225000381469727 C-13.291999816894531,30.798999786376953 -25.575000762939453,17.73200035095215 -26.236000061035156,1.0390000343322754 C-26.898000717163086,-15.654000282287598 -15.687999725341797,-29.650999069213867 -1.1979999542236328,-30.225000381469727 C13.291999816894531,-30.798999786376953 25.576000213623047,-17.732999801635742 26.23699951171875,-1.0399999618530273z"></path>
                                                    </g>
                                                </g>
                                                <g transform="matrix(1.0588505268096924,0.05912478268146515,-0.05190492421388626,0.9295519590377808,167.2076873779297,185.77981567382812)"
                                                   opacity="1" style="display: block;">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,97.20700073242188,71.1989974975586)">
                                                        <path fill="rgb(255,92,30)" fill-opacity="1"
                                                              d=" M41.696998596191406,36.9739990234375 C29.65399932861328,38.28499984741211 19.33300018310547,36.733001708984375 5.3429999351501465,38.40299987792969 C-9.744999885559082,40.20500183105469 -23.506999969482422,41.44499969482422 -33.36899948120117,43.70399856567383 C-53.76100158691406,48.374000549316406 -50.29399871826172,21.06999969482422 -36.617000579833984,12.008999824523926 C-13.786999702453613,-3.115999937057495 -27.0049991607666,-48.96500015258789 -3.941999912261963,-51.520999908447266 C23.211000442504883,-54.53200149536133 17.384000778198242,-6.745999813079834 30.6200008392334,1.100000023841858 C55.130001068115234,15.628999710083008 54.691001892089844,35.558998107910156 41.696998596191406,36.9739990234375z"></path>
                                                        <path stroke-linecap="butt"
                                                              stroke-linejoin="miter"
                                                              fill-opacity="0" stroke-miterlimit="10"
                                                              stroke="rgb(207,53,2)" stroke-opacity="1"
                                                              stroke-width="6.667"
                                                              d=" M41.696998596191406,36.9739990234375 C29.65399932861328,38.28499984741211 19.33300018310547,36.733001708984375 5.3429999351501465,38.40299987792969 C-9.744999885559082,40.20500183105469 -23.506999969482422,41.44499969482422 -33.36899948120117,43.70399856567383 C-53.76100158691406,48.374000549316406 -50.29399871826172,21.06999969482422 -36.617000579833984,12.008999824523926 C-13.786999702453613,-3.115999937057495 -27.0049991607666,-48.96500015258789 -3.941999912261963,-51.520999908447266 C23.211000442504883,-54.53200149536133 17.384000778198242,-6.745999813079834 30.6200008392334,1.100000023841858 C55.130001068115234,15.628999710083008 54.691001892089844,35.558998107910156 41.696998596191406,36.9739990234375z"></path>
                                                    </g>
                                                </g>
                                                <g transform="matrix(1.04714035987854,0.17297616600990295,-0.18167060613632202,0.9176068902015686,189.04067993164062,183.98095703125)"
                                                   opacity="1" style="display: block;">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,33.59000015258789,24.059999465942383)">
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(255,180,132)"
                                                              stroke-opacity="1" stroke-width="8"
                                                              d=" M33.4010009765625,54.904998779296875 C40.18899917602539,45.810001373291016 45.720001220703125,29.763999938964844 42.35300064086914,1.4539999961853027"></path>
                                                    </g>
                                                </g>
                                                <g transform="matrix(1.0588505268096924,0.05912478268146515,-0.05190492421388626,0.9295519590377808,201.84579467773438,233.84320068359375)"
                                                   opacity="1" style="display: block;">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,64.81900024414062,32.64699935913086)">
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(125,9,9)"
                                                              stroke-opacity="1" stroke-width="8"
                                                              d=" M-31.94499969482422,19.31999969482422 C-8.442000389099121,16.590999603271484 12.746999740600586,15.402000427246094 34.715999603271484,14.5600004196167"></path>
                                                    </g>
                                                </g>
                                            </g>
                                            <g clip-path="url(#__lottie_element_4)"
                                               style="display: block;"
                                               transform="matrix(1,0,0,1,0,0)" opacity="1">
                                                <g clip-path="url(#__lottie_element_67)"
                                                   style="display: block;"
                                                   transform="matrix(1,0,0,1,12,9)"
                                                   opacity="1">
                                                    <g style="display: block;"
                                                       transform="matrix(1.1153854131698608,0,0,1.1153854131698608,60.77406311035156,359.4287109375)"
                                                       opacity="1">
                                                        <g opacity="1"
                                                           transform="matrix(1,0,0,1,176.4949951171875,64.81999969482422)">
                                                            <path stroke-linecap="round"
                                                                  stroke-linejoin="round"
                                                                  fill-opacity="0"
                                                                  stroke="rgb(3,180,255)"
                                                                  stroke-opacity="1"
                                                                  stroke-width="3.4588179857497163"
                                                                  d=" M151.4949951171875,0 C151.4949951171875,21.992000579833984 83.66899871826172,39.81999969482422 0.0010000000474974513,39.81999969482422 C-83.66699981689453,39.81999969482422 -151.49400329589844,21.992000579833984 -151.49400329589844,0 C-151.49400329589844,-21.992000579833984 -83.66699981689453,-39.81999969482422 0.0010000000474974513,-39.81999969482422 C83.66899871826172,-39.81999969482422 151.4949951171875,-21.992000579833984 151.4949951171875,0z"></path>
                                                        </g>
                                                    </g>
                                                </g>
                                                <g clip-path="url(#__lottie_element_60)"
                                                   style="display: none;">
                                                    <g style="display: none;">
                                                        <g>
                                                            <path stroke-linecap="round"
                                                                  stroke-linejoin="round"
                                                                  fill-opacity="0"></path>
                                                        </g>
                                                    </g>
                                                </g>
                                                <g style="display: block;"
                                                   transform="matrix(0.9994161128997803,0.03416689485311508,-0.03416689485311508,0.9994161128997803,61.98320007324219,207.96136474609375)"
                                                   opacity="1">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,211.84800720214844,148.99600219726562)">
                                                        <path fill="rgb(255,212,39)" fill-opacity="1"
                                                              d=" M-148.48399353027344,73.28600311279297 C-162.2740020751953,57.900001525878906 -166.84800720214844,40.064998626708984 -164.63499450683594,19.916000366210938 C-154.0050048828125,-76.89700317382812 -97.05400085449219,-123.99600219726562 -0.01899999938905239,-123.99600219726562 C104.19499969482422,-123.99600219726562 166.84800720214844,-86.6729965209961 166.84800720214844,17.10700035095215 C166.84800720214844,49.95800018310547 158.42100524902344,71.88200378417969 110.90799713134766,88.61399841308594 C60.7130012512207,106.29100036621094 -103.03700256347656,123.99600219726562 -148.48399353027344,73.28600311279297z"></path>
                                                        <path stroke-linecap="butt"
                                                              stroke-linejoin="miter"
                                                              fill-opacity="0" stroke-miterlimit="10"
                                                              stroke="rgb(249,143,22)"
                                                              stroke-opacity="1"
                                                              stroke-width="10"
                                                              d=" M-148.48399353027344,73.28600311279297 C-162.2740020751953,57.900001525878906 -166.84800720214844,40.064998626708984 -164.63499450683594,19.916000366210938 C-154.0050048828125,-76.89700317382812 -97.05400085449219,-123.99600219726562 -0.01899999938905239,-123.99600219726562 C104.19499969482422,-123.99600219726562 166.84800720214844,-86.6729965209961 166.84800720214844,17.10700035095215 C166.84800720214844,49.95800018310547 158.42100524902344,71.88200378417969 110.90799713134766,88.61399841308594 C60.7130012512207,106.29100036621094 -103.03700256347656,123.99600219726562 -148.48399353027344,73.28600311279297z"></path>
                                                    </g>
                                                </g>
                                                <g style="display: block;"
                                                   transform="matrix(0.9994161128997803,0.03416689485311508,-0.03416689485311508,0.9994161128997803,87.93304443359375,279.61883544921875)"
                                                   opacity="1">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,342.5580139160156,59.694000244140625)">
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(251,237,32)"
                                                              stroke-opacity="1" stroke-width="10"
                                                              d=" M-8.102999687194824,28.209999084472656 C-5.85699987411499,54.694000244140625 -4.571000099182129,79.2249984741211 -55.90700149536133,95.08699798583984"></path>
                                                    </g>
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,33.013999938964844,46.38600158691406)">
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(255,255,255)"
                                                              stroke-opacity="1" stroke-width="10"
                                                              d=" M0.8320000171661377,53.5890007019043 C-1.840999960899353,64.80699920654297 -0.8809999823570251,83.75599670410156 15.973999977111816,98.44999694824219"></path>
                                                    </g>
                                                </g>
                                                <g style="display: block;"
                                                   transform="matrix(-0.07711925357580185,0.9970217943191528,-0.9970217943191528,-0.07711925357580185,189.81234741210938,249.4874725341797)"
                                                   opacity="1">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,57.97800064086914,81.80899810791016)">
                                                        <path fill="rgb(255,212,39)" fill-opacity="1"
                                                              d=" M60.257999420166016,-13.585000038146973 C18.37700080871582,3.48799991607666 31.726999282836914,59.17100143432617 1.4229999780654907,65.64600372314453 C-29.417999267578125,72.23600006103516 -67.26000213623047,5.479000091552734 8.246999740600586,-52.58700180053711"></path>
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(249,143,22)"
                                                              stroke-opacity="1" stroke-width="10"
                                                              d=" M60.257999420166016,-13.585000038146973 C18.37700080871582,3.48799991607666 31.726999282836914,59.17100143432617 1.4229999780654907,65.64600372314453 C-29.417999267578125,72.23600006103516 -67.26000213623047,5.479000091552734 8.246999740600586,-52.58700180053711"></path>
                                                    </g>
                                                </g>
                                                <g style="display: block;"
                                                   transform="matrix(-0.07711925357580185,0.9970217943191528,-0.9970217943191528,-0.07711925357580185,167.09414672851562,266.70172119140625)"
                                                   opacity="1">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,39.57600021362305,60.46099853515625)">
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(255,255,255)"
                                                              stroke-opacity="1" stroke-width="10"
                                                              d=" M-6.065999984741211,51.957000732421875 C-36.0629997253418,35.319000244140625 -21.531999588012695,-7.610000133514404 4.515999794006348,-32.64899826049805"></path>
                                                    </g>
                                                </g>
                                                <g style="display: block;"
                                                   transform="matrix(-0.2415323555469513,-0.9703927636146545,0.9703927636146545,-0.2415323555469513,348.4349060058594,359.02471923828125)"
                                                   opacity="1">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,57.97700119018555,82.88200378417969)">
                                                        <path fill="rgb(255,212,39)" fill-opacity="1"
                                                              d=" M-50.946998596191406,-4.448999881744385 C0.04899999871850014,12.557999610900879 -15.902999877929688,73.81700134277344 8.329000473022461,73.40799713134766 C40.1879997253418,72.87000274658203 51.487998962402344,13.829000473022461 17.27199935913086,-30.06999969482422"></path>
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(249,143,22)"
                                                              stroke-opacity="1" stroke-width="10"
                                                              d=" M-50.946998596191406,-4.448999881744385 C0.04899999871850014,12.557999610900879 -15.902999877929688,73.81700134277344 8.329000473022461,73.40799713134766 C40.1879997253418,72.87000274658203 51.487998962402344,13.829000473022461 17.27199935913086,-30.06999969482422"></path>
                                                    </g>
                                                </g>
                                                <g style="display: block;"
                                                   transform="matrix(-0.2415323555469513,-0.9703927636146545,0.9703927636146545,-0.2415323555469513,370.02239990234375,324.41802978515625)"
                                                   opacity="1">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,37.183998107910156,57.85100173950195)">
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(251,237,32)"
                                                              stroke-opacity="1" stroke-width="10"
                                                              d=" M8.777999877929688,53.064998626708984 C22.225000381469727,27.374000549316406 19.93400001525879,7.171999931335449 -9.428999900817871,-29.461999893188477"></path>
                                                    </g>
                                                </g>
                                                <g style="display: block;"
                                                   transform="matrix(0.998259425163269,-0.05897533893585205,0.05897533893585205,0.998259425163269,44.71356201171875,38.593017578125)"
                                                   opacity="1">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,198.8719940185547,158.7830047607422)">
                                                        <path fill="rgb(255,212,39)" fill-opacity="1"
                                                              d=" M-127.66699981689453,133.7830047607422 C-162.63900756835938,114.08599853515625 -173.8719940185547,72.41500091552734 -173.8719940185547,36.566001892089844 C-173.8719940185547,-49.277000427246094 -96.02799987792969,-133.7830047607422 -0.0010000000474974513,-133.7830047607422 C96.0260009765625,-133.7830047607422 173.8719940185547,-49.277000427246094 173.8719940185547,36.566001892089844 C173.8719940185547,72.78299713134766 160.01600646972656,103.4520034790039 136.78500366210938,126.80799865722656"></path>
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="miter"
                                                              fill-opacity="0" stroke-miterlimit="10"
                                                              stroke="rgb(249,143,22)"
                                                              stroke-opacity="1"
                                                              stroke-width="10"
                                                              d=" M-127.66699981689453,133.7830047607422 C-162.63900756835938,114.08599853515625 -173.8719940185547,72.41500091552734 -173.8719940185547,36.566001892089844 C-173.8719940185547,-49.277000427246094 -96.02799987792969,-133.7830047607422 -0.0010000000474974513,-133.7830047607422 C96.0260009765625,-133.7830047607422 173.8719940185547,-49.277000427246094 173.8719940185547,36.566001892089844 C173.8719940185547,72.78299713134766 160.01600646972656,103.4520034790039 136.78500366210938,126.80799865722656"></path>
                                                    </g>
                                                </g>
                                                <g style="display: block;"
                                                   transform="matrix(0.998259425163269,-0.05897533893585205,0.05897533893585205,0.998259425163269,75.31443786621094,66.15728759765625)"
                                                   opacity="1">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,102.4729995727539,69.81999969482422)">
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(255,255,255)"
                                                              stroke-opacity="1" stroke-width="10"
                                                              d=" M-64.1969985961914,37.69300079345703 C-51.96500015258789,12.99899959564209 -31.9689998626709,-8.79800033569336 -7.127999782562256,-23.780000686645508 C14.475000381469727,-36.80699920654297 39.742000579833984,-44.680999755859375 66.75599670410156,-44.81800079345703"></path>
                                                    </g>
                                                </g>
                                                <g style="display: block;"
                                                   transform="matrix(0.998259425163269,-0.05897533893585205,0.05897533893585205,0.998259425163269,320.42364501953125,90.41513061523438)"
                                                   opacity="1">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,48.32400131225586,110.46199798583984)">
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(251,237,32)"
                                                              stroke-opacity="1" stroke-width="10"
                                                              d=" M-16.94300079345703,-79.33699798583984 C8,-53.970001220703125 23.322999954223633,-20.672000885009766 23.322999954223633,12.880000114440918 C23.322999954223633,41.71799850463867 12.003000259399414,66.18199920654297 -7.013999938964844,84.8949966430664"></path>
                                                    </g>
                                                </g>
                                                <g style="display: block;"
                                                   transform="matrix(0.6320319175720215,-0.07357577234506607,0.06459126621484756,0.554853081703186,116.8563232421875,211.3378143310547)"
                                                   opacity="1">
                                                    <path stroke-linecap="butt" stroke-linejoin="miter"
                                                          fill-opacity="0" stroke-miterlimit="4"
                                                          stroke="rgb(0,0,0)" stroke-opacity="1"
                                                          stroke-width="2.810267573765458"
                                                          d=" M56.05,40.16 C53.81,52.87 39.13,62.15 24.34,59.05 C10.13,55.98 1.08,42 5.01,29.25 C9.18,16.01 22.35,12.07 36.57,15.04 C51.27,18.01 58.54,27.69 56.05,40.16z"></path>
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,30.38800048828125,33.638999938964844)">
                                                        <path fill="rgb(0,0,0)" fill-opacity="1"
                                                              d=" M25.658645629882812,6.518488883972168 C23.42104148864746,19.232221603393555 8.737354278564453,28.51234245300293 -6.044381141662598,25.414819717407227 C-20.259004592895508,22.33881187438965 -29.30475616455078,8.365612983703613 -25.379024505615234,-4.389430046081543 C-21.20948600769043,-17.63261604309082 -8.033101081848145,-21.567890167236328 6.184051513671875,-18.603168487548828 C20.87726402282715,-15.633231163024902 28.153108596801758,-5.952154636383057 25.658645629882812,6.518488883972168z"></path>
                                                    </g>
                                                </g>
                                                <g style="display: block;"
                                                   transform="matrix(0.17298713326454163,-0.020137690007686615,0.017678631469607353,0.15186327695846558,132.38385009765625,223.27011108398438)"
                                                   opacity="1">
                                                    <g opacity="1"
                                                       transform="matrix(0.7515299916267395,0,0,0.7515299916267395,15.770000457763672,-20.802000045776367)">
                                                        <path fill="rgb(255,255,255)" fill-opacity="1"
                                                              d=" M25.448999404907227,7.369999885559082 C20.760000228881836,23.562000274658203 5.564000129699707,33.388999938964844 -8.491000175476074,29.31800079345703 C-22.54599952697754,25.24799919128418 -30.13800048828125,8.821999549865723 -25.448999404907227,-7.369999885559082 C-20.759000778198242,-23.562000274658203 -5.564000129699707,-33.388999938964844 8.491000175476074,-29.319000244140625 C22.54599952697754,-25.24799919128418 30.13800048828125,-8.821999549865723 25.448999404907227,7.369999885559082z"></path>
                                                    </g>
                                                </g>
                                                <g style="display: block;"
                                                   transform="matrix(0.6320319175720215,-0.07357577234506607,0.06459126621484756,0.554853081703186,340.7568054199219,184.58001708984375)"
                                                   opacity="1">
                                                    <path stroke-linecap="butt" stroke-linejoin="miter"
                                                          fill-opacity="0" stroke-miterlimit="4"
                                                          stroke="rgb(0,0,0)" stroke-opacity="1"
                                                          stroke-width="2.810267573765458"
                                                          d=" M53.38,31.95 C55.15,44.77 43.84,56.58 28.52,57.14 C10.73,57.77 0.74,46.63 0.91,34.03 C1.35,21.19 9.15,12.43 26.54,11.63 C43.1,10.87 52.11,19.44 53.38,31.95z"></path>
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,27.14699935913086,31.049999237060547)">
                                                        <path fill="rgb(0,0,0)" fill-opacity="1"
                                                              d=" M26.23699951171875,0.8982415199279785 C28.00496482849121,13.724313735961914 16.69042205810547,25.529743194580078 1.3725175857543945,26.086599349975586 C-16.419265747070312,26.716243743896484 -26.407119750976562,15.575119972229004 -26.236000061035156,2.9772415161132812 C-25.800870895385742,-9.864567756652832 -17.999725341796875,-18.6190128326416 -0.60222327709198,-19.4226131439209 C15.951918601989746,-20.178998947143555 24.959989547729492,-11.614766120910645 26.23699951171875,0.8982415199279785z"></path>
                                                    </g>
                                                </g>
                                                <g style="display: block;"
                                                   transform="matrix(0.11722296476364136,-0.013646098785102367,0.011979742906987667,0.10290860384702682,356.36590576171875,196.98597717285156)"
                                                   opacity="1">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,-23.78700065612793,-45.98099899291992)">
                                                        <path fill="rgb(255,255,255)" fill-opacity="1"
                                                              d=" M26.23699951171875,-1.0399999618530273 C26.898000717163086,15.652999877929688 15.687999725341797,29.650999069213867 1.1979999542236328,30.225000381469727 C-13.291999816894531,30.798999786376953 -25.575000762939453,17.73200035095215 -26.236000061035156,1.0390000343322754 C-26.898000717163086,-15.654000282287598 -15.687999725341797,-29.650999069213867 -1.1979999542236328,-30.225000381469727 C13.291999816894531,-30.798999786376953 25.576000213623047,-17.732999801635742 26.23699951171875,-1.0399999618530273z"></path>
                                                    </g>
                                                </g>
                                                <g style="display: block;"
                                                   transform="matrix(1.0533864498138428,-0.12262628972530365,0.10765210539102554,0.9247550964355469,144.7596435546875,197.9034881591797)"
                                                   opacity="1">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,97.20700073242188,71.1989974975586)">
                                                        <path fill="rgb(255,92,30)" fill-opacity="1"
                                                              d=" M101.22000122070312,37.49100112915039 C92.58899688720703,47.672000885009766 43.66400146484375,30.472999572753906 -1.378999948501587,36.14099884033203 C-49.34299850463867,42.17599868774414 -72.09700012207031,52.066001892089844 -81.95899963378906,54.32500076293945 C-102.35099792480469,58.994998931884766 -100.6989974975586,28.02400016784668 -85.20600128173828,22.628999710083008 C-3.691999912261963,-5.755000114440918 -34.41600036621094,-46.18899917602539 -3.941999912261963,-51.520999908447266 C28.722999572753906,-57.236000061035156 2.688999891281128,-4.263000011444092 77.59200286865234,5.64300012588501 C108.03399658203125,9.668999671936035 113.04100036621094,23.547000885009766 101.22000122070312,37.49100112915039z"></path>
                                                        <path stroke-linecap="butt"
                                                              stroke-linejoin="miter"
                                                              fill-opacity="0" stroke-miterlimit="10"
                                                              stroke="rgb(207,53,2)" stroke-opacity="1"
                                                              stroke-width="6.667"
                                                              d=" M101.22000122070312,37.49100112915039 C92.58899688720703,47.672000885009766 43.66400146484375,30.472999572753906 -1.378999948501587,36.14099884033203 C-49.34299850463867,42.17599868774414 -72.09700012207031,52.066001892089844 -81.95899963378906,54.32500076293945 C-102.35099792480469,58.994998931884766 -100.6989974975586,28.02400016784668 -85.20600128173828,22.628999710083008 C-3.691999912261963,-5.755000114440918 -34.41600036621094,-46.18899917602539 -3.941999912261963,-51.520999908447266 C28.722999572753906,-57.236000061035156 2.688999891281128,-4.263000011444092 77.59200286865234,5.64300012588501 C108.03399658203125,9.668999671936035 113.04100036621094,23.547000885009766 101.22000122070312,37.49100112915039z"></path>
                                                    </g>
                                                </g>
                                                <g style="display: block;"
                                                   transform="matrix(1.0612975358963013,-0.008448002859950066,-0.022246699780225754,0.9351533055305481,165.96441650390625,192.40138244628906)"
                                                   opacity="1">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,33.59000015258789,24.059999465942383)">
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(255,180,132)"
                                                              stroke-opacity="1" stroke-width="8"
                                                              d=" M-4.133999824523926,66.6520004272461 C15.543999671936035,55.43600082397461 39.5260009765625,37.487998962402344 36.6609992980957,6.078000068664551"></path>
                                                    </g>
                                                </g>
                                                <g style="display: block;"
                                                   transform="matrix(1.0533864498138428,-0.12262628972530365,0.10765210539102554,0.9247550964355469,187.09921264648438,239.34320068359375)"
                                                   opacity="1">
                                                    <g opacity="1"
                                                       transform="matrix(1,0,0,1,64.81900024414062,32.64699935913086)">
                                                        <path stroke-linecap="round"
                                                              stroke-linejoin="round"
                                                              fill-opacity="0" stroke="rgb(125,9,9)"
                                                              stroke-opacity="1" stroke-width="8"
                                                              d=" M-85.74700164794922,29.072999954223633 C-17.44499969482422,5.822000026702881 31.20199966430664,5.9029998779296875 89.28199768066406,13.989999771118164"></path>
                                                    </g>
                                                </g>
                                            </g>
                                        </g>
                                    </svg>
                                </div>
                            </div>
                            <div class="cart-screen_text__iXE2X">В корзине пока ничего нет. Самое время
                                наполнить ее!
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>