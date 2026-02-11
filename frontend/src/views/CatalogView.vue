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

<script>
import { useAuthStore, getCSRFToken } from '../users/auth.js'
import { useRouter } from 'vue-router'

import jsonData from '../response.json' // Import the data



export default {
    name: 'CatalogView',
    data() {
        return {
            user: {
                user_id: '',
                user_data: ''
            },
            catalog: [],
            main_catalog: 1,
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



    mounted() {
        const catalogId = this.$route.query.id;
    this.fetchCatalog(catalogId);
    },

    async created() {
        await this.fetchProfile();
    },



    methods: {
            async fetchProfile() {
                try {
                    // jsonData window.Telegram.WebApp.initDataUnsafe?.user
                    const tg_user = jsonData
                    this.user.user_id = tg_user.user.id
                    // const response = await fetch(`https://refactored-fishstick-jj7qgwww9x94cq4r6-8000.app.github.dev/api/main/${tg_user.id}`)
                    // const data = await response.json()

                    const response = await fetch(`http://localhost:8000/user/${this.user.user_id}`, {
                        method: 'GET',
                        headers: {
                          'Content-Type': 'application/json',
                          'X-CSRFToken': getCSRFToken(),
                        },
                        credentials: 'include',
                      })
                    this.user.user_data = await response.json()

                  if (this.user.user_data.result == 'crated') {
                    const response = await fetch('http://localhost:8000/user_edit', {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                      'X-CSRFToken': getCSRFToken(),
                    },
                     body: JSON.stringify({
                         chat_id: tg_user.user.id,
                         first_name: tg_user.user.first_name,
                         last_name: tg_user.user.last_name,
                         telegram_name: tg_user.user.username
                    }),
                    credentials: 'include',
                      })

                  }

                } catch (error) {
                    console.log(error);
                }
            },

            async fetchCatalog(id = null) {
                const targetId = id || null;

                const url = targetId
                    ? `http://localhost:8000/api/category/${targetId}`
                    : 'http://localhost:8000/api/catalog';

                try {
                    const response = await fetch(url, { /* ... ваши заголовки ... */ });
                    const data = await response.json();

                    if (!targetId) {
                        // Логика для корня каталога
                        this.main_catalog = 1; // Условно помечаем, что мы в корне
                        this.catalog = data.results || data;
                    } else {
                        // Логика для конкретной категории
                        this.main_catalog = 0;
                        this.catalog = data;

                        // Если детей нет — уходим в список товаров
                        if (data.children && data.children.length === 0) {
                            this.$router.push({
                                path: '/products',
                                query: { catalog_id: targetId }
                            });
                        }
                    }
                } catch (e) {
                    console.error("Ошибка загрузки каталога", e);
                }
            },

        async allInCategory(id) {
            this.$router.push({
                path: '/products',
                query: { catalog_id: id }
            })
        },

    }
}

// telegram authentication
/*
export default {
    name: 'ProfileView',
    data() {
        return {
            user: {
                id: '',
                name: '',
                completedTasks: 0
            }
        }
    },
    async mounted() {
        await this.fetchProfile()
    },
    methods: {
        async fetchProfile() {
            try {
                const tg_user = window.Telegram.WebApp.initDataUnsafe?.user
                const response = await fetch(`https://refactored-fishstick-jj7qgwww9x94cq4r6-8000.app.github.dev/api/main/${tg_user.id}`)
                const data = await response.json()
                this.user.id = tg_user.id
                this.user.name = tg_user.first_name
                this.user.completedTasks = data.completedTasks
            } catch (error) {
                console.log(error)
            }
        },
    }
}
*/
</script>
