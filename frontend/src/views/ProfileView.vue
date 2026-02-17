<script>
import { ref, onMounted } from 'vue';
import { useAuthStore, getCSRFToken } from '../users/auth.js'
import { useRouter } from 'vue-router'

export default {
    name: 'ProfileView',
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
            ordersCount: 0,
            baseUrl: import.meta.env.VITE_API_URL
        }
    },

    async created() {
        await this.fetchProfile();
        await this.fetchOrders()
    },

    methods: {
        async fetchProfile() {
            try {
                const tgUser = this.tg?.initDataUnsafe?.user;
                this.user_id = tgUser?.id;

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

        async fetchOrders() {
            try {
                const response = await fetch(`${this.baseUrl}/api/orders/?chat_id=${this.user_id}`)
                const data = await response.json()
                this.ordersCount = data.count

              } catch (error) {
                console.log(error);
            }
        },

        async togglePreorder(event) {
            const newValue = event.target.checked;
            this.user_data.preorder = newValue;

            try {
                const response = await fetch(`${this.baseUrl}/api/profile/update/`, {
                    method: 'PATCH',
                                headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken()
                    },
                    body: JSON.stringify({
                        chat_id: this.user_id,
                        preorder: newValue
                    })
                });

                if (!response.ok) throw new Error("Ошибка при сохранении");

            } catch (error) {
                console.error("Не удалось обновить статус на сервере:", error);
                this.user_data.preorder = !newValue;
            }
        },

        async editLink() {
            this.$router.push({
            path: '/edit_profile/'
            });
        },

        async ordersFavorite() {
            this.$router.push({
            path: '/favorite/'
            });
        },

        async ordersLink() {
            this.$router.push({
            path: '/orders_history/'
            });
        }
    }
}
</script>

<template>
    <div class="telegram-app_telegram_app__6iz4V">
        <div class="stack-navigation_screen___5WKf screen-0">
            <div class="tab-bar-screen_tab_bar_screen__kkfEZ" style="--tab-bar-height: 49px;">
                <div class="tab-bar-screen_container__PsZlI">
                    <div class="tab-bar-screen_screen__y4lze tab-bar-screen_active__pBXjN tab-settings">
                        <div class="stack-navigation_screen___5WKf screen-0">

                            <div class="my-profile-page_profile_page__RST4o">
                                <div class="my-profile-page_head____pVZ">
                                    <div class="my-profile-page_title__97P4K">Профиль</div>
                                </div>
                                <ul class="section_section__M8xUg">
                                    <li class="section-item_section_item_action__SzcKE">
                                        <div class="ui_layout__4JB94">
                                            <div class="data-section-row_data_section_row__qEDdW">
                                                <span>ID пользователя</span>
                                                <span class="data-section-row_value__OkqbL data-section-row_empty__LHAq3">{{ user_data.chat_id ?? 'Не указан' }}</span>
                                            </div>
                                            <div class="data-section-row_data_section_row__qEDdW">
                                                <span>ФИО получателя</span>
                                                <span class="data-section-row_value__OkqbL data-section-row_empty__LHAq3">{{ user_data.first_name ?? 'Не указан' }} {{ user_data.last_name ?? '' }}</span>
                                            </div>
                                            <div class="data-section-row_data_section_row__qEDdW">
                                                <span>Телефон</span>
                                                <span class="data-section-row_value__OkqbL data-section-row_empty__LHAq3">{{ user_data.phone ?? 'Не указан' }}</span>
                                            </div>
                                            <div class="data-section-row_data_section_row__qEDdW">
                                                <span>Адрес доставки</span>
                                                <span class="data-section-row_value__OkqbL data-section-row_empty__LHAq3">{{ user_data.delivery_street ?? 'Не указан' }}</span>
                                            </div>
                                            <button @click="editLink()"
                                                    class="button_button__FUDeW button_text__g8M_m ui_btn__ZNAnS">
                                                Редактировать
                                            </button>
                                        </div>
                                    </li>
                                </ul>
                                <ul class="section_section__M8xUg">
                                    <li class="section-item_section_item__PrnFC">
                                        <div class="section-item_icon__Ltu7v" style="background:#ff0049">
                                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"
                                                 viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                                 stroke-width="3" stroke-linecap="round" stroke-linejoin="round"
                                                 class="tabler-icon tabler-icon-box ">
                                                <path d="M12 3l8 4.5l0 9l-8 4.5l-8 -4.5l0 -9l8 -4.5"></path>
                                                <path d="M12 12l8 -4.5"></path>
                                                <path d="M12 12l0 9"></path>
                                                <path d="M12 12l-8 -4.5"></path>
                                            </svg>
                                        </div>
                                        <div class="section-item_body__6L6s2">
                                            <div @click="ordersLink()">Заказы</div>
                                        </div>
                                        <div class="section-item_right__dZF4D">
                                            <div class="section-item_count__sNTOa">{{ ordersCount }}</div>
                                            <div class="section-item_chevron__i8kBw">
                                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"
                                                     viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                                     stroke-width="2" stroke-linecap="round"
                                                     stroke-linejoin="round"
                                                     class="tabler-icon tabler-icon-chevron-right ">
                                                    <path d="M9 6l6 6l-6 6"></path>
                                                </svg>
                                            </div>
                                        </div>
                                    </li>
                                    <li class="section-item_section_item__PrnFC">
                                        <div class="section-item_icon__Ltu7v" style="background:#ff385c">
                                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"
                                                 viewBox="0 0 24 24" fill="currentColor" stroke="none"
                                                 class="tabler-icon tabler-icon-heart-filled ">
                                                <path d="M6.979 3.074a6 6 0 0 1 4.988 1.425l.037 .033l.034 -.03a6 6 0 0 1 4.733 -1.44l.246 .036a6 6 0 0 1 3.364 10.008l-.18 .185l-.048 .041l-7.45 7.379a1 1 0 0 1 -1.313 .082l-.094 -.082l-7.493 -7.422a6 6 0 0 1 3.176 -10.215z"></path>
                                            </svg>
                                        </div>
                                        <div class="section-item_body__6L6s2">
                                            <div @click="ordersFavorite()">Избранное</div>
                                        </div>
                                        <div class="section-item_right__dZF4D">
                                            <div class="section-item_count__sNTOa"></div>
                                            <div class="section-item_chevron__i8kBw">
                                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"
                                                     viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                                     stroke-width="2" stroke-linecap="round"
                                                     stroke-linejoin="round"
                                                     class="tabler-icon tabler-icon-chevron-right ">
                                                    <path d="M9 6l6 6l-6 6"></path>
                                                </svg>
                                            </div>
                                        </div>
                                    </li>
                                    <li class="section-item_section_item__PrnFC">
                                        <div class="section-item_icon__Ltu7v" style="background:#81C45E">
                                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"
                                                 viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"
                                                 stroke-linecap="round" stroke-linejoin="round"
                                                 class="tabler-icon tabler-icon-id ">
                                                <path d="M3 4m0 3a3 3 0 0 1 3 -3h12a3 3 0 0 1 3 3v10a3 3 0 0 1 -3 3h-12a3 3 0 0 1 -3 -3z"></path>
                                                <path d="M9 10m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"></path>
                                                <path d="M15 8l2 0"></path>
                                                <path d="M15 12l2 0"></path>
                                                <path d="M7 16l10 0"></path>
                                            </svg>
                                        </div>
                                        <div class="section-item_body__6L6s2">
                                            <div>Предзаказ</div>
                                        </div>
                                        <div class="section-item_right__dZF4D">
                                            <div class="section-item_count__sNTOa"></div>
                                            <div class="section-item_chevron__i8kBw">
                                                <label class="split_switch__w2miW">
                                                    <input type="checkbox"
                                                           :checked="user_data.preorder"
                                                           @change="togglePreorder">
                                                    <span class="split_background__irQnz">
                                                    <div class="split_handle__R3ALi"></div>
                                                    </span>
                                                </label>
                                            </div>
                                        </div>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>