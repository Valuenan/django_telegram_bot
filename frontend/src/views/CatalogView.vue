<script>
import { ref, onMounted } from 'vue'
import { useAuthStore, getCSRFToken } from '../users/auth.js'
import { useRouter, useRoute } from 'vue-router'

export default {
    name: 'CatalogView',
    setup() {
        const authStore = useAuthStore();
        const router = useRouter();
        const route = useRoute();
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
            route,
            isTelegram,
            tg
        }
    },

    data() {
        return {
            user_id: '',
            catalog: [],
            main_catalog: 1,
            loading: true,
            baseUrl: import.meta.env.VITE_API_URL
        }
    },

    mounted() {
        const catalogId = this.$route.query.id;
        this.fetchCatalog(catalogId);
    },

    methods: {
        async fetchCatalog(id = null) {
            const targetId = id || null;
            const url = targetId
                ? `${this.baseUrl}/api/category/${targetId}/`
                : `${this.baseUrl}/api/catalog/`;

            try {
                const response = await fetch(url, {
                    headers: { 'X-CSRFToken': getCSRFToken() }
                });
                const data = await response.json();
                this.loading = false

                if (!targetId) {
                    this.main_catalog = 1;
                    this.catalog = data.results || data;
                } else {
                    this.main_catalog = 0;
                    this.catalog = data;

                    if (data.children && data.children.length === 0) {
                        this.router.push({
                            path: '/products/',
                            query: { catalog_id: targetId }
                        });
                    }
                }
            } catch (e) {
                console.error("Ошибка загрузки каталога", e);
            }
        },

        async allInCategory(id) {
            this.router.push({
                path: '/products/',
                query: { catalog_id: id }
            })
        },
    }
}
</script>

<template>
    <div class="telegram-app_telegram_app__6iz4V">
        <div class="stack-navigation_screen___5WKf">
            <div class="tab-bar-screen_tab_bar_screen__kkfEZ"
                 style="--tab-bar-height: 49px;--tg-content-safe-area-inset-top: 48px">
                <div class="tab-bar-screen_container__PsZlI">
                    <div class="tab-bar-screen_screen__y4lze tab-bar-screen_active__pBXjN tab-catalog">
                        <div class="stack-navigation_screen___5WKf">
                            <div class="favorites-screen_favorites_screen__SSbmT">
                                <div class="catalog-screen_wrapper__WjtzY">
                                    <div class="catalog-screen_content__p1Hje">
                                        <div class="gender-categories_grid_category_section__33Ww1">
                                            <div v-if="loading" class="loader_ring"></div>
                                            <div v-if="main_catalog === 1"
                                                 v-for="(parent_category) in this.catalog"
                                                 class="gender-categories_section___6yOW">
                                                <div class="gender-categories_header__CcM7p">
                                                    <div class="gender-categories_title__NYQm5">
                                                        {{ parent_category.command }}
                                                    </div>
                                                </div>
                                                <div class="gender-categories_body__nnTOU">
                                                    <div class="gender-categories_row__B5nMy"
                                                         style="--row-grid-columns:repeat(2, 1fr);--row-grid-rows:1fr">

                                                        <div v-for="(children_category) in parent_category.children"
                                                             :key="children_category.id"
                                                             @click="fetchCatalog(children_category.id)"
                                                             class="gender-categories_column__ixf6W"
                                                             style="--column-grid-column:auto;--column-grid-row:1fr">
                                                            <div class="gender-categories_title__NYQm5">
                                                                <b>{{ children_category.command }}</b>
                                                            </div>
                                                        </div>

                                                    </div>
                                                </div>
                                            </div>

                                            <div v-else
                                                 class="gender-categories_section___6yOW">
                                                <div>
                                                    <div v-if="catalog.breadcrumbs && catalog.breadcrumbs.length > 0"
                                                         class="gender-categories_header__CcM7p"
                                                         style="justify-content:left">
                                                        <a @click="fetchCatalog(null)"
                                                                 class="breadcrumb-link gender-categories_title__NYQm5">
                                                                Начало
                                                            </a>
                                                            <b>></b>
                                                        <template
                                                                v-for="(crumb, index) in catalog.breadcrumbs.slice(0, -1)"
                                                                :key="index">
                                                            <a @click="fetchCatalog(crumb.id)"
                                                                 class="breadcrumb-link gender-categories_title__NYQm5">
                                                                {{ crumb.command }}
                                                            </a>
                                                            <b>></b>
                                                        </template>
                                                    </div>

                                                    <div class="gender-categories_header__CcM7p">
                                                        <div class="gender-categories_title__NYQm5">
                                                            {{ this.catalog.command }}
                                                        </div>
                                                        <button @click="allInCategory(this.catalog.id)"
                                                                class="button_button__FUDeW button_secondary__bEjIM gender-categories_see_all__zXRbP">
                                                            Все
                                                            <svg xmlns="http://www.w3.org/2000/svg" fill="none"
                                                                 viewBox="0 0 20 20"
                                                                 width="1em"
                                                                 height="1em">
                                                                <path stroke="currentColor" stroke-linecap="round"
                                                                      stroke-linejoin="round"
                                                                      stroke-width="1.5" d="m7.5 5 5 5-5 5"></path>
                                                            </svg>
                                                        </button>
                                                    </div>
                                                </div>
                                                <div class="gender-categories_body__nnTOU">
                                                    <div class="gender-categories_row__B5nMy"
                                                         style="--row-grid-columns:repeat(2, 1fr);--row-grid-rows:1fr">

                                                        <div v-for="(children_category) in this.catalog.children"
                                                             :key="children_category.id"
                                                             @click="fetchCatalog(children_category.id)"
                                                             class="gender-categories_column__ixf6W"
                                                             style="--column-grid-column:auto;--column-grid-row:1fr">
                                                            <div class="gender-categories_title__NYQm5">
                                                                <b>{{ children_category.command }}</b>
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
        </div>
    </div>
</template>
