/**
 * SmartReco AI - Unified Behavioral Tracker
 */
(function () {
    'use strict';

    // 1. Unified Configuration
    const API_ENDPOINT = '/api/track'; 

    // Helper to safely extract user ID from localStorage
    function getUserId() {
        const id = localStorage.getItem("user_id");
        return id ? Number(id) : null;
    }

    // 2. Core Event Dispatcher
    async function trackEvent(eventType, description = '', productId = null) {
        const payload = {
            user_id: getUserId(),
            event_type: eventType,
            description: String(description),
            event_data: String(description), // Backward compatibility
            product_id: productId ? parseInt(productId, 10) : null,
            timestamp: new Date().toISOString()
        };

        try {
            const response = await fetch(API_ENDPOINT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                console.warn('[SmartReco Tracker] Failed to log event:', eventType);
            }
        } catch (err) {
            console.error('[SmartReco Tracker] Network error:', err);
        }
    }

    // Expose helpers globally
    window.trackEvent = trackEvent;
    window.sendEvent = trackEvent;

    window.trackProductClick = function (productId, productName) {
        trackEvent('product_click', `Clicked ${productName || 'Product #' + productId}`, productId);
    };

    window.trackAddToCart = function (productId, productName) {
        trackEvent('add_to_cart', `Added ${productName || 'Product #' + productId} to cart`, productId);
    };

    window.trackSearch = function (query) {
        if (!query || !query.trim()) return;
        trackEvent('search', `User searched for: ${query.trim()}`);
    };

    // 3. Automated Event Listeners
    document.addEventListener('DOMContentLoaded', () => {
        // A. Track Page View
        trackEvent('page_view', `Opened ${window.location.pathname}`);

        // B. Track Search Form Submissions
        const searchForm = document.querySelector('form[action="/dashboard"]');
        if (searchForm) {
            searchForm.addEventListener('submit', () => {
                const searchInput = searchForm.querySelector('input[name="search"]');
                if (searchInput && searchInput.value.trim() !== '') {
                    window.trackSearch(searchInput.value);
                }
            });
        }

        // C. Global Click Delegation for Product Cards & Buttons
        document.body.addEventListener('click', (e) => {
            // Check for explicit .btn-add-cart
            const cartBtn = e.target.closest('.btn-add-cart');
            if (cartBtn) {
                const pId = cartBtn.getAttribute('data-product-id') || cartBtn.getAttribute('data-id');
                const pTitle = cartBtn.getAttribute('data-title') || 'Product';
                if (pId) window.trackAddToCart(pId, pTitle);
                return;
            }

            // Check for general product click/inspection
            const productCard = e.target.closest('[data-product-id], .product-btn');
            if (productCard) {
                const pId = productCard.getAttribute('data-product-id') || productCard.getAttribute('data-id');
                const pTitle = productCard.getAttribute('data-title') || `Product #${pId}`;
                if (pId) window.trackProductClick(pId, pTitle);
            }
        });
    });

    // 4. Track Time Spent on Page (Beacon API on Unload)
    const startTime = Date.now();

    window.addEventListener('beforeunload', () => {
        const seconds = Math.floor((Date.now() - startTime) / 1000);
        if (seconds < 2) return; // Ignore accidental misclicks

        const payload = JSON.stringify({
            user_id: getUserId(),
            event_type: 'time_spent',
            description: `${seconds} seconds spent on ${window.location.pathname}`,
            event_data: `${seconds} seconds`,
            product_id: null,
            timestamp: new Date().toISOString()
        });

        const blob = new Blob([payload], { type: 'application/json' });
        navigator.sendBeacon(API_ENDPOINT, blob);
    });

})();