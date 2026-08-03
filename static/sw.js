// Service Worker - 共福农机库存管理系统 PWA
const CACHE = 'farm-erp-v15';
const ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/js/common.js',
  '/static/js/jsQR.min.js',
  '/static/js/qrcode.min.js',
  '/static/manifest.json',
  '/static/icon.png',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).catch(()=>{}));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE).map(k => caches.delete(k))
    )).then(() => self.clients.claim())
  );
  // 通知所有客户端强制刷新
  e.waitUntil(
    self.clients.matchAll({type: 'window'}).then(clients => {
      clients.forEach(c => c.postMessage({type: 'SW_UPDATED'}));
    })
  );
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.pathname.startsWith('/api/')) return;
  // HTML 页面始终走网络（避免缓存旧模板）
  const isHTML = e.request.headers.get('accept')?.includes('text/html');
  if (isHTML) {
    e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));
    return;
  }
  // JS/CSS：network-first，确保拿到最新版
  if (url.pathname.startsWith('/static/')) {
    e.respondWith(
      fetch(e.request).then(resp => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return resp;
      }).catch(() => caches.match(e.request))
    );
    return;
  }
  e.respondWith(
    caches.match(e.request).then(cached => {
      return cached || fetch(e.request).then(resp => {
        if (resp.ok && url.origin === self.location.origin) {
          const clone = resp.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return resp;
      }).catch(() => cached)
    })
  );
});

// 接收消息：手动跳过等待
self.addEventListener('message', e => {
  if (e.data && e.data.type === 'SKIP_WAITING') self.skipWaiting();
});
