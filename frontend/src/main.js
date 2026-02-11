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

if (window.Telegram?.WebApp) {
    window.Telegram.WebApp.ready(); // Сообщаем, что WebApp готов
    window.Telegram.WebApp.expand(); // Делоем окно по всей высоте
}


app.use(router)
app.use(pinia)

const authStore = useAuthStore()
authStore.setCsrfToken()

app.mount('#app')

export default app







