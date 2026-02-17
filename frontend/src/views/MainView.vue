<script>
import { ref, onMounted } from 'vue'
import { useAuthStore, getCSRFToken } from '../users/auth.js'
import { useRouter } from 'vue-router'

export default {
    name: 'MainView',
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
            user_data: '',
            info: {},
            baseUrl: import.meta.env.VITE_API_URL
        }
    },

    async created() {
        const tgUser = this.tg?.initDataUnsafe?.user;
        this.user_id = tgUser?.id;

        await this.fetchProfile();
        await this.fetchMainMessage();
    },

    methods: {
        async fetchProfile() {
            try {
                const firstName = this.tg?.initDataUnsafe?.user?.first_name|| '';
                const telegramName = this.tg?.initDataUnsafe?.user?.telegram_name || '';

                const queryParams = new URLSearchParams({
                    first_name: firstName,
                    telegram_name: telegramName
                }).toString();

                const response = await fetch(`${this.baseUrl}/api/profile/${this.user_id}/?${queryParams}`, {
                    headers: { 'X-CSRFToken': getCSRFToken() }
                });

                if (response.ok) {
                    this.user_data = await response.json();
                }
            } catch (error) {
                console.error("Ошибка в fetchProfile:", error);
            }
        },

        async fetchMainMessage() {
            try {
                const response = await fetch(`${this.baseUrl}/api/main-messages/`);

                if (!response.ok) throw new Error('Ошибка загрузки сообщений');

                this.info = await response.json();
            } catch (error) {
                console.error("Main Message Error:", error);
            }
        },

        ordersLink() {
            this.router.push({
            path: '/orders_history/'
            });
        },

        async editLink() {
            this.$router.push({
            path: '/edit_profile/'
            });
        },
    }
}
</script>

<template>
    <div class="telegram-app_telegram_app__6iz4V" style="margin-left: 10px;"> <!-- box low -->
        <div class="stack-navigation_screen___5WKf screen-0">
            <div class="tab-bar-screen_tab_bar_screen__kkfEZ" style="--tab-bar-height: 49px;">
                <div class="tab-bar-screen_container__PsZlI">
                    <div class="tab-bar-screen_screen__y4lze tab-bar-screen_active__pBXjN tab-home">
                        <div class="stack-navigation_screen___5WKf screen-0">
                            <div class="favorites-screen_favorites_screen__SSbmT"> <!-- box low -->
                                <div class="home-screen_wrapper__3Ji45"> <!-- box upper -->
                                    <div class="actions_actions__Krnjv">
                                        <div class="actions_wrapper__dOu19">
                                            <div class="actions_column__Rl3CY">
                                                <div class="actions_card__etbMU actions_calculate_card__CPhrn">
                                                    <div @click="ordersLink()" class="actions_inner__woSPI">
                                                        <div class="actions_head__nPU_x">
                                                            <div class="actions_title__Z_UU4">Ваши заказы</div>
                                                        </div>
                                                        <div class="actions_footer__I9ld4">
                                                            <div class="actions_icon_box__0CtMZ">
                                                                <svg xmlns="http://www.w3.org/2000/svg"
                                                                     fill="none"
                                                                     viewBox="0 0 20 20" width="1em"
                                                                     height="1em">
                                                                    <path stroke="currentColor"
                                                                          stroke-linecap="round"
                                                                          stroke-linejoin="round"
                                                                          stroke-width="2"
                                                                          d="M4.167 10h11.666m0 0-5 5m5-5-5-5"></path>
                                                                </svg>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                            <div class="actions_column__Rl3CY">
                                                <div class="actions_card__etbMU actions_choose_on_site_card__UFMpb">
                                                    <div class="actions_inner__woSPI" style="padding:0">
                                                        <div class="actions_head__nPU_x" style="justify-content:center">
                                                            <img :src="`${baseUrl}/media/logo.jpg`" alt="ottuda" width="148px">
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        <div @click="editLink()" v-if="!user_data.phone" class="actions_wrapper__dOu19">
                                            <div class="main_info_message">
                                                У вас не указан номер телефона, он необходим для оформления заказа. Нажмите для редатирования профиля.
                                            </div>
                                        </div>
                                    </div>
                                    <template v-for="message in info">
                                        <div class="product-horizontal-list_header__kQNss">
                                            <div class="product-horizontal-list_info__FVjM3">
                                                <div class="product-horizontal-list_title__d4p_N">{{ message.title }}
                                                </div>
                                            </div>
                                        </div>
                                        <div class="bot-text">
                                            <p>{{ message.text }}</p>
                                        </div>
                                        <div v-if="message.image" class="bot-image-wrapper">
                                            <img :src="message.image" class="bot-image" alt="{{ message.title }}">
                                        </div>
                                    </template>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
