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

  function fillGuards() {
    for (var i = 0; i < GUARD_DEPTH; i++) {
      history.pushState({ _guard: true, i: i }, '', location.href);
    }
  }

  history.replaceState({ _guard: true, root: true }, '', location.href);
  fillGuards();

  window.addEventListener('popstate', function (e) {
    fillGuards();
  });
})();
