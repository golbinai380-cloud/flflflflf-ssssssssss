/**
 * Конфигурация приложения
 */

const AppConfig = {
    // API - АВТОМАТИЧЕСКИ ОПРЕДЕЛЯЕТСЯ ПО ДОМЕНУ
    API_BASE_URL: (() => {
        const hostname = window.location.hostname;
        const port = window.location.port;
        const protocol = window.location.protocol;

        // Для production домена darkshop.live
        if (hostname === 'darkshop.live' || hostname === 'www.darkshop.live') {
            // Если уже есть порт в URL, используем его
            if (port && port !== '80' && port !== '443') {
                return `${protocol}//${hostname}:${port}`;
            }
            // Иначе используем стандартный протокол без порта
            return `${protocol}//${hostname}`;
        }

        // Для localhost разработки
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return 'http://localhost:8000';
        }

        // Для других доменов - используем текущий URL
        if (port && port !== '80' && port !== '443') {
            return `${protocol}//${hostname}:${port}`;
        }
        return `${protocol}//${hostname}`;
    })(),

    API_TIMEOUT: 10000,

    // Feature flags
    FEATURES: {
        GIFT_TRANSFER: true,
        AUTO_CONVERSION: true,
        ANALYTICS: true,
        ADMIN_PANEL: false,  // Для админов
        REFERRAL_SYSTEM: false  // В разработке
    },

    // Балансы и лимиты
    LIMITS: {
        MIN_TRANSFER: 1,
        MAX_TRANSFER: 100,
        AUTO_REPLENISH_THRESHOLD: 10,  // Автопополнение при балансе < 10 звёзд
        COMMISSION_PERCENT: 10  // 10% комиссия при передаче
    },

    // UI
    UI: {
        ANIMATION_DURATION: 300,
        TOAST_DURATION: 3000,
        PAGE_TRANSITION_DURATION: 500
    },

    // Логирование
    LOGGING: {
        ENABLED: true,
        LEVEL: 'info'  // debug, info, warn, error
    },

    // Helper функция для API endpoints
    getApiUrl: function (endpoint) {
        // Если endpoint начинается с /market/, заменяем на /api/market/
        if (endpoint.startsWith('/market/') && !endpoint.includes('.tgs') && !endpoint.includes('.json') && !endpoint.includes('Stic/')) {
            return endpoint.replace('/market/', '/api/market/');
        }
        return endpoint;
    }
};

// Инициализация конфигурации
(function initConfig() {
    // Проверяем окружение
    const isDev = !window.location.hostname || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

    if (isDev) {
        console.log('🔧 Режим разработки');
        AppConfig.LOGGING.LEVEL = 'debug';
    } else {
        console.log('🚀 Режим production');
        console.log(`📡 API: ${AppConfig.API_BASE_URL}`);
    }

    // Сохраняем конфиг в глобальное пространство
    window.AppConfig = AppConfig;
})();

// Экспортируем для ES6 модулей (если используются)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AppConfig;
}

// Для обратной совместимости
if (typeof exports !== 'undefined') {
    exports.AppConfig = AppConfig;
}
