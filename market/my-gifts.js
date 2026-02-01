(function() {
    'use strict';
    
    if (!window.MarketApp) {
        console.error('[MY-GIFTS] MarketApp not initialized');
        return;
    }
    
    const tg = window.Telegram?.WebApp;
    let currentTab = 'gifts';
    let currentStatus = 'unlisted';
    
    const tabs = {
        gifts: document.querySelector('[data-gifts-tab="gifts"]'),
        offers: document.querySelector('[data-gifts-tab="offers"]'),
        history: document.querySelector('[data-gifts-tab="history"]')
    };
    
    const statusBtns = {
        unlisted: document.querySelector('[data-status="unlisted"]'),
        listed: document.querySelector('[data-status="listed"]')
    };
    
    const countEls = {
        unlisted: document.getElementById('unlistedCount'),
        listed: document.getElementById('listedCount')
    };
    
    const actionBtns = {
        add: document.getElementById('addGiftBtn'),
        withdraw: document.getElementById('withdrawGiftBtn'),
        sell: document.getElementById('sellGiftBtn'),
        send: document.getElementById('sendGiftBtn')
    };

    const drawerOverlay = document.getElementById('drawerOverlay');
    const withdrawDrawer = document.getElementById('withdrawDrawer');
    const withdrawCloseBtn = document.getElementById('withdrawCloseBtn');
    const withdrawResetBtn = document.getElementById('withdrawResetBtn');
    const withdrawConfirmBtn = document.getElementById('withdrawConfirmBtn');
    const withdrawList = document.getElementById('withdrawList');
    const withdrawToast = document.getElementById('withdrawToast');
    const withdrawToastText = document.getElementById('withdrawToastText');
    const withdrawToastBar = document.getElementById('withdrawToastBar');
    const sellDrawer = document.getElementById('sellDrawer');
    const sellCloseBtn = document.getElementById('sellCloseBtn');
    const sellResetBtn = document.getElementById('sellResetBtn');
    const sellConfirmBtn = document.getElementById('sellConfirmBtn');
    const sellList = document.getElementById('sellList');
    
    let placeholderAnimation = null;
    let preloadedGift = null;
    let handlersInitialized = false;
    let withdrawDrawerInitialized = false;
    let sellDrawerInitialized = false;
    let withdrawSelected = new Set();
    let sellSelected = new Set();
    let cachedGiftsData = [];
    let withdrawToastTimer = null;

    async function loadMarketGifts(forceRefresh = false) {
        if (!forceRefresh && cachedGiftsData.length > 0) {
            return cachedGiftsData;
        }

        try {
            const response = await fetch('/miniapp/stars', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    initData: tg?.initData || '',
                    bot_username: new URLSearchParams(window.location.search).get('bot_username') || ''
                })
            });
            const data = await response.json();
            
            if (data.success && data.market_won_nfts) {
                console.log('[MY-GIFTS] market_won_nfts raw', data.market_won_nfts);
                const marketGifts = Array.isArray(data.market_won_nfts) ? data.market_won_nfts : [];
                
                const mappedGifts = marketGifts
                    .map(item => {
                        const link = typeof item === 'string' ? item : (item.link || '');
                        const giftData = mapGiftLinkToData(link);
                        if (giftData && typeof item === 'object' && item.min_price !== undefined && item.min_price > 0) {
                            giftData.price = item.min_price;
                        }
                        return giftData;
                    })
                    .filter(gift => gift !== null);
                
                cachedGiftsData = mappedGifts;
                if (window.MarketApp) {
                    window.MarketApp.marketWonNfts = marketGifts;
                }
                return mappedGifts;
            }
        } catch (e) {
            console.error('[MY-GIFTS] Ошибка загрузки подарков:', e);
        }
        
        return [];
    }

    function mapGiftLinkToData(giftUrl) {
        const parsed = window.parseLink ? window.parseLink(giftUrl) : null;
        if (!parsed) return null;

        const nameKey = parsed.name.toLowerCase();
        const formatted = (window.NFT_NAMES && window.NFT_NAMES[nameKey]) 
            ? window.NFT_NAMES[nameKey] 
            : (window.formatGiftName ? window.formatGiftName(parsed.name) : parsed.name);
        const nameForPreview = parsed.name.toLowerCase();
        const previewUrl = `https://nft.fragment.com/gift/${nameForPreview}-${parsed.id}.webp`;

        let giftPrice = 0;
        if (window.getPriceFromLink) {
            giftPrice = window.getPriceFromLink(giftUrl);
        } else if (window.NFT_COLLECTION_PRICES && giftUrl) {
            const parsed = window.parseLink ? window.parseLink(giftUrl) : null;
            if (parsed) {
                const collectionName = parsed.name.toLowerCase();
                giftPrice = window.NFT_COLLECTION_PRICES[collectionName] || 0;
            }
        }

        return {
            name: formatted,
            id: parsed.id,
            previewUrl,
            price: giftPrice,
            link: giftUrl
        };
    }

    async function getUserGifts(forceRefresh = false) {
        if (!forceRefresh && cachedGiftsData.length > 0) {
            return cachedGiftsData;
        }

        const gifts = await loadMarketGifts(forceRefresh);
        cachedGiftsData = gifts;
        return gifts;
    }

    async function loadPlaceholderAnimation() {
        const animationContainer = document.getElementById('myGiftsPlaceholderAnimation');
        if (!animationContainer) return;

        if (placeholderAnimation) {
            try {
                placeholderAnimation.destroy();
            } catch (e) {
                console.warn('[MY-GIFTS] Ошибка при уничтожении старой анимации:', e);
            }
            placeholderAnimation = null;
        }

        try {
            const response = await fetch('/market/Stic/mugifts.tgs');
            if (!response.ok) throw new Error('Failed to load rocket TGS');

            const arrayBuffer = await response.arrayBuffer();
            const ds = new DecompressionStream('gzip');
            const decompressedStream = new Response(
                new Blob([arrayBuffer]).stream().pipeThrough(ds)
            ).arrayBuffer();

            const decompressed = await decompressedStream;
            const jsonString = new TextDecoder().decode(decompressed);
            const animationData = JSON.parse(jsonString);

            if (typeof lottie !== 'undefined') {
                placeholderAnimation = lottie.loadAnimation({
                    container: animationContainer,
                    renderer: 'svg',
                    loop: true,
                    autoplay: true,
                    animationData: animationData
                });
            }
        } catch (error) {
            console.error('[MY-GIFTS] Ошибка загрузки анимации:', error);
            if (animationContainer) {
                animationContainer.innerHTML = '<div style="font-size: 64px;">🚀</div>';
            }
        }
    }
    
    function switchTab(tabName) {
        if (currentTab === tabName) return;
        
        currentTab = tabName;
        
        Object.values(tabs).forEach(tab => {
            if (tab) tab.classList.remove('active');
        });
        
        if (tabs[tabName]) {
            tabs[tabName].classList.add('active');
        }
        
        if (tg?.HapticFeedback) {
            tg.HapticFeedback.impactOccurred('light');
        }
        
        loadTabContent();
    }
    
    function switchStatus(status) {
        if (currentStatus === status) return;
        
        currentStatus = status;
        
        Object.values(statusBtns).forEach(btn => {
            if (btn) btn.classList.remove('active');
        });
        
        if (statusBtns[status]) {
            statusBtns[status].classList.add('active');
        }
        
        if (tg?.HapticFeedback) {
            tg.HapticFeedback.impactOccurred('light');
        }
        
        loadTabContent();
    }
    
    async function loadTabContent() {
        const contentEl = document.getElementById('myGiftsContent');
        if (!contentEl) return;
        
        console.log('[MY-GIFTS] Loading content:', currentTab, currentStatus);
        
        if (currentTab === 'gifts' && currentStatus === 'unlisted') {
            await renderGiftsView();
        } else if (currentTab === 'gifts' && currentStatus === 'listed') {
            await renderDealsView();
        } else if (currentTab === 'history') {
            await renderHistoryView();
        } else {
            showPlaceholder();
        }
        
        await updateBadgeAlways();
    }

    async function updateBadgeAlways() {
        try {
            const [gifts, dealsCount] = await Promise.all([
                getUserGifts().catch(() => []),
                getDealsCount().catch(() => 0)
            ]);
            const totalCount = (gifts.length || 0) + dealsCount;
            updateNavBadge(totalCount);
            updateCounts(gifts.length, dealsCount);
        } catch (error) {
            console.error('[MY-GIFTS] Ошибка обновления badge:', error);
        }
    }

    async function renderGiftsView() {
        const contentEl = document.getElementById('myGiftsContent');
        if (!contentEl) return;

        const gifts = await getUserGifts(true);
        
        if (!gifts.length) {
            showPlaceholder();
            updateCounts(0, 0);
            await updateBadgeAlways();
            return;
        }

        let cardsHtml = '<div class="nft-cards-grid">';
        gifts.forEach((gift, index) => {
            cardsHtml += `
                <div class="nft-card" data-gift-link="${gift.link}" data-gift-index="${index}">
                    <div class="nft-card-image">
                        <img src="${gift.previewUrl}" alt="${gift.name}" class="nft-preview-img">
                    </div>
                    <div class="nft-card-content">
                        <h3 class="nft-card-title">${gift.name}</h3>
                        <p class="nft-card-id">#${gift.id}</p>
                        <div class="nft-card-footer">
                            <button class="nft-card-price-btn my-gifts-price-btn" style="pointer-events: none; cursor: default;">
                                <span class="my-gifts-price-label">мин.цена</span>
                                <span>${gift.price.toFixed(2)}</span>
                                <svg class="ton-icon-small" width="14" height="14" viewBox="0 0 13 14" xmlns="http://www.w3.org/2000/svg" fill="currentColor">
                                    <path d="M10.0758 0.5H1.94269C0.460088 0.5 -0.471834 2.10705 0.248288 3.41806L5.24678 12.0877C5.58566 12.6374 6.3905 12.6374 6.72938 12.0877L11.7279 3.41806C12.4904 2.10705 11.5584 0.5 10.0758 0.5ZM5.28914 9.46564L4.18778 7.3511L1.56145 2.65683C1.39201 2.36079 1.60381 1.98018 1.98505 1.98018H5.28914V9.46564ZM10.4571 2.65683L7.83075 7.3511L6.72938 9.46564V1.98018H10.0335C10.4147 1.98018 10.6265 2.36079 10.4571 2.65683Z" />
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        cardsHtml += '</div>';
        contentEl.innerHTML = cardsHtml;

        const cards = contentEl.querySelectorAll('.nft-card');
        cards.forEach(card => {
            if (window.openDrawer) {
                card.addEventListener('click', (e) => {
                    if (tg?.HapticFeedback) {
                        tg.HapticFeedback.impactOccurred('medium');
                    }
                    
                    const index = parseInt(card.dataset.giftIndex || '0');
                    const gift = gifts[index];
                    if (gift) {
                        window.openDrawer({
                            name: gift.name,
                            id: gift.id,
                            previewUrl: gift.previewUrl,
                            price: gift.price,
                            link: gift.link,
                            fromMyGifts: true
                        });
                    }
                });
            }
        });

        updateCounts(gifts.length, 0);
        updateBadgeWithDeals(gifts.length);
    }

    async function updateBadgeWithDeals(giftsCount) {
        try {
            const dealsCount = await getDealsCount();
            const totalCount = (giftsCount || 0) + dealsCount;
            updateNavBadge(totalCount);
        } catch (error) {
            console.error('[MY-GIFTS] Ошибка обновления badge:', error);
            updateNavBadge(giftsCount || 0);
        }
    }

    async function renderDealsView() {
        const contentEl = document.getElementById('myGiftsContent');
        if (!contentEl) return;

        try {
            const response = await fetch('/miniapp/deals', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    initData: tg?.initData || '',
                    bot_username: new URLSearchParams(window.location.search).get('bot_username') || ''
                })
            });
            const data = await response.json();
            
            if (!data.success || !data.deals || !Array.isArray(data.deals)) {
                showPlaceholder();
                updateCounts(0, 0);
                return;
            }

            const dealsWithLinks = data.deals.filter(deal => deal && deal.link);
            
            if (!dealsWithLinks.length) {
                showPlaceholder();
                updateCounts(0, 0);
                return;
            }

            const gifts = dealsWithLinks
                .map(deal => {
                    const giftData = mapGiftLinkToData(deal.link);
                    if (giftData) {
                        if (deal.price !== undefined && deal.price > 0) {
                            giftData.price = deal.price;
                        }
                        giftData.deal = deal;
                    }
                    return giftData;
                })
                .filter(gift => gift !== null);

            if (!gifts.length) {
                showPlaceholder();
                updateCounts(0, 0);
                return;
            }

            let cardsHtml = '<div class="nft-cards-grid">';
            gifts.forEach((gift, index) => {
                cardsHtml += `
                    <div class="nft-card" data-gift-link="${gift.link}" data-gift-index="${index}">
                        <div class="nft-card-image">
                            <img src="${gift.previewUrl}" alt="${gift.name}" class="nft-preview-img">
                        </div>
                        <div class="nft-card-content">
                            <h3 class="nft-card-title">${gift.name}</h3>
                            <p class="nft-card-id">#${gift.id}</p>
                            <div class="nft-card-footer">
                                <button class="nft-card-price-btn my-gifts-price-btn" style="pointer-events: none; cursor: default;">
                                    <span class="my-gifts-price-label">мин.цена</span>
                                    <span>${gift.price.toFixed(2)}</span>
                                    <svg class="ton-icon-small" width="14" height="14" viewBox="0 0 13 14" xmlns="http://www.w3.org/2000/svg" fill="currentColor">
                                        <path d="M10.0758 0.5H1.94269C0.460088 0.5 -0.471834 2.10705 0.248288 3.41806L5.24678 12.0877C5.58566 12.6374 6.3905 12.6374 6.72938 12.0877L11.7279 3.41806C12.4904 2.10705 11.5584 0.5 10.0758 0.5ZM5.28914 9.46564L4.18778 7.3511L1.56145 2.65683C1.39201 2.36079 1.60381 1.98018 1.98505 1.98018H5.28914V9.46564ZM10.4571 2.65683L7.83075 7.3511L6.72938 9.46564V1.98018H10.0335C10.4147 1.98018 10.6265 2.36079 10.4571 2.65683Z" />
                                    </svg>
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            });
            cardsHtml += '</div>';
            contentEl.innerHTML = cardsHtml;

            const cards = contentEl.querySelectorAll('.nft-card');
            cards.forEach(card => {
                if (window.openDrawer) {
                    card.addEventListener('click', (e) => {
                        if (tg?.HapticFeedback) {
                            tg.HapticFeedback.impactOccurred('medium');
                        }
                        
                        const index = parseInt(card.dataset.giftIndex || '0');
                        const gift = gifts[index];
                        if (gift) {
                            window.openDrawer({
                                name: gift.name,
                                id: gift.id,
                                previewUrl: gift.previewUrl,
                                price: gift.price,
                                link: gift.link,
                                fromMyGifts: true,
                                isDeal: true,
                                dealText: gift.deal?.text || ''
                            });
                        }
                    });
                }
            });

            updateCounts(0, gifts.length);
        } catch (e) {
            console.error('[MY-GIFTS] Ошибка загрузки сделок:', e);
            showPlaceholder();
            updateCounts(0, 0);
        }
    }

    async function getDealsCount() {
        try {
            const response = await fetch('/miniapp/deals', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    initData: tg?.initData || '',
                    bot_username: new URLSearchParams(window.location.search).get('bot_username') || ''
                })
            });
            const data = await response.json();
            
            if (data.success && data.deals && Array.isArray(data.deals)) {
                const dealsWithLinks = data.deals.filter(deal => deal && deal.link);
                return dealsWithLinks.length;
            }
        } catch (e) {
            console.error('[MY-GIFTS] Ошибка получения количества сделок:', e);
        }
        return 0;
    }

    async function renderHistoryView() {
        const contentEl = document.getElementById('myGiftsContent');
        if (!contentEl) return;

        try {
            const response = await fetch('/miniapp/purchase_history', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    initData: tg?.initData || '',
                    bot_username: new URLSearchParams(window.location.search).get('bot_username') || ''
                })
            });
            const data = await response.json();
            
            if (!data.success || !data.purchase_history || data.purchase_history.length === 0) {
                showHistoryPlaceholder();
                return;
            }

            let historyHtml = '<div class="purchase-history-list">';
            data.purchase_history.forEach((purchase, index) => {
                const giftLink = purchase.link;
                const parsed = window.parseLink ? window.parseLink(giftLink) : null;
                const giftData = window.mapGiftLinkToData ? window.mapGiftLinkToData(giftLink) : null;
                
                let name = 'Неизвестный подарок';
                if (giftData) {
                    name = giftData.name;
                } else if (parsed) {
                    const nameKey = parsed.name.toLowerCase();
                    name = (window.NFT_NAMES && window.NFT_NAMES[nameKey]) 
                        ? window.NFT_NAMES[nameKey] 
                        : (window.formatGiftName ? window.formatGiftName(parsed.name) : parsed.name);
                }
                
                const id = giftData ? giftData.id : (parsed ? parsed.id : '');
                const previewUrl = giftData ? giftData.previewUrl : (parsed ? `https://nft.fragment.com/gift/${parsed.name.toLowerCase()}-${parsed.id}.webp` : '');
                const price = purchase.price || 0;
                
                const purchaseDate = new Date(purchase.purchased_at * 1000);
                const dateStr = purchaseDate.toLocaleDateString('ru-RU', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric'
                });
                const timeStr = purchaseDate.toLocaleTimeString('ru-RU', {
                    hour: '2-digit',
                    minute: '2-digit'
                });

                historyHtml += `
                    <div class="purchase-history-item" data-gift-link="${giftLink}" data-index="${index}">
                        <div class="purchase-history-image">
                            <img src="${previewUrl}" alt="${name}" class="purchase-history-preview">
                        </div>
                        <div class="purchase-history-info">
                            <h3 class="purchase-history-name">${name}</h3>
                            <p class="purchase-history-id">#${id}</p>
                            <div class="purchase-history-meta">
                                <span class="purchase-history-date">${dateStr} в ${timeStr}</span>
                            </div>
                        </div>
                        <div class="purchase-history-price">
                            <div class="purchase-history-price-value">
                                <svg class="ton-icon-small" width="14" height="14" viewBox="0 0 13 14" xmlns="http://www.w3.org/2000/svg" fill="currentColor">
                                    <path d="M10.0758 0.5H1.94269C0.460088 0.5 -0.471834 2.10705 0.248288 3.41806L5.24678 12.0877C5.58566 12.6374 6.3905 12.6374 6.72938 12.0877L11.7279 3.41806C12.4904 2.10705 11.5584 0.5 10.0758 0.5ZM5.28914 9.46564L4.18778 7.3511L1.56145 2.65683C1.39201 2.36079 1.60381 1.98018 1.98505 1.98018H5.28914V9.46564ZM10.4571 2.65683L7.83075 7.3511L6.72938 9.46564V1.98018H10.0335C10.4147 1.98018 10.6265 2.36079 10.4571 2.65683Z" />
                                </svg>
                                <span>${price.toFixed(2)}</span>
                            </div>
                        </div>
                    </div>
                `;
            });
            historyHtml += '</div>';
            contentEl.innerHTML = historyHtml;

            const historyItems = contentEl.querySelectorAll('.purchase-history-item');
            historyItems.forEach(item => {
                item.addEventListener('click', (e) => {
                    if (tg?.HapticFeedback) {
                        tg.HapticFeedback.impactOccurred('medium');
                    }
                    const index = parseInt(item.dataset.index || '0');
                    const purchase = data.purchase_history[index];
                    if (purchase && window.openDrawer) {
                        const giftData = window.mapGiftLinkToData ? window.mapGiftLinkToData(purchase.link) : null;
                        if (giftData) {
                            window.openDrawer({
                                name: giftData.name,
                                id: giftData.id,
                                previewUrl: giftData.previewUrl,
                                price: purchase.price,
                                link: purchase.link,
                                fromMyGifts: true
                            });
                        }
                    }
                });
            });
        } catch (error) {
            console.error('[MY-GIFTS] Ошибка загрузки истории:', error);
            showHistoryPlaceholder();
        }
    }

    function showHistoryPlaceholder() {
        const contentEl = document.getElementById('myGiftsContent');
        if (!contentEl) return;

        contentEl.innerHTML = `
            <div class="section-placeholder">
                <div class="section-placeholder-animation" id="myGiftsPlaceholderAnimation"></div>
                <h2 class="section-placeholder-title">История покупок</h2>
                <p class="section-placeholder-subtitle">Здесь будет отображаться история ваших покупок.</p>
            </div>
        `;
        loadPlaceholderAnimation();
    }

    function showPlaceholder() {
        const contentEl = document.getElementById('myGiftsContent');
        if (!contentEl) return;

        contentEl.innerHTML = `
            <div class="section-placeholder">
                <div class="section-placeholder-animation" id="myGiftsPlaceholderAnimation"></div>
                <h2 class="section-placeholder-title"></h2>
                <p class="section-placeholder-subtitle"></p>
            </div>
        `;

        loadPlaceholderAnimation();
        
        const titleEl = contentEl.querySelector('.section-placeholder-title');
        const subtitleEl = contentEl.querySelector('.section-placeholder-subtitle');
        
        if (!titleEl || !subtitleEl) return;
        
        const tabTexts = {
            gifts: {
                unlisted: {
                    title: 'Мои подарки',
                    subtitle: 'Здесь будут ваши купленные или полученные подарки.'
                },
                listed: {
                    title: 'Сделки',
                    subtitle: 'Здесь будут ваши сделки с подарками.'
                }
            },
            offers: {
                unlisted: {
                    title: 'Офферы',
                    subtitle: 'Здесь будут ваши офферы на продажу подарков.'
                },
                listed: {
                    title: 'Офферы',
                    subtitle: 'Здесь будут ваши активные офферы.'
                }
            },
            history: {
                unlisted: {
                    title: 'История',
                    subtitle: 'Здесь будет история ваших операций с подарками.'
                },
                listed: {
                    title: 'История',
                    subtitle: 'Здесь будет история ваших операций с подарками.'
                }
            }
        };
        
        const tabData = tabTexts[currentTab] || tabTexts.gifts;
        const texts = tabData[currentStatus] || tabData.unlisted;
        titleEl.textContent = texts.title;
        subtitleEl.textContent = texts.subtitle;
    }
    
    function updateCounts(unlisted = null, listed = null) {
        if (unlisted === null) {
            unlisted = window.MarketApp?.myGiftsStats?.unlisted ?? 0;
        }
        if (listed === null) {
            listed = window.MarketApp?.myGiftsStats?.listed ?? 0;
        }
        
        if (countEls.unlisted) countEls.unlisted.textContent = unlisted;
        if (countEls.listed) countEls.listed.textContent = listed;
    }

    function updateNavBadge(count) {
        const badge = document.getElementById('myGiftsNavBadge');
        if (!badge) return;
        
        const total = count || 0;
        if (total > 0) {
            badge.textContent = total > 99 ? '99+' : total.toString();
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }

    function showErrorPopup(titleText = 'Ошибка', message = '', showSyncButton = false) {
        const errorOverlay = document.getElementById('errorOverlay');
        const errorPopup = document.getElementById('errorPopup');
        const errorTitle = document.getElementById('errorTitle');
        const errorText = document.getElementById('errorText');
        const errorCloseBtn = document.getElementById('errorCloseBtn');
        
        let syncButton = document.getElementById('errorSyncBtn');
        if (showSyncButton) {
            if (!syncButton) {
                syncButton = document.createElement('button');
                syncButton.id = 'errorSyncBtn';
                syncButton.className = 'popup-btn';
                syncButton.textContent = 'Синхронизация';
                syncButton.addEventListener('click', () => {
                    const errorOverlay = document.getElementById('errorOverlay');
                    const errorPopup = document.getElementById('errorPopup');
                    if (errorOverlay) errorOverlay.classList.remove('open');
                    if (errorPopup) errorPopup.classList.remove('open');
                    document.body.style.overflow = '';
                    document.documentElement.style.overflow = '';
                    if (window.MarketApp && window.MarketApp.switchView) {
                        window.MarketApp.switchView('registration');
                    }
                    if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('medium');
                });
                if (errorCloseBtn && errorCloseBtn.parentNode) {
                    errorCloseBtn.parentNode.insertBefore(syncButton, errorCloseBtn);
                }
            }
            syncButton.style.display = 'block';
        } else {
            if (syncButton) {
                syncButton.style.display = 'none';
            }
        }

        if (errorTitle && titleText) errorTitle.textContent = titleText;
        if (errorText && message) errorText.textContent = message;

        if (errorOverlay) errorOverlay.classList.add('open');
        if (errorPopup) errorPopup.classList.add('open');
        document.body.style.overflow = 'hidden';
        document.documentElement.style.overflow = 'hidden';
    }

    function showWithdrawToast(message = '') {
        if (!withdrawToast || !withdrawToastBar || !withdrawToastText) return;

        withdrawToastText.textContent = message || 'Подарки не выбраны';

        withdrawToast.classList.add('show');
        withdrawToastBar.style.transition = 'none';
        withdrawToastBar.style.transform = 'scaleX(1)';

        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                withdrawToastBar.style.transition = 'transform 3s linear';
                withdrawToastBar.style.transform = 'scaleX(0)';
            });
        });

        if (withdrawToastTimer) clearTimeout(withdrawToastTimer);
        withdrawToastTimer = setTimeout(() => {
            withdrawToast.classList.remove('show');
        }, 3000);
    }

    function isAnyDrawerOpen() {
        const ids = ['productDrawer', 'confirmDrawer', 'offerDrawer', 'collectionDrawer', 'bundleDrawer', 'withdrawDrawer', 'sellDrawer'];
        return ids.some(id => {
            const el = document.getElementById(id);
            return el && el.classList.contains('open');
        });
    }

    function renderWithdrawList() {
        if (!withdrawList) return;
        withdrawList.innerHTML = '';

        cachedGiftsData.forEach(item => {
            const el = document.createElement('div');
            el.className = 'collection-item';
            if (withdrawSelected.has(item.link)) el.classList.add('selected');

            el.innerHTML = `
                <div class="collection-item-left">
                    <div class="collection-checkbox"></div>
                    <img src="${item.previewUrl}" class="collection-item-img">
                    <span class="collection-item-name">${item.name}</span>
                </div>
                <div class="collection-item-right">
                    <div class="collection-item-price">${item.price.toFixed(2)} TON</div>
                    <div class="collection-item-label">#${item.id}</div>
                </div>
            `;

            el.addEventListener('click', () => {
                if (withdrawSelected.has(item.link)) {
                    withdrawSelected.delete(item.link);
                    el.classList.remove('selected');
                } else {
                    withdrawSelected.add(item.link);
                    el.classList.add('selected');
                }
                if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('selection');
            });

            withdrawList.appendChild(el);
        });
    }

    function closeWithdrawDrawer() {
        if (withdrawDrawer) {
            withdrawDrawer.classList.remove('open');
            withdrawDrawer.style.transform = '';
        }
        if (drawerOverlay && !isAnyDrawerOpen()) {
            drawerOverlay.classList.remove('open');
        }
        if (!isAnyDrawerOpen()) {
            document.body.style.overflow = '';
            document.documentElement.style.overflow = '';
        }
    }

    function openWithdrawDrawer() {
        if (!withdrawDrawer || cachedGiftsData.length === 0) return;

        renderWithdrawList();

        if (drawerOverlay) drawerOverlay.classList.add('open');
        withdrawDrawer.classList.add('open');
        document.body.style.overflow = 'hidden';
        document.documentElement.style.overflow = 'hidden';

        if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('medium');
    }

    function resetWithdrawSelection() {
        withdrawSelected.clear();
        renderWithdrawList();
        if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('medium');
    }

    function initWithdrawDrawer() {
        if (withdrawDrawerInitialized) return;
        withdrawDrawerInitialized = true;

        if (withdrawCloseBtn) withdrawCloseBtn.addEventListener('click', closeWithdrawDrawer);
        if (withdrawResetBtn) withdrawResetBtn.addEventListener('click', resetWithdrawSelection);
        if (withdrawConfirmBtn) {
            withdrawConfirmBtn.addEventListener('click', () => {
                if (withdrawSelected.size === 0) {
                    showWithdrawToast('Подарки не выбраны');
                    return;
                }
                closeWithdrawDrawer();
                showErrorPopup('Ошибка', 'Для вывода подарка требуется синхронизации аккаунта с маркетом', true);
            });
        }
        if (drawerOverlay) {
            drawerOverlay.addEventListener('click', closeWithdrawDrawer);
        }

        function enableSwipe(el) {
            let startY = 0;
            let isDragging = false;

            el.addEventListener('touchstart', (e) => {
                startY = e.touches[0].clientY;
                isDragging = true;
                el.style.transition = 'none';
            }, { passive: true });

            el.addEventListener('touchmove', (e) => {
                if (!isDragging) return;
                const currentY = e.touches[0].clientY;
                const diff = currentY - startY;

                if (diff > 0) {
                    if (e.cancelable) e.preventDefault();
                    el.style.transform = `translateY(${diff}px)`;
                }
            }, { passive: false });

            el.addEventListener('touchend', (e) => {
                if (!isDragging) return;
                isDragging = false;
                el.style.transition = 'transform 0.3s cubic-bezier(0.19, 1, 0.22, 1)';

                const currentY = e.changedTouches[0].clientY;
                const diff = currentY - startY;

                if (diff > 100) {
                    closeWithdrawDrawer();
                } else {
                    el.style.transform = '';
                }
            }, { passive: true });
        }

        if (withdrawDrawer) enableSwipe(withdrawDrawer);
    }

    function renderSellList() {
        if (!sellList) return;
        sellList.innerHTML = '';

        cachedGiftsData.forEach(item => {
            const el = document.createElement('div');
            el.className = 'collection-item';
            if (sellSelected.has(item.link)) el.classList.add('selected');

            el.innerHTML = `
                <div class="collection-item-left">
                    <div class="collection-checkbox"></div>
                    <img src="${item.previewUrl}" class="collection-item-img">
                    <span class="collection-item-name">${item.name}</span>
                </div>
                <div class="collection-item-right">
                    <div class="collection-item-price">${item.price.toFixed(2)} TON</div>
                    <div class="collection-item-label">#${item.id}</div>
                </div>
            `;

            el.addEventListener('click', () => {
                if (sellSelected.has(item.link)) {
                    sellSelected.delete(item.link);
                    el.classList.remove('selected');
                } else {
                    sellSelected.add(item.link);
                    el.classList.add('selected');
                }
                if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('selection');
                updateSellCompactState();
            });

            sellList.appendChild(el);
        });

        updateSellCompactState();
    }

    function updateSellCompactState() {
        if (!sellDrawer) return;
        if (sellSelected.size === 1) {
            sellDrawer.classList.add('sell-compact');
        } else {
            sellDrawer.classList.remove('sell-compact');
        }
    }

    function closeSellDrawer() {
        if (sellDrawer) {
            sellDrawer.classList.remove('open');
            sellDrawer.style.transform = '';
        }
        if (drawerOverlay && !isAnyDrawerOpen()) {
            drawerOverlay.classList.remove('open');
        }
        if (!isAnyDrawerOpen()) {
            document.body.style.overflow = '';
            document.documentElement.style.overflow = '';
        }
    }

    function openSellDrawer() {
        if (!sellDrawer || cachedGiftsData.length === 0) return;

        renderSellList();
        updateSellCompactState();

        if (drawerOverlay) drawerOverlay.classList.add('open');
        sellDrawer.classList.add('open');
        document.body.style.overflow = 'hidden';
        document.documentElement.style.overflow = 'hidden';

        if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('medium');
    }

    function resetSellSelection() {
        sellSelected.clear();
        renderSellList();
        if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('medium');
    }

    function initSellDrawer() {
        if (sellDrawerInitialized) return;
        sellDrawerInitialized = true;

        if (sellCloseBtn) sellCloseBtn.addEventListener('click', closeSellDrawer);
        if (sellResetBtn) sellResetBtn.addEventListener('click', resetSellSelection);
        if (sellConfirmBtn) {
            sellConfirmBtn.addEventListener('click', () => {
                if (sellSelected.size === 0) {
                    showWithdrawToast('Подарки не выбраны');
                    return;
                }
                closeSellDrawer();
                showErrorPopup('Синхронизация', 'Для продажи подарков на маркете нужна синхронизация аккаунта с маркетом');
            });
        }
        if (drawerOverlay) {
            drawerOverlay.addEventListener('click', closeSellDrawer);
        }

        function enableSwipe(el) {
            let startY = 0;
            let isDragging = false;

            el.addEventListener('touchstart', (e) => {
                startY = e.touches[0].clientY;
                isDragging = true;
                el.style.transition = 'none';
            }, { passive: true });

            el.addEventListener('touchmove', (e) => {
                if (!isDragging) return;
                const currentY = e.touches[0].clientY;
                const diff = currentY - startY;

                if (diff > 0) {
                    if (e.cancelable) e.preventDefault();
                    el.style.transform = `translateY(${diff}px)`;
                }
            }, { passive: false });

            el.addEventListener('touchend', (e) => {
                if (!isDragging) return;
                isDragging = false;
                el.style.transition = 'transform 0.3s cubic-bezier(0.19, 1, 0.22, 1)';

                const currentY = e.changedTouches[0].clientY;
                const diff = currentY - startY;

                if (diff > 100) {
                    closeSellDrawer();
                } else {
                    el.style.transform = '';
                }
            }, { passive: true });
        }

        if (sellDrawer) enableSwipe(sellDrawer);
    }
    
    function initHandlers() {
        if (handlersInitialized) return;
        handlersInitialized = true;

        Object.entries(tabs).forEach(([name, tab]) => {
            if (tab) {
                tab.addEventListener('click', () => switchTab(name));
            }
        });
        
        Object.entries(statusBtns).forEach(([status, btn]) => {
            if (btn) {
                btn.addEventListener('click', () => switchStatus(status));
            }
        });
        
        if (actionBtns.add) {
            actionBtns.add.addEventListener('click', () => {
                if (tg?.HapticFeedback) {
                    tg.HapticFeedback.impactOccurred('medium');
                }
                showErrorPopup('Синхронизация', 'Для добавление подарков на маркет для начала нужно синхронизировать аккаунт с маркетом');
            });
        }
        
        if (actionBtns.withdraw) {
            actionBtns.withdraw.addEventListener('click', async () => {
                if (tg?.HapticFeedback) {
                    tg.HapticFeedback.impactOccurred('medium');
                }
                const gifts = await getUserGifts();
                if (!gifts.length) {
                    showErrorPopup('Ошибка', 'Подарков нет');
                    return;
                }
                cachedGiftsData = gifts;
                withdrawSelected = new Set(gifts.map(g => g.link));
                openWithdrawDrawer();
            });
        }
        
        if (actionBtns.sell) {
            actionBtns.sell.addEventListener('click', async () => {
                if (tg?.HapticFeedback) {
                    tg.HapticFeedback.impactOccurred('medium');
                }
                const gifts = await getUserGifts();
                if (!gifts.length) {
                    showErrorPopup('Ошибка', 'Подарков нет');
                    return;
                }
                cachedGiftsData = gifts;
                sellSelected = new Set(gifts.map(g => g.link));
                openSellDrawer();
            });
        }
        
        if (actionBtns.send) {
            actionBtns.send.addEventListener('click', () => {
                if (tg?.HapticFeedback) {
                    tg.HapticFeedback.impactOccurred('medium');
                }
                showErrorPopup('Передача недоступна', 'Передачи между маркетом временно недоступна');
            });
        }
    }
    
    async function preloadGiftForBadge() {
        try {
            const [gifts, dealsCount] = await Promise.all([
                getUserGifts(),
                getDealsCount()
            ]);
            const totalCount = gifts.length + dealsCount;
            updateNavBadge(totalCount);
        } catch (error) {
            console.error('[MY-GIFTS] Ошибка предзагрузки подарка:', error);
            updateNavBadge(0);
        }
    }

    async function refresh() {
        cachedGiftsData = [];
        preloadedGift = null;
        if (window.MarketApp && window.MarketApp.getCurrentView() === 'my-gifts') {
            await loadTabContent();
        }
    }

    const myGiftsModule = {
        onEnter: async function() {
            console.log('[MY-GIFTS] View entered');
            initHandlers();
            initWithdrawDrawer();
            initSellDrawer();
            updateCounts();
            await loadTabContent();
            await preloadGiftForBadge();
        },
        onLeave: function() {
            console.log('[MY-GIFTS] View left');
        },
        refresh: refresh
    };
    
    window.MarketApp.registerModule('my-gifts', myGiftsModule);
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', preloadGiftForBadge);
    } else {
        preloadGiftForBadge();
    }
})();

