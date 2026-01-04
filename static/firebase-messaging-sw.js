importScripts('https://www.gstatic.com/firebasejs/9.6.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.6.1/firebase-messaging-compat.js');

// Initialize the Firebase app in the service worker by passing in the messagingSenderId.
firebase.initializeApp({
    'messagingSenderId': '123456789' // Placeholder - This will be effectively overridden by the browser's instance or needs injection if hardcoding is bad.
    // Actually, for SW, we might need the full config or just sender ID.
    // Ideally, we should fetch this or have it injected. 
    // For now, let's use a robust approach:
});

const messaging = firebase.messaging();

// Background message handler
messaging.onBackgroundMessage(function (payload) {
    console.log('[firebase-messaging-sw.js] Received background message ', payload);
    // Customize notification here
    const notificationTitle = payload.notification.title;
    const notificationOptions = {
        body: payload.notification.body,
        icon: '/static/icons/icon-192x192.png' // Ensure this exists or use a default
    };

    self.registration.showNotification(notificationTitle, notificationOptions);
});
