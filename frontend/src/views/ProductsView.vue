<script>
import { ref, onMounted } from 'vue'
import { useAuthStore, getCSRFToken } from '../users/auth.js'
import { useRouter } from 'vue-router'

export default {
    name: 'ProductView',
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
            catalog: {},
            products: [],
            nextPageUrl: null,
            loading: false,
            shop_discount: 'no_sale',
            baseUrl: import.meta.env.VITE_API_URL
        }
    },

    async created() {
        const tgUser = this.tg?.initDataUnsafe?.user;
        this.user_id = tgUser?.id;

        await this.fetchCatalog();
        await this.loadProducts();
    },

    mounted() {
        window.addEventListener('scroll', this.handleScroll);
    },

    beforeUnmount() {
        window.removeEventListener('scroll', this.handleScroll);
    },

    methods: {
        async fetchCatalog() {
            try {
                const response = await fetch(`${this.baseUrl}/api/category/${this.$route.query.catalog_id}/?chat_id=${this.user_id}`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken(),
                    },
                    credentials: 'include',
                });
                if (response.ok) {
                    this.catalog = await response.json();
                }
            } catch (e) {
                console.error("Ошибка каталога:", e);
            }
        },

        handleScroll() {
            const el = this.$refs.scrollContainer || document.documentElement;
            const scrollBottom = el.scrollHeight - el.scrollTop <= el.clientHeight + 100;

            if (scrollBottom && !this.loading && this.nextPageUrl !== 'stop') {
                this.loadProducts();
            }
        },

        async loadProducts() {
            if (this.loading || this.nextPageUrl === 'stop') return;

            let url = this.nextPageUrl;
            if (!url) {
                const catId = this.$route.query.catalog_id;
                url = `${this.baseUrl}/api/products/?category=${catId}&chat_id=${this.user_id}`;
            }

            this.loading = true;
            try {
                const response = await fetch(url);
                const data = await response.json();

                const newProducts = data.results || [];
                this.products = [...this.products, ...newProducts];

                this.nextPageUrl = data.links?.next || data.next || 'stop';
            } catch (e) {
                console.error("Ошибка загрузки товаров:", e);
            } finally {
                this.loading = false;
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
                    }),
                    credentials: 'include',
                });

                if (response.ok) {
                    const product = this.products.find(p => p.id === productId);
                    if (product) {
                        product.is_tracked = !product.is_tracked;
                    }
                }
            } catch (e) {
                console.error("Ошибка при обновлении трека:", e);
            }
        },

        handleImageError(event) {
            event.target.src = `${this.baseUrl}/static/products/no-image.jpg`;
        },

        productLink(id) {
            this.router.push({ path: '/product/', query: { id: id } });
        },

        catalogLink(id) {
            this.router.push({ path: '/catalog/', query: { id: id } });
        },
    }
}
</script>

<template>
    <div class="telegram-app_telegram_app__6iz4V"> <!-- box low -->
        <div class="stack-navigation_screen___5WKf screen-0">
            <div class="tab-bar-screen_tab_bar_screen__kkfEZ" style="--tab-bar-height: 49px;">
                <div class="tab-bar-screen_container__PsZlI">
                    <div class="tab-bar-screen_screen__y4lze tab-bar-screen_active__pBXjN tab-catalog">
                        <div class="stack-navigation_screen___5WKf screen-0">
                            <div class="catalog-category-screen_catalog_category_screen__WLIa6"> <!-- box low -->
                                <div class="heading_heading__LP60V products_heading__tXqTW"> <!-- header catalog -->
                                    <div class="container_container__OTRj8 heading_container__iqu2k">
                                        <div class="heading_containerSearchHeader__HN8N6">
                                            <div class="heading_compound_header__ehM2t">
                                                <div v-if="catalog.breadcrumbs && catalog.breadcrumbs.length > 0"
                                                     class="gender-categories_header__CcM7p"
                                                     style="justify-content:left">

                                                    <a @click="catalogLink(null)"
                                                       class="breadcrumb-link">
                                                        Начало</a><b>></b>
                                                    <template
                                                            v-for="(crumb, index) in catalog.breadcrumbs"
                                                            :key="index">
                                                        <a @click="catalogLink(crumb.id)"
                                                           class="breadcrumb-link">
                                                            {{ crumb.command }}</a><b>></b>
                                                    </template>
                                                </div>
                                                <div class="heading_search_row__bwFkS">
                                                    <h1 class="heading_title__mqET_">
                                                        {{ this.catalog.command }}
                                                    </h1>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="products_products_page__cvIez"> <!-- product catalog -->
                                    <div class="container_container__OTRj8">
                                        <div class="products_body__A_1DV">
                                            <div class="products_products__U66Dk">
                                                <div class="">
                                                    <div class="client-product-grid_client_product_grid__qaOK8"
                                                         ref="scrollContainer"
                                                         @scroll="handleScroll"
                                                         style="height: 80vh; overflow-y: auto;">
                                                        <a v-for="(product) in this.products" :key="product.id"
                                                           @click="productLink(product.id)"
                                                           class="product-card_product_card__i7cQJ client-product-grid_product__eQVXY">
                                                            <div class="product-card-images_wrap__1bDck">
                                                                <div class="product-card-images_scroll__cMUco">
                                                                    <div><img :src="product.image?.url"
                                                                              @error="handleImageError"
                                                                              :alt="product?.name"
                                                                              class="product-card-images_cover__zSpAe">
                                                                    </div>
                                                                </div>
                                                            </div>
                                                            <button
                                                                    @click.stop="toggleTrack(product?.id)"
                                                                    class="favorite-button_favorite_button__a_ct8 product-card_favorite__ticzG"
                                                                    :class="{'favorite-button_on__2qN_y': product?.is_tracked}"
                                                                    :aria-label="product?.is_tracked ? 'Лайк' : 'Снять лайк'"
                                                            >
                                                                <svg xmlns="http://www.w3.org/2000/svg" width="22"
                                                                     height="22" viewBox="0 0 24 24" fill="none"
                                                                     stroke="currentColor" stroke-width="1"
                                                                     stroke-linecap="round" stroke-linejoin="round"
                                                                     class="tabler-icon tabler-icon-heart ">
                                                                    <path d="M19.5 12.572l-7.5 7.428l-7.5 -7.428a5 5 0 1 1 7.5 -6.566a5 5 0 1 1 7.5 6.572"></path>
                                                                </svg>
                                                            </button>
                                                            <div class="product-card_card_body__6SHkh">
                                                                <div class="product-card-price_product_card_price__wgMh1 product-card-price_num__oTZ2i">
                                                                    <span :class="{'discount-active': product?.rests[0]?.shop_active_discount !== 'no_sale' &&
                                                                    Number(product?.rests[0]?.shop_active_discount === 'extra' ? product?.discount_group?.extra_value : product?.discount_group?.regular_value) !== 1}">
                                                                        {{ product.price * 1 }} ₽
                                                                    </span>
                                                                    <span :style="{ display: (product?.rests[0]?.shop_active_discount === 'regular' && Number(product.discount_group.regular_value) !== 1) ? '' : 'none' }">
                                                                        {{ Math.round(product.price * product.discount_group.regular_value) }} ₽
                                                                    </span>
                                                                    <span :style="{ display: (product?.rests[0]?.shop_active_discount === 'extra' && Number(product.discount_group.extra_value) !== 1) ? '' : 'none' }">
                                                                        {{ Math.round(product.price * product.discount_group.extra_value) }} ₽
                                                                    </span>
                                                                </div>
                                                                <div class="product-card_name__EfN1S"> {{ product.name
                                                                    }}
                                                                </div>
                                                                <div class="product-card_properties__8Op3G">
                                                                    <div class="product-card_delivery__s1GEd">
                                                                        № {{ product.id }} :: В наличии {{
                                                                        product.rests[0]?.amount }}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </a>
                                                        <div v-if="loading" class="loader_ring"></div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>