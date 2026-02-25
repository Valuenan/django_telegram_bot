import axios from 'axios';

const api = axios.create({
    baseURL: (import.meta.env.VITE_API_URL || '').trim(),
    headers: {
        'Content-Type': 'application/json',
        'cloudflare-skip-browser-warning': 'true',
    }
});

api.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
}, (error) => Promise.reject(error));

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        if (originalRequest.url.includes('auth/telegram') || originalRequest.url.includes('token/refresh')) {
            return Promise.reject(error);
        }

        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            try {
                const refreshToken = localStorage.getItem('refresh_token');
                if (!refreshToken) throw new Error("No refresh token");

                const { data } = await axios.post(`${import.meta.env.VITE_API_URL}/api/token/refresh/`, {
                    refresh: refreshToken
                });

                localStorage.setItem('access_token', data.access);
                if (data.refresh) localStorage.setItem('refresh_token', data.refresh);

                originalRequest.headers.Authorization = `Bearer ${data.access}`;
                return api(originalRequest);
            } catch (refreshError) {
                console.error("Refresh token expired or invalid");
                localStorage.clear();
                return Promise.reject(refreshError);
            }
        }
        return Promise.reject(error);
    }
);

export default api;