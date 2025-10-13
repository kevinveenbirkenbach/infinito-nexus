/* logoutPatch.js */
(function(global) {
  /**
   * Initialize the logout patch script.
   * @param {string} logoutUrlBase - Base logout URL (e.g., from your OIDC client).
   * @param {string} webProtocol - Protocol to use (e.g., "https").
   * @param {string} primaryDomain - Primary domain (e.g., "example.com").
   */
  function initLogoutPatch(logoutUrlBase, webProtocol, primaryDomain) {
    const redirectUri = encodeURIComponent(webProtocol + '://' + primaryDomain);
    const logoutUrl = logoutUrlBase + '?redirect_uri=' + redirectUri;

    function matchesLogout(str) {
      return str && /(?:^|\W)log\s*out(?:\W|$)|logout/i.test(str);
    }

    /**
    * Returns true if any attribute name or value on the given element
    * contains the substring "logout" (case-insensitive).
    *
    * @param {Element} element – The DOM element to inspect.
    * @returns {boolean} – True if "logout" appears in any attribute name or value.
    */
    function containsLogoutAttribute(element) {
      for (const attribute of element.attributes) {
        if (/logout/i.test(attribute.name) || /logout/i.test(attribute.value)) {
          return true;
        }
      }
      return false;
    }

    function matchesTechnicalIndicators(el) {
      const title = el.getAttribute('title');
      const ariaLabel = el.getAttribute('aria-label');
      const onclick = el.getAttribute('onclick');

      if (matchesLogout(title) || matchesLogout(ariaLabel) || matchesLogout(onclick)) return true;

      for (const attr of el.attributes) {
        if (attr.name.startsWith('data-') && matchesLogout(attr.name + attr.value)) return true;
      }

      if (typeof el.onclick === 'function' && matchesLogout(el.onclick.toString())) return true;

      if (el.tagName.toLowerCase() === 'use') {
        const href = el.getAttribute('xlink:href') || el.getAttribute('href');
        if (matchesLogout(href)) return true;
      }
      return false;
    }

    /**
    * Apply logout redirect behavior to a matching element:
    * – Installs a capturing click‐handler to force navigation to logoutUrl
    * – Always sets href/formaction/action to logoutUrl
    * – Marks the element as patched to avoid double‐binding
    *
    * @param {Element} el – The element to override (e.g. <a>, <button>, <form>, <input>)
    * @param {string} logoutUrl – The full logout URL including redirect params
    */
    function overrideLogout(el, logoutUrl) {
      // avoid patching the same element twice
      if (el.dataset._logoutHandled) return;
      el.dataset._logoutHandled = "true";

      // show pointer cursor
      el.style.cursor = 'pointer';

      // capture‐phase listener so it fires before any framework handlers
      el.addEventListener('click', function(e) {
        e.preventDefault();
        window.location.href = logoutUrl;
      }, { capture: true });

      const tag = el.tagName.toLowerCase();

      // always set the link target on <a>
      if (tag === 'a') {
        el.setAttribute('href', logoutUrl);
      }
      // always set the formaction on <button> or <input>
      else if ((tag === 'button' || tag === 'input') && el.hasAttribute('formaction')) {
        el.setAttribute('formaction', logoutUrl);
      }
      // always set the form action on <form>
      else if (tag === 'form') {
        el.setAttribute('action', logoutUrl);
      }
    }

    function scanAndPatch(elements) {
      elements.forEach(el => {
        const tagName = el.tagName.toLowerCase();
        const isPotential = ['a','button','input','form','use'].includes(tagName);
        if (!isPotential) return;
        if (
          matchesLogout(el.getAttribute('name')) ||
          matchesLogout(el.id) ||
          matchesLogout(el.className) ||
          matchesLogout(el.innerText) ||
          containsLogoutAttribute(el) ||
          matchesTechnicalIndicators(el)
        ) {
          overrideLogout(el, logoutUrl);
        }
      });
    }

    // Initial scan
    scanAndPatch(Array.from(document.querySelectorAll('*')));

    // Watch for dynamic content
    const observer = new MutationObserver(mutations => {
      mutations.forEach(mutation => {
        mutation.addedNodes.forEach(node => {
          if (!(node instanceof Element)) return;
          scanAndPatch([node, ...node.querySelectorAll('*')]);
        });
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  // Expose to global scope
  global.initLogoutPatch = initLogoutPatch;
})(window);
