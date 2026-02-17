<script>
import { ref, onMounted } from 'vue'
import { useAuthStore, getCSRFToken } from '../users/auth.js'
import { useRouter } from 'vue-router'

export default {
    name: 'ProductDetailView',
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
            user_data: {},
            product: null,
            cart: null,
            quantity: 0,
            discount_value: 1,
            baseUrl: import.meta.env.VITE_API_URL
        }
    },

    async created() {
        const tgUser = this.tg?.initDataUnsafe?.user;
        this.user_id = tgUser?.id;

        await this.fetchProfile();
        await this.fetchProductDetail();
        if (this.product) {
            await this.fetchCart();
        }
    },

    methods: {
        async fetchProfile() {
            try {
                const response = await fetch(`${this.baseUrl}/api/profile/${this.user_id}/`, {
                    headers: {
                        'X-CSRFToken': getCSRFToken()
                        }
                });
                if (response.ok) {
                    this.user_data = await response.json();
                }
            } catch (error) {
                console.error("Ошибка загрузки профиля:", error);
            }
        },

        async fetchCart() {
            try {
                const response = await fetch(`${this.baseUrl}/api/cart/?chat_id=${this.user_id}`);
                const data = await response.json();
                const cartItems = data.results || [];

                this.cart = cartItems.find(item => {
                    const cartProductId = item.product?.id || item.product;
                    return cartProductId === this.product?.id;
                });

                this.quantity = this.cart ? this.cart.amount : 0;
            } catch (e) {
                console.error("Ошибка загрузки корзины", e);
                this.quantity = 0;
            }
        },

        async fetchProductDetail() {
            try {
                const id = this.$route.query.id;
                const response = await fetch(`${this.baseUrl}/api/product/${id}/?chat_id=${this.user_id}`, {
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken(),
                    }
                });
                this.product = await response.json();

                const discountType = this.product?.rests[0]?.shop_active_discount;
                const group = this.product?.discount_group;

                this.discount_value = (discountType === 'extra') ? (group?.extra_value || 1) :
                                      (discountType === 'regular') ? (group?.regular_value || 1) : 1;
            } catch (e) {
                console.error("Ошибка загрузки товара", e);
            }
        },

        handleImageError(event) {
            event.target.src = `${this.baseUrl}/static/products/no-image.jpg`;
        },

        async changeCount(product, delta) {
            const maxRest = product?.rests[0]?.amount || 0;
            const nextValue = this.quantity + delta;

            const isPreorderMode = this.user_data?.preorder === true;

            if (delta > 0 && nextValue > maxRest && !isPreorderMode) {
                return;
            }

            if (nextValue <= 0) {
                this.quantity = 0;
                if (this.cart?.id) {
                    try {
                        const response = await fetch(`${this.baseUrl}/api/cart/${this.cart.id}/?chat_id=${this.user_id}`, {
                            method: 'DELETE',
                            headers: { 'X-CSRFToken': getCSRFToken() },
                            credentials: 'include',
                        });
                        if (response.ok) {
                            this.cart = null;
                        }
                    } catch (error) {
                        console.error("Ошибка при удалении:", error);
                    }
                }
                return;
            }

            if (nextValue <= maxRest || isPreorderMode) {
                this.quantity = nextValue;
                try {
                    const isPreorderItem = (maxRest === 0 || nextValue > maxRest) && isPreorderMode;

                    const payload = {
                        chat_id: this.user_id,
                        product: product.id,
                        amount: this.quantity,
                        price: product.price,
                        preorder: isPreorderItem
                    };

                    const response = await fetch(`${this.baseUrl}/api/cart/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCSRFToken(),
                        },
                        body: JSON.stringify(payload),
                        credentials: 'include',
                    });

                    if (response.ok) {
                        const data = await response.json();
                        this.cart = data;
                    }
                } catch (error) {
                    console.error("Ошибка сети:", error);
                }
            }
        },

        async toggleTrack(productId) {
            try {
                const response = await fetch(`${this.baseUrl}/api/profile/track/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken(),
                    },
                    body: JSON.stringify({
                        chat_id: this.user_id,
                        product_id: productId
                    })
                });

                if (response.ok) {
                    if (this.product) this.product.is_tracked = !this.product.is_tracked;
                }
            } catch (e) {
                console.error("Ошибка трекинга:", e);
            }
        },

        catalogLink(id) {
            this.router.push({ path: '/catalog/', query: { id: id } });
        }
    }
}
</script>

<template>
    <div class="telegram-app_telegram_app__6iz4V"> <!-- box low -->
        <div class="stack-navigation_screen___5WKf screen-0">
            <div class="tab-bar-screen_tab_bar_screen__kkfEZ" style="--tab-bar-height: 49px;">
                <div class="tab-bar-screen_container__PsZlI">
                    <div class="tab-bar-screen_screen__y4lze tab-bar-screen_active__pBXjN tab-catalog">
                        <div class="stack-navigation_screen___5WKf screen-0.32849058145042576">
                            <div class="product-screen_product_screen__4p1ko product-screen_show_off_hero__W2_B8">
                                <div class="product-screen_inner__OqLLs">
                                    <div>
                                        <div class="hero-show-off-variant_productHero__Kspuk">
                                            <div>
                                                <div class="hero-show-off-variant_productHero_showOff_sneaker__jewgd">
                                                    <div v-if="product?.breadcrumbs && product?.breadcrumbs.length > 0"
                                                         class="hero-show-off-variant_productHero_showOff_sneaker_brand_title__s7U3f"
                                                         style="justify-content:left;flex-direction:row;">

                                                        <a @click="catalogLink(null)"
                                                           class="breadcrumb-link">
                                                            Начало</a><b>></b>
                                                        <template
                                                                v-for="(crumb, index) in product.breadcrumbs"
                                                                :key="index">
                                                            <a @click="catalogLink(crumb.id)"
                                                               class="breadcrumb-link">
                                                                {{ crumb.command }}</a><b>></b>
                                                        </template>
                                                    </div>
                                                </div>
                                                <div class="hero-show-off-variant_productHero_showOff_sneaker__jewgd">
                                                    <div class="hero-show-off-variant_productHero_showOff_wrapper__d5b_E">
                                                        <div class="hero-show-off-variant_productHero_showOff_sneaker_brand_title__s7U3f">
                                                            <h1 class="hero-show-off-variant_productHero_showOff_sneaker_title__fLzsC"
                                                                style="-webkit-text-stroke: 0.1px black">
                                                                {{ product?.name }}</h1>
                                                        </div>
                                                    </div>
                                                    <div class="hero-show-off-variant_productHero_showOff_sneaker_imageMobile__X55d_">
                                                        <img v-if="product && product.image"
                                                             :src="product.image.url"
                                                             :alt="product.name"
                                                             @error="handleImageError" style="color: transparent;">
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        <div class="hero-info_productHero_showOff_info_wrapper___G_08">
                                            <div class="hero-info_productHero_showOff_info__zVLke">
                                                <div class="hero-info_productHero_showOff_properties_infoBlockParent__Jf_6m">
                                                    <div class="hero-info_productHero_showOff_properties_infoBlock__orWv6">
                                                        <div class="original_original___BEbe">
                                                            <div class="original_original_main__2ulSI">
                                                                Количество: {{ product?.rests[0]?.amount * 1 || 0 }} шт.
                                                            </div>
                                                        </div>
                                                        <div>
                                                            <div>
                                                                <div style="background-color: rgb(0, 0, 0);"></div>
                                                            </div>
                                                            <div>
                                                                <div style="background-color: rgb(215, 215, 215);"></div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <button
                                                            @click="toggleTrack(product?.id)"
                                                            class="favorite-button_favorite_button__a_ct8 hero-info_heart__hUlWV"
                                                            :class="{'favorite-button_on__2qN_y': product?.is_tracked}"
                                                            :aria-label="product?.is_tracked ? 'Лайк' : 'Снять лайк'"
                                                    >
                                                        <svg xmlns="http://www.w3.org/2000/svg" width="36"
                                                             height="36" viewBox="0 0 24 24" fill="none"
                                                             stroke="currentColor" stroke-width="1.5"
                                                             stroke-linecap="round" stroke-linejoin="round"
                                                             class="tabler-icon tabler-icon-heart ">
                                                            <path d="M19.5 12.572l-7.5 7.428l-7.5 -7.428a5 5 0 1 1 7.5 -6.566a5 5 0 1 1 7.5 6.572"></path>
                                                        </svg>
                                                    </button>
                                                </div>
                                                <div>
                                                    <div class="product-properties_wrapper__ykc45"
                                                         data-scroll-left="false" data-scroll-right="false">
                                                        <div class="product-properties_product_properties__Hi4E8">
                                                            <div class="product-properties_property__UvQmG">
                                                                <div class="product-properties_property_title__p58An">
                                                                    Артикул
                                                                </div>
                                                                <div class="product-properties_property_value__rSTbK">
                                                                    <span>№ {{ product?.id }}</span></div>
                                                            </div>
                                                            <div class="product-properties_property__UvQmG">
                                                                <div class="product-properties_property_title__p58An">
                                                                    Описание:
                                                                </div>
                                                                <div class="product-properties_property_value__rSTbK">
                                                                    {{ product?.description }}
                                                                </div>
                                                            </div>
                                                        </div>
                                                        <div class="product-properties_custom_scrollbar__vlK2w">
                                                            <div class="product-properties_custom_scrollbar_thumb__KOV2d"
                                                                 style="width: 108.165px; transform: translateX(0px);"></div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                    </div>
                                    <div class="product-actions_product_actions__ng4Ma product-actions_with_tabbar__Dn8nh product-screen_actions__EaCEp">
                                        <div class="product-actions_buttons__9Rs_R">
                                            <div class="product-actions_cart__cU4sQ">
                                                <div data-v-5bff6dd4="" class="cart-item_button__MUAX2">
                                                    <div @click.stop="changeCount(product, -1)"
                                                         class="cart-item_change_count__IejK4"
                                                         :class="{ 'hide': (quantity || 0) <= 0 }">
                                                        -
                                                    </div>
                                                    {{ quantity || 0 }}
                                                    <div @click.stop="changeCount(product, 1)"
                                                         class="cart-item_change_count__IejK4"
                                                         :class="{ 'hide': ((quantity || 0) >= (product?.rests[0]?.amount || 0) || (product?.rests[0]?.amount || 0) === 0) && !user_data?.preorder }">
                                                        +
                                                    </div>
                                                </div>
                                            </div>
                                            <div class="button_button__AjjDz product-actions_buy__hoAgO"
                                                 :style="{
                                                    background: (product?.rests?.length === 0 && !user_data?.preorder) ? '#de0e18 !important' :
                                                                (product?.rests?.length === 0 && user_data?.preorder) ? '#eb9c00 !important' : '' }"
                                                 href="">
                                                <span style="display: inline-block; transform: translateZ(0); will-change: contents;">
                                                    {{ quantity === 0 ? 'Цена:' : 'Сумма:' }}
                                                </span>
                                                <div>
                                                    <div v-if="product?.rests?.length > 0">
                                                        <!-- Основная цена (зачеркивается, если есть активная скидка) -->
                                                        <span :class="{'discount-active': product?.rests[0]?.shop_active_discount !== 'no_sale' && Number(discount_value) !== 1}">
                                                            {{ Math.round(product?.price) * (quantity || 1) }}&nbsp;₽
                                                        </span>

                                                        <!-- Цена со скидкой (показывается только если скидка активна и не равна 1) -->
                                                        <span v-if="product?.rests[0]?.shop_active_discount !== 'no_sale' && Number(discount_value) !== 1">
                                                            <br>
                                                            {{ Math.round(product?.price * discount_value) * (quantity || 1) }}&nbsp;₽
                                                        </span>
                                                    </div>
                                                    <!-- СЛУЧАЙ 2: Товара нет в наличии (rests пустой) -->
                                                    <div v-else>
                                                        <!-- Если включен предзаказ — показываем цену -->
                                                        <span v-if="user_data?.preorder">
                                                            {{ Math.round(product?.price) * (quantity || 1) }}&nbsp;₽
                                                        </span>
                                                        <!-- Если предзаказ выключен — пишем "Нет в наличии" -->
                                                        <span v-else>
                                                            Нет в наличии
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="snackbar-container_snackbar_container__gTEZz"
                                 style="--snackbar-bottom: 167px;"></div>

                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>