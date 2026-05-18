/**
 * Session Guard — prevents browser back-button from leaving
 * authenticated pages (chat / admin dashboards).
 *
 * Strategy: push multiple guard entries into the history stack
 * so rapid back-presses are absorbed before reaching the previous
 * page. Each popstate re-fills the guard entries.
 */
(function () {
  'use strict';

  var GUARD_DEPTH = 3;   // number of guard entries to maintain
  var GUARD_KEY = '_sg';

  // Fill the history stack with guard entries
  function fillGuards() {
    for (var i = 0; i < GUARD_DEPTH; i++) {
      history.pushState({ _guard: true, i: i }, '', location.href);
    }
  }

  // On first load: replace current entry, then add guards
  history.replaceState({ _guard: true, root: true }, '', location.href);
  fillGuards();

  // Whenever back is pressed and we land on a guard entry (or any entry),
  // re-push guards to keep the wall up
  window.addEventListener('popstate', function (e) {
    // If we are still on the same page, re-push guards
    fillGuards();
  });
})();
