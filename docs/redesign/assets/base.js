(() => {
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  let toastTimer;

  function showToast(message) {
    let node = document.querySelector('.toast');
    if (!node) {
      node = document.createElement('div');
      node.className = 'toast';
      node.setAttribute('role', 'status');
      document.body.appendChild(node);
    }
    node.textContent = message;
    node.classList.add('is-visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => node.classList.remove('is-visible'), 2200);
  }

  document.addEventListener('click', (event) => {
    const toggle = event.target.closest('[data-switch]');
    if (toggle) {
      const next = !toggle.classList.contains('on');
      toggle.classList.toggle('on', next);
      toggle.setAttribute('aria-checked', String(next));
      if (toggle.dataset.toastOn || toggle.dataset.toastOff) {
        showToast(next ? (toggle.dataset.toastOn || '已启用') : (toggle.dataset.toastOff || '已停用'));
      }
      return;
    }

    const action = event.target.closest('[data-toast]');
    if (action) {
      showToast(action.dataset.toast);
      return;
    }

    const nav = event.target.closest('[data-nav]');
    if (nav) {
      const group = nav.closest('[data-nav-group]');
      const scope = group || document;
      $$('[data-nav]', scope).forEach((item) => item.classList.toggle('active', item === nav));
      nav.setAttribute('aria-current', 'page');
      $$('[data-nav]', scope).forEach((item) => {
        if (item !== nav) item.removeAttribute('aria-current');
      });
      if (nav.dataset.navToast) showToast(nav.dataset.navToast);
      return;
    }

    const chip = event.target.closest('[data-chip]');
    if (chip) {
      $$('[data-chip]', chip.parentElement).forEach((item) => item.classList.toggle('active', item === chip));
      return;
    }

    const select = event.target.closest('[data-select]');
    if (select) {
      $$('[data-select]').forEach((item) => item.classList.toggle('is-selected', item === select));
      ['title', 'meta', 'size', 'date', 'file', 'img'].forEach((key) => {
        const value = select.dataset[key];
        if (!value) return;
        $$(`[data-detail-${key}]`).forEach((node) => {
          if (node.tagName === 'IMG') node.src = value;
          else node.textContent = value;
        });
      });
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    const select = event.target.closest('[data-select]');
    if (!select || event.target !== select) return;
    event.preventDefault();
    select.click();
  });

  window.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      const search = document.querySelector('[data-search]');
      if (search) {
        event.preventDefault();
        search.focus();
        if (search.select) search.select();
      }
    }
  });
})();
