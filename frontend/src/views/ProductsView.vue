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
                                            <!--                                            <div class="heading_search__KpO8Z">-->
                                            <!--                                                <div class="search-input-button_container__PU3cS"><span>Поиск</span>-->
                                            <!--                                                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"-->
                                            <!--                                                         viewBox="0 0 24 24" fill="none" stroke="currentColor"-->
                                            <!--                                                         stroke-width="1" stroke-linecap="round" stroke-linejoin="round"-->
                                            <!--                                                         class="tabler-icon tabler-icon-search ">-->
                                            <!--                                                        <path d="M10 10m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0"></path>-->
                                            <!--                                                        <path d="M21 21l-6 -6"></path>-->
                                            <!--                                                    </svg>-->
                                            <!--                                                </div>-->
                                            <!--                                            </div>-->
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
                                                                        {{ product.price * product.discount_group.regular_value }} ₽
                                                                    </span>
                                                                    <span :style="{ display: (product?.rests[0]?.shop_active_discount === 'extra' && Number(product.discount_group.extra_value) !== 1) ? '' : 'none' }">
                                                                        {{ product.price * product.discount_group.extra_value }} ₽
                                                                    </span>
                                                                </div>
                                                                <div class="product-card_name__EfN1S"> {{ product.name
                                                                    }}
                                                                </div>
                                                                <div class="product-card_properties__8Op3G">
                                                                    <div class="product-card_delivery__s1GEd">
                                                                        № {{ product.id }} :: В наличии {{
                                                                        product.rests[0].amount }}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </a>
                                                    </div>
                                                    <div v-if="loading">Загрузка...</div>
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

<script>
import { useAuthStore, getCSRFToken } from '../users/auth.js'
import { useRouter } from 'vue-router'

import jsonData from '../response.json' // Import the data

export default {
    name: 'ProductView',
    data() {
        return {
            user: {
                user_id: '',
                user_data: ''
            },
            catalog: {},
            products: [],
            nextPageUrl: null,
            loading: false,
            shop_discount: 'no_sale'
        }
    },
    setup() {
        const authStore = useAuthStore();
        const router = useRouter();


        return {
            authStore,
            router,
        }
    },

    async created() {
        await this.fetchProfile();
        await this.fetchCatalog();
    },

    async mounted() {
        this.loadProducts();
        window.addEventListener('scroll', this.handleScroll);
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

        async fetchCatalog() {
                const response = await fetch(`http://localhost:8000/api/category/${this.$route.query.catalog_id}`, {
                            method: 'GET',
                            headers: {
                              'Content-Type': 'application/json',
                              'X-CSRFToken': getCSRFToken(),
                            },
                            credentials: 'include',
                          })
                this.catalog = await response.json()
            },
        handleScroll() {
            const el = this.$refs.scrollContainer;

            if (el.scrollHeight - el.scrollTop <= el.clientHeight + 50) {
                if (!this.loading && this.nextPageUrl && this.nextPageUrl !== 'stop') {
                    this.loadProducts();
                }
            }
        },

        async loadProducts() {

            let url = this.nextPageUrl;
            console.log(this.user.user_id)
            if (!url) {
                    const catId = this.$route.query.catalog_id;
                    url = `http://localhost:8000/api/products?category=${catId}&chat_id=${this.user.user_id}`;
                }

            if (this.loading || url === 'stop') return;

            this.loading = true;
            try {
                const response = await fetch(url);
                const data = await response.json();

                this.products = [...this.products, ...data.results];

                this.nextPageUrl = data.links.next || 'stop';
                console.log(this.products)

            } catch (e) {
                console.error(e);
            } finally {
                this.loading = false;
            }
        },

        async toggleTrack(productId) {
            try {
                const response = await fetch('http://localhost:8000/api/profile/track/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken(),
                    },
                    body: JSON.stringify({
                        chat_id: this.user.user_id,
                        product_id: productId
                    }),
                    credentials: 'include',
                });

                if (response.ok) {
                    const data = await response.json();

                    const product = this.products.find(p => p.id === productId);
                    if (product) {
                        product.is_tracked = !product.is_tracked;
                    }


                    console.log(`Товар ${data.action}`);
                }
            } catch (e) {
                console.error("Ошибка при обновлении трека:", e);
            }
        },


        handleImageError(event) {
            event.target.src = 'http://localhost:8000/static/products/no-image.jpg';
        },

        productLink(id) {
                this.$router.push({
                path: '/product',
                query: { id: id }
            });
        },

        catalogLink(id) {
            this.$router.push({
            path: '/catalog',
            query: { id: id }
            });
        },

    }
}
</script>