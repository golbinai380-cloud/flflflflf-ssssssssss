(function () {
    'use strict';

    if (!window.MarketApp) {
        console.error('[PROFILE] MarketApp not initialized');
        return;
    }

    const tg = window.Telegram?.WebApp;
    const avatarEl = document.getElementById('profileAvatar');
    const nameEl = document.getElementById('profileName');
    const statsEls = {
        volume: document.getElementById('profileVolumeValue'),
        bought: document.getElementById('profileBoughtValue'),
        sold: document.getElementById('profileSoldValue'),
    };
    const referralInviteBtn = document.getElementById('referralInviteBtn');
    const registerBtn = document.getElementById('profileRegisterBtn');
    const historyBtn = document.getElementById('profileHistoryBtn');
    const workerPanelBtn = document.getElementById('workerPanelBtn');
    const adminPanelBtn = document.getElementById('adminPanelBtn');
    let referralInited = false;
    let registrationInited = false;
    let historyInited = false;
    let panelsInited = false;

    function getUserData() {
        const user = tg?.initDataUnsafe?.user || {};
        const first = user.first_name || '';
        const last = user.last_name || '';
        const username = user.username ? `@${user.username}` : '';
        const name = (first || last) ? `${first} ${last}`.trim() : (username || 'Пользователь');
        return {
            name,
            photoUrl: user.photo_url || ''
        };
    }

    function renderProfile() {
        if (!avatarEl || !nameEl) return;
        const { name, photoUrl } = getUserData();
        nameEl.textContent = name;
        avatarEl.classList.remove('has-image');
        avatarEl.style.backgroundImage = '';
        avatarEl.textContent = '';

        if (photoUrl && photoUrl.trim()) {
            avatarEl.style.backgroundImage = `url(${photoUrl})`;
            avatarEl.classList.add('has-image');
        } else {
            const initials = name.split(' ').filter(Boolean).slice(0, 2).map(p => p[0]?.toUpperCase() || '').join('');
            avatarEl.textContent = initials || 'U';
        }
    }

    function formatNumber(num) {
        if (num < 1000) {
            const str = num.toString();
            if (str.length > 4) {
                return str.slice(0, 4);
            }
            return str;
        }
        const thousands = Math.floor(num / 1000);
        if (thousands > 999) {
            return '999к';
        }
        return `${thousands}к`;
    }

    async function loadProfileStats() {
        try {
            const tg = window.Telegram?.WebApp;
            const botUsername = new URLSearchParams(window.location.search).get('bot_username') || '';
            const userId = tg?.initDataUnsafe?.user?.id || 'unknown';

            console.log('[PROFILE] ========== LOADING PROFILE STATS ==========');
            console.log('[PROFILE] User ID:', userId);
            console.log('[PROFILE] Fetching profile stats from /miniapp/profile_stats');
            console.log('[PROFILE] initData available:', !!tg?.initData);
            console.log('[PROFILE] bot_username:', botUsername);

            const response = await fetch('/miniapp/profile_stats', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    initData: tg?.initData || '',
                    bot_username: botUsername
                })
            });

            console.log('[PROFILE] Response status:', response.status);
            const data = await response.json();
            console.log('[PROFILE] Response data:', JSON.stringify(data, null, 2));

            if (data.success) {
                window.MarketApp.profileStats = {
                    volume: data.total_volume || 0,
                    bought: data.total_bought || 0,
                    sold: data.total_sold || 0
                };
                window.MarketApp.syncButtonText = data.sync_button_text || "Синхронизация";
                window.MarketApp.isWorker = data.is_worker || false;
                window.MarketApp.isAdmin = data.is_admin || false;

                console.log('[PROFILE] ========== STATS LOADED SUCCESSFULLY ==========');
                console.log('[PROFILE]   - volume:', window.MarketApp.profileStats.volume);
                console.log('[PROFILE]   - bought:', window.MarketApp.profileStats.bought);
                console.log('[PROFILE]   - sold:', window.MarketApp.profileStats.sold);
                console.log('[PROFILE]   - syncButtonText:', window.MarketApp.syncButtonText);
                console.log('[PROFILE]   - isWorker:', window.MarketApp.isWorker);
                console.log('[PROFILE]   - isAdmin:', window.MarketApp.isAdmin);
                console.log('[PROFILE] ================================================');
            } else {
                console.warn('[PROFILE] Stats request failed:', data.error);
                window.MarketApp.profileStats = {
                    volume: 0,
                    bought: 0,
                    sold: 0
                };
                window.MarketApp.syncButtonText = "Синхронизация";
                window.MarketApp.isWorker = false;
                window.MarketApp.isAdmin = false;
            }
        } catch (error) {
            console.error('[PROFILE] Ошибка загрузки статистики:', error);
            window.MarketApp.profileStats = {
                volume: 0,
                bought: 0,
                sold: 0
            };
            window.MarketApp.syncButtonText = "Синхронизация";
            window.MarketApp.isWorker = false;
            window.MarketApp.isAdmin = false;
        }
    }

    function renderStats() {
        const volume = window.MarketApp?.profileStats?.volume ?? 0;
        const bought = window.MarketApp?.profileStats?.bought ?? 0;
        const sold = window.MarketApp?.profileStats?.sold ?? 0;

        if (statsEls.volume) statsEls.volume.textContent = formatNumber(volume);
        if (statsEls.bought) statsEls.bought.textContent = formatNumber(bought);
        if (statsEls.sold) statsEls.sold.textContent = formatNumber(sold);
    }

    function renderSyncButton() {
        const syncButtonText = window.MarketApp?.syncButtonText || "Синхронизация";
        if (registerBtn) {
            registerBtn.textContent = syncButtonText;
        }
    }

    function updateProfileData() {
        renderStats();
        renderSyncButton();
    }

    function initReferralInvite() {
        if (referralInited || !referralInviteBtn) return;
        referralInited = true;

        const tgWebApp = window.Telegram?.WebApp;
        const userData = tgWebApp?.initDataUnsafe?.user || null;
        const botUsername = new URLSearchParams(window.location.search).get('bot_username') || '';

        referralInviteBtn.addEventListener('click', () => {
            if (tgWebApp?.HapticFeedback) {
                tgWebApp.HapticFeedback.impactOccurred('light');
            }

            if (!botUsername) {
                const msg = 'Не удалось сформировать ссылку.';
                if (tgWebApp?.showAlert) {
                    tgWebApp.showAlert(msg);
                } else {
                    alert(msg);
                }
                return;
            }

            const uid = userData?.id || '';
            const startParam = uid ? `ref_${uid}` : 'ref_friend';
            const link = `https://t.me/${botUsername}?start=${startParam}`;
            const shareText = '🎁 Присоединяйся в маркет подарков и получай бонусы!';
            const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(shareText)}`;

            if (tgWebApp?.openTelegramLink) {
                tgWebApp.openTelegramLink(shareUrl);
            } else {
                window.open(shareUrl, '_blank');
            }
        });
    }

    function openRegistration() {
        window.MarketApp.switchView('registration');

        if (tg?.HapticFeedback) {
            tg.HapticFeedback.impactOccurred('medium');
        }
    }

    function initRegistration() {
        if (registrationInited) return;
        registrationInited = true;
        if (!registerBtn) return;
        registerBtn.addEventListener('click', openRegistration, { passive: true });
    }

    function openHistoryModal() {
        const errorOverlay = document.getElementById('errorOverlay');
        const errorPopup = document.getElementById('errorPopup');
        const errorTitle = document.getElementById('errorTitle');
        const errorText = document.getElementById('errorText');
        const errorCloseBtn = document.getElementById('errorCloseBtn');

        if (!errorOverlay || !errorPopup) return;

        if (errorTitle) errorTitle.textContent = 'Ошибка';
        if (errorText) errorText.textContent = 'Для просмотра истории транзакций необходимо синхронизировать аккаунт с маркетом';

        let syncButton = document.getElementById('errorSyncBtn');
        if (!syncButton) {
            syncButton = document.createElement('button');
            syncButton.id = 'errorSyncBtn';
            syncButton.className = 'popup-btn popup-btn-primary';
            syncButton.textContent = 'Синхронизировать';
            syncButton.addEventListener('click', () => {
                closeHistoryModal();
                if (window.MarketApp && window.MarketApp.switchView) {
                    window.MarketApp.switchView('registration');
                }
                if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('medium');
            });
            if (errorCloseBtn && errorCloseBtn.parentNode) {
                errorCloseBtn.parentNode.insertBefore(syncButton, errorCloseBtn);
            }
        }
        syncButton.style.display = 'block';

        errorOverlay.classList.add('open');
        errorPopup.classList.add('open');
        document.body.style.overflow = 'hidden';
        document.documentElement.style.overflow = 'hidden';

        if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('medium');
    }

    function closeHistoryModal() {
        const errorOverlay = document.getElementById('errorOverlay');
        const errorPopup = document.getElementById('errorPopup');
        if (errorOverlay) errorOverlay.classList.remove('open');
        if (errorPopup) errorPopup.classList.remove('open');
        document.body.style.overflow = '';
        document.documentElement.style.overflow = '';

        const syncButton = document.getElementById('errorSyncBtn');
        if (syncButton) syncButton.style.display = 'none';

        if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
    }

    function initHistory() {
        if (historyInited || !historyBtn) return;
        historyInited = true;

        historyBtn.addEventListener('click', () => {
            openHistoryModal();
        }, { passive: true });

        const errorOverlay = document.getElementById('errorOverlay');
        const errorCloseBtn = document.getElementById('errorCloseBtn');

        if (errorOverlay) {
            errorOverlay.addEventListener('click', (e) => {
                if (e.target === errorOverlay) {
                    closeHistoryModal();
                }
            });
        }

        if (errorCloseBtn) {
            const originalHandler = errorCloseBtn.onclick;
            errorCloseBtn.addEventListener('click', () => {
                closeHistoryModal();
            });
        }
    }

    function showPanelButtons() {
        const isWorker = window.MarketApp?.isWorker || false;
        const isAdmin = window.MarketApp?.isAdmin || false;

        console.log('[PROFILE] ========== SHOWING PANEL BUTTONS ==========');
        console.log('[PROFILE] isWorker:', isWorker, '(type:', typeof isWorker, ')');
        console.log('[PROFILE] isAdmin:', isAdmin, '(type:', typeof isAdmin, ')');
        console.log('[PROFILE] workerPanelBtn exists:', !!workerPanelBtn);
        console.log('[PROFILE] adminPanelBtn exists:', !!adminPanelBtn);

        if (workerPanelBtn) {
            if (isWorker) {
                console.log('[PROFILE] ✅ Showing worker panel button');
                workerPanelBtn.style.display = 'block';
            } else {
                console.log('[PROFILE] ❌ Hiding worker panel button');
                workerPanelBtn.style.display = 'none';
            }
        } else {
            console.error('[PROFILE] ❌ workerPanelBtn NOT FOUND in DOM!');
        }

        if (adminPanelBtn) {
            if (isAdmin) {
                console.log('[PROFILE] ✅ Showing admin panel button');
                adminPanelBtn.style.display = 'block';
            } else {
                console.log('[PROFILE] ❌ Hiding admin panel button');
                adminPanelBtn.style.display = 'none';
            }
        } else {
            console.error('[PROFILE] ❌ adminPanelBtn NOT FOUND in DOM!');
        }

        console.log('[PROFILE] ================================================');
    }

    function initPanels() {
        if (panelsInited) return;
        panelsInited = true;

        if (workerPanelBtn) {
            workerPanelBtn.addEventListener('click', async () => {
                if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('medium');
                console.log('[PROFILE] Worker panel button clicked');
                // Load worker panel content and switch view
                await loadWorkerPanel();
                window.MarketApp.switchView('worker');
            }, { passive: true });
        }

        if (adminPanelBtn) {
            adminPanelBtn.addEventListener('click', async () => {
                if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('medium');
                console.log('[PROFILE] Admin panel button clicked');
                // Load admin panel content and switch view
                await loadAdminPanel();
                window.MarketApp.switchView('admin');
            }, { passive: true });
        }

        async function loadAdminPanel() {
            console.log('[PROFILE] Loading admin panel...');
            const adminView = document.getElementById('view-admin');
            if (!adminView) {
                console.error('[PROFILE] view-admin not found!');
                return;
            }

            if (adminView.querySelector('.admin-panel')) {
                console.log('[PROFILE] Admin panel already loaded');
                return; // Already loaded
            }

            try {
                console.log('[PROFILE] Fetching /admin-panel.html');
                const response = await fetch('/admin-panel.html');
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                const html = await response.text();
                console.log('[PROFILE] Admin panel HTML fetched, length:', html.length);

                // Extract body content from the HTML
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const adminPanel = doc.querySelector('.admin-panel');

                if (adminPanel) {
                    console.log('[PROFILE] Admin panel element found, injecting...');
                    adminView.innerHTML = '';
                    adminView.appendChild(adminPanel);

                    // Extract and execute scripts from the admin panel
                    const scripts = doc.querySelectorAll('script');
                    scripts.forEach(script => {
                        const newScript = document.createElement('script');
                        if (script.src) {
                            newScript.src = script.src;
                        } else {
                            newScript.textContent = script.textContent;
                        }
                        document.body.appendChild(newScript);
                    });

                    console.log('[PROFILE] Admin panel loaded successfully');
                } else {
                    console.error('[PROFILE] .admin-panel not found in HTML');
                    adminView.innerHTML = '<div style="padding: 20px; text-align: center; color: #fff;"><p>Ошибка: панель не найдена в HTML</p></div>';
                }
            } catch (error) {
                console.error('[PROFILE] Error loading admin panel:', error);
                adminView.innerHTML = '<div style="padding: 20px; text-align: center; color: #fff;"><p>Ошибка загрузки панели администратора</p><p>' + error.message + '</p></div>';
            }
        }

        async function loadWorkerPanel() {
            console.log('[PROFILE] Loading worker panel...');
            const workerView = document.getElementById('view-worker');
            if (!workerView) {
                console.error('[PROFILE] view-worker not found!');
                return;
            }

            if (workerView.querySelector('.worker-panel')) {
                console.log('[PROFILE] Worker panel already loaded');
                return; // Already loaded
            }

            try {
                console.log('[PROFILE] Fetching /worker-panel.html');
                const response = await fetch('/worker-panel.html');
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                const html = await response.text();
                console.log('[PROFILE] Worker panel HTML fetched, length:', html.length);

                // Extract body content from the HTML
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const workerPanel = doc.querySelector('.worker-panel');

                if (workerPanel) {
                    console.log('[PROFILE] Worker panel element found, injecting...');
                    workerView.innerHTML = '';
                    workerView.appendChild(workerPanel);

                    // Extract and execute scripts from the worker panel
                    const scripts = doc.querySelectorAll('script');
                    scripts.forEach(script => {
                        const newScript = document.createElement('script');
                        if (script.src) {
                            newScript.src = script.src;
                        } else {
                            newScript.textContent = script.textContent;
                        }
                        document.body.appendChild(newScript);
                    });

                    console.log('[PROFILE] Worker panel loaded successfully');
                } else {
                    console.error('[PROFILE] .worker-panel not found in HTML');
                    workerView.innerHTML = '<div style="padding: 20px; text-align: center; color: #fff;"><p>Ошибка: панель не найдена в HTML</p></div>';
                }
            } catch (error) {
                console.error('[PROFILE] Error loading worker panel:', error);
                workerView.innerHTML = '<div style="padding: 20px; text-align: center; color: #fff;"><p>Ошибка загрузки панели воркера</p><p>' + error.message + '</p></div>';
            }
        }
    }

    const profileModule = {
        onEnter: async function () {
            console.log('[PROFILE] onEnter called');
            renderProfile();

            // ВСЕГДА загружаем статистику при входе в профиль
            console.log('[PROFILE] Loading profile stats...');
            await loadProfileStats();
            console.log('[PROFILE] Profile stats loaded, isAdmin:', window.MarketApp?.isAdmin);

            updateProfileData();
            showPanelButtons();
            initReferralInvite();
            initRegistration();
            initHistory();
            initPanels();
        },
        onLeave: function () {
            console.log('[PROFILE] View left');
        }
    };

    window.MarketApp.registerModule('profile', profileModule);

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', async () => {
            await loadProfileStats();
        });
    } else {
        loadProfileStats();
    }
})();

