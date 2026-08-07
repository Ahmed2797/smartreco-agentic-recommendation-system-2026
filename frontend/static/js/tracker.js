// /**
//  * SmartReco AI - Unified Behavioral Tracker
//  */
// (function () {
//     'use strict';

//     // 1. Unified Configuration
//     const API_ENDPOINT = '/api/track'; 

//     // Helper to safely extract user ID from localStorage
//     function getUserId() {
//         const id = localStorage.getItem("user_id");
//         return id ? Number(id) : null;
//     }

//     // 2. Core Event Dispatcher
//     async function trackEvent(eventType, description = '', productId = null) {
//         const payload = {
//             user_id: getUserId(),
//             event_type: eventType,
//             description: String(description),
//             event_data: String(description), // Backward compatibility
//             product_id: productId ? parseInt(productId, 10) : null,
//             timestamp: new Date().toISOString()
//         };

//         try {
//             const response = await fetch(API_ENDPOINT, {
//                 method: 'POST',
//                 headers: {
//                     'Content-Type': 'application/json'
//                 },
//                 body: JSON.stringify(payload)
//             });

//             if (!response.ok) {
//                 console.warn('[SmartReco Tracker] Failed to log event:', eventType);
//             }
//         } catch (err) {
//             console.error('[SmartReco Tracker] Network error:', err);
//         }
//     }

//     // Expose helpers globally
//     window.trackEvent = trackEvent;
//     window.sendEvent = trackEvent;

//     window.trackProductClick = function (productId, productName) {
//         trackEvent('product_click', `Clicked ${productName || 'Product #' + productId}`, productId);
//     };

//     window.trackAddToCart = function (productId, productName) {
//         trackEvent('add_to_cart', `Added ${productName || 'Product #' + productId} to cart`, productId);
//     };

//     window.trackSearch = function (query) {
//         if (!query || !query.trim()) return;
//         trackEvent('search', `User searched for: ${query.trim()}`);
//     };

//     // 3. Automated Event Listeners
//     document.addEventListener('DOMContentLoaded', () => {
//         // A. Track Page View
//         trackEvent('page_view', `Opened ${window.location.pathname}`);

//         // B. Track Search Form Submissions
//         const searchForm = document.querySelector('form[action="/dashboard"]');
//         if (searchForm) {
//             searchForm.addEventListener('submit', () => {
//                 const searchInput = searchForm.querySelector('input[name="search"]');
//                 if (searchInput && searchInput.value.trim() !== '') {
//                     window.trackSearch(searchInput.value);
//                 }
//             });
//         }

//         // C. Global Click Delegation for Product Cards & Buttons
//         document.body.addEventListener('click', (e) => {
//             // Check for explicit .btn-add-cart
//             const cartBtn = e.target.closest('.btn-add-cart');
//             if (cartBtn) {
//                 const pId = cartBtn.getAttribute('data-product-id') || cartBtn.getAttribute('data-id');
//                 const pTitle = cartBtn.getAttribute('data-title') || 'Product';
//                 if (pId) window.trackAddToCart(pId, pTitle);
//                 return;
//             }

//             // Check for general product click/inspection
//             const productCard = e.target.closest('[data-product-id], .product-btn');
//             if (productCard) {
//                 const pId = productCard.getAttribute('data-product-id') || productCard.getAttribute('data-id');
//                 const pTitle = productCard.getAttribute('data-title') || `Product #${pId}`;
//                 if (pId) window.trackProductClick(pId, pTitle);
//             }
//         });
//     });

//     // 4. Track Time Spent on Page (Beacon API on Unload)
//     const startTime = Date.now();

//     window.addEventListener('beforeunload', () => {
//         const seconds = Math.floor((Date.now() - startTime) / 1000);
//         if (seconds < 2) return; // Ignore accidental misclicks

//         const payload = JSON.stringify({
//             user_id: getUserId(),
//             event_type: 'time_spent',
//             description: `${seconds} seconds spent on ${window.location.pathname}`,
//             event_data: `${seconds} seconds`,
//             product_id: null,
//             timestamp: new Date().toISOString()
//         });

//         const blob = new Blob([payload], { type: 'application/json' });
//         navigator.sendBeacon(API_ENDPOINT, blob);
//     });

// })();


// // Reusable Event Tracker
// async function logRealUserEvent(eventType, eventData, productId = null) {
//     try {
//         await fetch('/api/events/log', {
//             method: 'POST',
//             headers: { 'Content-Type': 'application/json' },
//             body: JSON.stringify({
//                 event_type: eventType,
//                 event_data: eventData,
//                 product_id: productId
//             })
//         });
//     } catch (err) {
//         console.error("Event logging error:", err);
//     }
// }

// // 1. Real Page View Event
// window.addEventListener('DOMContentLoaded', () => {
//     logRealUserEvent('view_page', window.location.pathname);
// });

// // 2. Real Search Query Event
// document.querySelector('#search-form')?.addEventListener('submit', (e) => {
//     const searchQuery = document.querySelector('#search-input').value;
//     if (searchQuery) {
//         logRealUserEvent('search_query', searchQuery);
//     }
// });

// // 3. Real Product Click Event
// function onProductCardClick(productId, productTitle) {
//     logRealUserEvent('product_click', `Viewed ${productTitle}`, productId);
// }


/**
 * SmartReco AI — Unified Behavioral Tracker
 * Target Endpoint: POST /api/events/log
 */
(function () {
    'use strict';

    const API_ENDPOINT = '/api/events/log';

    /**
     * Core Event Logging Engine
     */
    async function logRealUserEvent(eventType, eventData = '', productId = null) {
        const payload = {
            event_type: eventType,
            event_data: String(eventData),
            product_id: productId ? parseInt(productId, 10) : null
        };

        try {
            const response = await fetch(API_ENDPOINT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                console.warn('[SmartReco Tracker] Failed to log event:', eventType);
            }
        } catch (err) {
            console.error('[SmartReco Tracker] Network error:', err);
        }
    }

    // Expose helpers globally for inline HTML triggers
    window.logRealUserEvent = logRealUserEvent;
    
    window.trackProductClick = function (productId, productTitle) {
        logRealUserEvent('product_click', `Viewed ${productTitle || 'Product #' + productId}`, productId);
    };

    window.trackAddToCart = function (productId, productTitle) {
        logRealUserEvent('add_to_cart', `Added ${productTitle || 'Product #' + productId} to cart`, productId);
    };

    window.trackSearch = function (query) {
        if (!query || !query.trim()) return;
        logRealUserEvent('search_query', query.trim());
    };

    // Backward compatibility wrapper
    window.onProductCardClick = window.trackProductClick;

    /**
     * Automated DOM Listeners
     */
    document.addEventListener('DOMContentLoaded', () => {
        // 1. Automatically Log Page Views
        logRealUserEvent('view_page', window.location.pathname);

        // 2. Automatically Track Search Form Submissions
        const searchForm = document.querySelector('#search-form') || document.querySelector('form[action*="dashboard"]');
        if (searchForm) {
            searchForm.addEventListener('submit', () => {
                const searchInput = searchForm.querySelector('#search-input') || searchForm.querySelector('input[name="search"]');
                if (searchInput && searchInput.value.trim() !== '') {
                    window.trackSearch(searchInput.value);
                }
            });
        }

        // 3. Global Event Delegation (Click Tracking)
        document.body.addEventListener('click', (e) => {
            // Add to Cart Button Click
            const cartBtn = e.target.closest('.btn-add-cart');
            if (cartBtn) {
                const pId = cartBtn.getAttribute('data-product-id') || cartBtn.getAttribute('data-id');
                const pTitle = cartBtn.getAttribute('data-title') || 'Product';
                if (pId) window.trackAddToCart(pId, pTitle);
                return;
            }

            // General Product Card Click
            const productCard = e.target.closest('[data-product-id], .product-card, .product-btn');
            if (productCard) {
                const pId = productCard.getAttribute('data-product-id') || productCard.getAttribute('data-id');
                const pTitle = productCard.getAttribute('data-title') || `Product #${pId}`;
                if (pId) window.trackProductClick(pId, pTitle);
            }
        });
    });

    /**
     * Time Spent on Page (Unload Beacon)
     */
    const startTime = Date.now();

    window.addEventListener('beforeunload', () => {
        const seconds = Math.floor((Date.now() - startTime) / 1000);
        if (seconds < 2) return; // Skip accidental page bounces

        const payload = JSON.stringify({
            event_type: 'time_spent',
            event_data: `${seconds} seconds on ${window.location.pathname}`,
            product_id: null
        });

        const blob = new Blob([payload], { type: 'application/json' });
        navigator.sendBeacon(API_ENDPOINT, blob);
    });

})();