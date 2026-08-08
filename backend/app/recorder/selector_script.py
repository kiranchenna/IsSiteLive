"""Injected into every page of a recording session via add_init_script.

Listens for real DOM events triggered by the synthetic input the backend
dispatches via CDP, computes a stable selector for the target element, and
reports each action to Python through the __record binding.
"""

RECORDER_INIT_SCRIPT = r"""
(function () {
  function cssPath(el) {
    if (!el || el.nodeType !== 1) return '';
    if (el.id) return '#' + CSS.escape(el.id);
    var testid = el.getAttribute && el.getAttribute('data-testid');
    if (testid) return '[data-testid="' + testid + '"]';
    if (el.name) return el.tagName.toLowerCase() + '[name="' + el.name + '"]';

    var path = [];
    var node = el;
    for (var i = 0; i < 4 && node && node.nodeType === 1; i++) {
      var selector = node.tagName.toLowerCase();
      if (node.className && typeof node.className === 'string') {
        var cls = node.className.trim().split(/\s+/)[0];
        if (cls) selector += '.' + CSS.escape(cls);
      }
      var parent = node.parentElement;
      if (parent) {
        var siblings = Array.prototype.filter.call(parent.children, function (c) {
          return c.tagName === node.tagName;
        });
        if (siblings.length > 1) {
          selector += ':nth-of-type(' + (siblings.indexOf(node) + 1) + ')';
        }
      }
      path.unshift(selector);
      node = parent;
    }
    return path.join(' > ');
  }

  document.addEventListener(
    'click',
    function (e) {
      if (!window.__record) return;
      var el = e.target;
      if (!el) return;
      // Body/html clicks are still reported (e.g. a slightly missed "mark success" click) --
      // the Python side decides whether a click on the page background is worth keeping.
      var selector = el === document.documentElement ? 'html' : el === document.body ? 'body' : cssPath(el);
      if (selector) window.__record({ type: 'click', selector: selector });
    },
    true
  );

  document.addEventListener(
    'input',
    function (e) {
      if (!window.__record) return;
      var el = e.target;
      if (!el || (el.tagName !== 'INPUT' && el.tagName !== 'TEXTAREA')) return;
      var selector = cssPath(el);
      if (selector) window.__record({ type: 'fill', selector: selector, value: el.value });
    },
    true
  );
})();
"""
