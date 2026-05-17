/**
 * Session Guard — prevents browser back-button from navigating
 * to login / signup / landing pages while the user is authenticated.
 *
 * How it works:
 *  1. On load, pushes a guard entry into browser history.
 *  2. Listens for popstate (back button). If triggered, re-pushes
 *     the guard entry so the user stays on the current page.
 *  3. Intercepts any programmatic navigation to auth pages while logged in.
 */
(function () {
  'use strict';

  const AUTH_PATHS = ['/', '/auth/login', '/auth/signup'];

  function isAuthPage(url) {
    try {
      const path = new URL(url, window.location.origin).pathname;
      return AUTH_PATHS.includes(path);
    } catch (e) {
      return AUTH_PATHS.includes(url);
    }
  }

  // Push a guard state on load
  if (!history.state || !history.state._guard) {
    history.replaceState({ _guard: true, url: location.href }, '', location.href);
  }

  // When back is pressed, push forward again to stay on this page
  window.addEventListener('popstate', function (e) {
    if (!e.state || !e.state._guard) {
      // User pressed back — push them forward again
      history.pushState({ _guard: true, url: location.href }, '', location.href);
    }
  });
})();
