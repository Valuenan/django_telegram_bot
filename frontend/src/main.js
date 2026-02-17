import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import axios from 'axios'
import { useAuthStore } from './users/auth'

import "./static/css/style_1.css"
import "./static/css/style_2.css"
import "./static/css/style_3.css"


const app = createApp(App)
const pinia = createPinia()

app.use(pinia) // Сначала подключаем пинию
app.use(router)

const authStore = useAuthStore()

authStore.setCsrfToken().then(() => {
    if (window.Telegram?.WebApp?.initData) {
        authStore.loginViaTelegram();
    }
});

app.mount('#app')






