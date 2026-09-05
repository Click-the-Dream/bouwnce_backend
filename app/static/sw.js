/* Bouwnce web push service worker */
self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("push", (event) => {
  let payload;
  try {
    payload = event.data ? event.data.json() : {};
  } catch (err) {
    payload = { title: "Bouwnce", body: "" };
  }

  const data = payload.data || {};
  const title = payload.title || "Bouwnce";
  const options = {
    body: payload.body || "",
    icon: data.icon || "/static/icon-192.png",
    badge: "/static/icon-192.png",
    tag: data.tag || "bouwnce-push",
    renotify: true,
    data: { url: data.url || "/", type: data.type || "" },
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl =
    (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clients) => {
        for (const client of clients) {
          if ("focus" in client) {
            client.focus();
            if ("navigate" in client) {
              client.navigate(targetUrl);
            }
            return;
          }
        }
        return self.clients.openWindow(targetUrl);
      }),
  );
});
