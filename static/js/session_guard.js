/**
 * Session Guard — prevents browser back-button from navigating
 * to login / signup / landing pages while the user is authenticated.
 *
 * Technique: replaces the current history entry with a guard state,
 * then continuously pushes back whenever a popstate fires without
 * the guard marker.
 */
(function () {
  'use strict';

  // Mark the current entry
  history.replaceState({ _guard: true }, '');

  // On every popstate (back/forward), push the user right back
  window.addEventListener('popstate', function () {
    history.pushState({ _guard: true }, '', location.href);
  });
})();
