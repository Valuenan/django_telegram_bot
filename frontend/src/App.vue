<template>
    <div id="app">
        <div v-if="isInitialized">
            <router-view />
            <Navbar />
        </div>
        <div v-else>Загрузка системы...</div>
  </div>
</template>

<script>
import Navbar from './components/Navbar.vue'
import api from './api';

export default {
    name: 'App',
    components: { Navbar },
    data() {
        return {
            isInitialized: false
        }
    },
    async mounted() {
        const tg = window.Telegram?.WebApp;
        tg?.ready();
        tg?.expand();

        await this.ensureAuth();
        this.isInitialized = true;
    },
    methods: {
        async ensureAuth() {
            const token = localStorage.getItem('access_token');
            if (token) return true;

            const initData = window.Telegram?.WebApp?.initData;
            if (!initData) return false;

            try {
                const response = await api.post('api/auth/telegram/', {
                    initData: initData
                });

                if (response.status === 200) {
                    const data = response.data;
                    localStorage.setItem('access_token', data.access);
                    localStorage.setItem('refresh_token', data.refresh);
                    return true;
                }
            } catch (e) {
                console.error("Auth error:", e);
                return false;
            }
            return false;
        }
    }
}
</script>