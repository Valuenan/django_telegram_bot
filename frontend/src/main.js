import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './users/auth'

import "./static/css/style_1.css"
import "./static/css/style_2.css"
import "./static/css/style_3.css"

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

const authStore = useAuthStore()

if (window.Telegram?.WebApp?.initData) {
    authStore.loginViaTelegram().then((success) => {
        if (success) {
            console.log("Авторизация через Telegram успешна");
        }
    });
}

app.mount('#app')






