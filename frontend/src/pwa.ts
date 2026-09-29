export function registerServiceWorker(): void {
  if (!("serviceWorker" in navigator)) {
    return;
  }
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/sw.js")
      .then((reg) => {
        // Promptly check for service worker updates
        reg.update();
      })
      .catch(() => {
        // PWA is optional; the app should keep working if registration fails.
      });
  });

  let refreshing = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (!refreshing) {
      refreshing = true;
      window.location.reload();
    }
  });
}

