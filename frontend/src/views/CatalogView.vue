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
            <div class="catalog-screen_catalog_screen__rP0k4">
                <div class="catalog-screen_wrapper__WjtzY">
                    <div class="catalog-screen_content__p1Hje">
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
                                         style="justify-content:left;flex-wrap:wrap">
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
</template>
