import { defineStore } from 'pinia'
import api from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => {
    const storedUser = localStorage.getItem('user_data')
    return {
      user: storedUser ? JSON.parse(storedUser) : null,
      isAuthenticated: !!localStorage.getItem('access_token'),
    }
  },
  actions: {
    async loginViaTelegram() {
        const tg = window.Telegram?.WebApp;
        const initData = tg?.initData;

        if (!initData) return false;

        try {
            const { data } = await api.post('/api/auth/telegram/', { initData });

            localStorage.setItem('access_token', data.access);
            localStorage.setItem('refresh_token', data.refresh);

            this.isAuthenticated = true;

            await this.fetchUser();
            return true;
        } catch (error) {
            console.error('Ошибка входа через Telegram:', error);
            this.logout();
            return false;
        }
    },

    async fetchUser() {
      try {
        const { data } = await api.get('/api/profile/me/');
        this.user = data;
        localStorage.setItem('user_data', JSON.stringify(data));
      } catch (error) {
        console.error('Не удалось загрузить данные пользователя', error);
        if (error.response?.status === 401) this.logout();
      }
    },

    logout() {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user_data');
      this.user = null;
      this.isAuthenticated = false;
    }
  }
})