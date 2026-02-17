<script>
import { ref, onMounted } from 'vue'
import { useAuthStore, getCSRFToken } from '../users/auth.js'
import { useRouter } from 'vue-router'

export default {
    name: 'EditProfileView',
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
            baseUrl: import.meta.env.VITE_API_URL
        }
    },

    async mounted() {
        await this.fetchProfile();
    },

    methods: {
        async fetchProfile() {
            try {
                const tgUser = this.tg?.initDataUnsafe?.user;
                this.user_id = tgUser?.id

                const response = await fetch(`${this.baseUrl}/api/profile/${this.user_id}/`, {
                    headers: {
                        'X-CSRFToken': getCSRFToken(),
                    }
                });

                if (response.ok) {
                    this.user_data = await response.json();
                }
            } catch (error) {
                console.error("Ошибка загрузки профиля:", error);
            }
        },

        async updateProfile() {
            try {
                const payload = {
                    chat_id: this.user_id,
                    first_name: this.user_data.first_name,
                    last_name: this.user_data.last_name,
                    phone: this.user_data.phone,
                    delivery_street: this.user_data.delivery_street,
                };

                const response = await fetch(`${this.baseUrl}/api/profile/update/`, {
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
                    this.user_data = data;
                    this.router.push('/profile/');
                } else {
                    const errorData = await response.json();
                    console.error("Ошибка сервера:", errorData);
                }
            } catch (error) {
                console.error("Ошибка сети:", error);
            }
        }
    }
}
</script>

<template>
    <div class="telegram-app_telegram_app__6iz4V">
        <div class="stack-navigation_screen___5WKf screen-0.5879402681886656">
            <div class="profile-delivery-screen_profile_delivery_page__s4W5a">
                <h1>Данные доставки</h1>
                <h2>Данные получателя</h2>
                <div :class="{ 'input_empty__GAE30': !user_data.first_name && !user_data.last_name }"
                     class="input_input__3nfmj">
                    <label class="input_label__vwXZk">Имя, фамилия</label>
                    <input v-model="user_data.first_name" type="text">
                    <input v-model="user_data.last_name" type="text">
                </div>
                <div
                        class="phone-input_input__Wrfm6"
                        :class="{ 'input_empty__GAE30': !user_data.phone }"
                >
                    <label class="phone-input_label__0TZe9">Телефон</label>
                    <div class="phone-input_phone_number_container__yjkC7 react-tel-input ">
                        <input class="form-control " placeholder="+7 (999) 999 99 99" type="number"
                               v-model="user_data.phone">
                        <div class="flag-dropdown ">
                            <div class="selected-flag" title="Russia: + 7" tabindex="0" role="button"
                                 aria-haspopup="listbox">
                                <div class="flag ru">
                                    <div class="arrow"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div
                        class="input_input__3nfmj"
                        :class="{ 'input_empty__GAE30': !user_data.delivery_street }"
                >
                    <label class="input_label__vwXZk">Адрес доставки</label>
                    <!-- Используем v-model для мгновенной связи данных -->
                    <input
                            type="text"
                            v-model="user_data.delivery_street"
                    >
                </div>
                <div data-v-5bff6dd4="" id="observer-point" style="height: 10px;"></div>
                <div>
                    <button @click="updateProfile()" class="button_button__FUDeW button_primary__G81VK">Сохранить</button>
                </div>
            </div>
        </div>
    </div>
</template>
