import { defineStore } from 'pinia'
import api from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => {
    const storedState = localStorage.getItem('authState')
    return storedState ? JSON.parse(storedState) : {
      user: null,
      isAuthenticated: false,
    }
  },
  actions: {
    // 1. Вход через Telegram
    async loginViaTelegram() {
        const tg = window.Telegram?.WebApp;
        if (tg?.initData) {
            try {
                const response = await api.get('/user/', {
                    headers: {
                        'Authorization': `twa ${tg.initData}`
                    }
                });

                this.user = response.data;
                this.isAuthenticated = true;
                this.saveState();
            } catch (error) {
                console.error('Ошибка входа:', error);
            }
        }
    },

    // 2. Установка CSRF
    async setCsrfToken() {
      try {
        // Относительный путь
        await api.get('/set-csrf-token/');
      } catch (e) {
        console.error("CSRF Error", e);
      }
    },

    // 3. Получение данных профиля
    async fetchUser() {
      try {
        const response = await api.get('/user/', {
          headers: { 'X-CSRFToken': getCSRFToken() }
        });
        this.user = response.data;
        this.isAuthenticated = true;
      } catch (error) {
        console.error('Failed to fetch user', error);
        this.user = null;
        this.isAuthenticated = false;
      }
      this.saveState();
    },

    // 4. Выход
    async logout(router = null) {
      try {
        await api.post('/logout', {}, {
          headers: { 'X-CSRFToken': getCSRFToken() }
        });
        this.user = null;
        this.isAuthenticated = false;
        this.saveState();
        if (router) await router.push({ name: 'login' });
      } catch (error) {
        console.error('Logout failed', error);
      }
    },

    saveState() {
      localStorage.setItem('authState', JSON.stringify({
        user: this.user,
        isAuthenticated: this.isAuthenticated,
      }));
    },
  },
})

export function getCSRFToken() {
  const name = 'csrftoken'
  let cookieValue = null
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';')
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim()
      if (cookie.substring(0, name.length + 1) === name + '=') {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
        break
      }
    }
  }
  return cookieValue;
}