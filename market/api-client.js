/**
 * API Client для взаимодействия с бэкендом
 */

class APIClient {
    constructor(baseURL) {
        // Используем переданный baseURL или берем из AppConfig
        this.baseURL = baseURL || (window.AppConfig ? window.AppConfig.API_BASE_URL : 'http://localhost:8000');
        this.token = localStorage.getItem('tg_token');

        console.log('🔌 API Client инициализирован:', this.baseURL);
    }

    /**
     * Отправляет запрос к API
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (this.token && !endpoint.includes('/auth/')) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                if (response.status === 401) {
                    // Токен истек, требуется переавторизация
                    this.clearToken();
                    window.location.reload();
                }
                throw new Error(`HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    /**
     * Методы авторизации
     */
    async authenticateTelegramWebApp(initData) {
        const response = await this.request('/api/auth/telegram-web-app', {
            method: 'POST',
            body: JSON.stringify({ initData })
        });

        if (response.status === 'success') {
            this.setToken(response.token);
            return response;
        }

        throw new Error('Authentication failed');
    }

    async validateSession(token) {
        return this.request(`/api/auth/validate-session?token=${token}`, {
            method: 'GET'
        });
    }

    setToken(token) {
        this.token = token;
        localStorage.setItem('tg_token', token);
    }

    clearToken() {
        this.token = null;
        localStorage.removeItem('tg_token');
    }

    /**
     * Методы управления подарками
     */
    async getUserInventory() {
        return this.request(`/api/gifts/inventory?token=${this.token}`, {
            method: 'GET'
        });
    }

    async transferGift(toUserId, giftId, quantity = 1) {
        return this.request(`/api/gifts/transfer?token=${this.token}`, {
            method: 'POST',
            body: JSON.stringify({
                to_user_id: toUserId,
                gift_id: giftId,
                quantity: quantity
            })
        });
    }

    async autoConvertGifts() {
        return this.request(`/api/gifts/auto-convert?token=${this.token}`, {
            method: 'POST'
        });
    }

    /**
     * Методы аналитики
     */
    async getAnalyticsReport(category = null) {
        let url = '/api/analytics/report';
        if (category) {
            url += `?category=${category}`;
        }
        return this.request(url, { method: 'GET' });
    }

    async getLogs(category = null, limit = 100) {
        let url = `/api/analytics/logs?limit=${limit}`;
        if (category) {
            url += `&category=${category}`;
        }
        return this.request(url, { method: 'GET' });
    }

    /**
     * Проверка здоровья API
     */
    async healthCheck() {
        return this.request('/api/health', { method: 'GET' });
    }
}

// Создаем глобальный экземпляр ПОСЛЕ загрузки AppConfig
// Используем setTimeout чтобы дать AppConfig время на инициализацию
if (typeof window !== 'undefined') {
    // Если AppConfig уже загружен, создаем сразу
    if (window.AppConfig) {
        window.api = new APIClient();
        console.log('✅ API Client создан с AppConfig');
    } else {
        // Иначе ждем немного
        setTimeout(() => {
            window.api = new APIClient();
            console.log('✅ API Client создан (отложенная инициализация)');
        }, 100);
    }
}
