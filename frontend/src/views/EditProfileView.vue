<template>
    <div class="telegram-app_telegram_app__6iz4V">
        <div class="stack-navigation_screen___5WKf screen-0.5879402681886656">
            <div class="profile-delivery-screen_profile_delivery_page__s4W5a">
                <h1>Данные доставки</h1>
                <h2>Данные получателя</h2>
                <div :class="{ 'input_empty__GAE30': !user.user_data.first_name && !user.user_data.last_name }"
                     class="input_input__3nfmj">
                    <label class="input_label__vwXZk">Имя, фамилия</label>
                    <input v-model="user.user_data.first_name" type="text">
                    <input v-model="user.user_data.last_name" type="text">
                </div>
                <div
                        class="phone-input_input__Wrfm6"
                        :class="{ 'input_empty__GAE30': !user.user_data.phone }"
                >
                    <label class="phone-input_label__0TZe9">Телефон</label>
                    <div class="phone-input_phone_number_container__yjkC7 react-tel-input ">
                        <input class="form-control " placeholder="+7 (999) 999 99 99" type="number"
                               v-model="user.user_data.phone">
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
                        :class="{ 'input_empty__GAE30': !user.user_data.delivery_street }"
                >
                    <label class="input_label__vwXZk">Адрес доставки</label>
                    <!-- Используем v-model для мгновенной связи данных -->
                    <input
                            type="text"
                            v-model="user.user_data.delivery_street"
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


<script>
import { useAuthStore, getCSRFToken } from '../users/auth.js'
import { useRouter } from 'vue-router'

import jsonData from '../response.json' // Import the data


export default {
    name: 'EditProfileView',
    data() {
        return {
            user: {
                    user_id: '',
                    user_data: []
                },
            totalCount: 0,
            totalSum: 0,
        }
    },

    async mounted() {
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

                const response = await fetch(`http://localhost:8000/api/profile/${this.user.user_id}`)
                this.user.user_data = await response.json()
                console.log(this.user)

              } catch (error) {
                console.log(error);
            }
        },

        async updateProfile() {
            try {
                const payload = {
                    chat_id: this.user.user_id,
                    first_name: this.user.user_data.first_name,
                    last_name: this.user.user_data.last_name,
                    phone: this.user.user_data.phone,
                    delivery_street: this.user.user_data.delivery_street,
                };

                const response = await fetch('http://localhost:8000/api/profile/update/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken(),
                    },
                    body: JSON.stringify(payload),
                    credentials: 'include',
                });

                const data = await response.json();
                if (response.ok) {
                    this.user.user_data = data;
                    this.$router.push({
                        path: '/profile',
                    });
                    console.log("Профиль обновлен");
                } else {
                    console.error("Ошибка:", data);
                }
            } catch (error) {
                console.error("Ошибка сети:", error);
            }
        }
    }
}
</script>
