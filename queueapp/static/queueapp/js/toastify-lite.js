(function (window, document) {
  'use strict';

  var DEFAULT_AUTO_CLOSE = 4200;
  var MAX_TOASTS = 5;
  var iconByType = {
    success: '✓',
    error: '×',
    warning: '!',
    info: 'i',
    default: 'i'
  };

  function normalizeType(type) {
    var value = String(type || 'info').toLowerCase();
    if (value === 'danger') return 'error';
    if (value === 'warn') return 'warning';
    if (['success', 'error', 'warning', 'info', 'default'].indexOf(value) === -1) return 'info';
    return value;
  }

  function getContainer(position) {
    var pos = position || 'top-right';
    var selector = '.Toastify__toast-container--' + pos;
    var container = document.querySelector(selector);
    if (!container) {
      container = document.createElement('div');
      container.className = 'Toastify__toast-container Toastify__toast-container--' + pos;
      container.setAttribute('aria-live', 'polite');
      container.setAttribute('aria-atomic', 'true');
      document.body.appendChild(container);
    }
    return container;
  }

  function dismiss(toast) {
    if (!toast || toast.dataset.dismissed === 'true') return;
    toast.dataset.dismissed = 'true';
    toast.classList.remove('Toastify__toast--visible');
    toast.classList.add('Toastify__toast--leaving');
    window.setTimeout(function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 280);
  }

  function trimQueue(container) {
    var toasts = container.querySelectorAll('.Toastify__toast');
    if (toasts.length > MAX_TOASTS) dismiss(toasts[0]);
  }

  function show(message, options) {
    options = options || {};
    var type = normalizeType(options.type);
    var autoClose = typeof options.autoClose === 'number' ? options.autoClose : DEFAULT_AUTO_CLOSE;
    var container = getContainer(options.position || 'top-right');

    var toast = document.createElement('div');
    toast.className = 'Toastify__toast Toastify__toast-theme--light Toastify__toast--' + type;
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');

    var icon = document.createElement('span');
    icon.className = 'Toastify__toast-icon';
    icon.textContent = iconByType[type] || iconByType.info;

    var body = document.createElement('div');
    body.className = 'Toastify__toast-body';
    body.textContent = message == null ? '' : String(message);

    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'Toastify__close-button';
    close.setAttribute('aria-label', 'Fermer la notification');
    close.innerHTML = '&times;';
    close.addEventListener('click', function () { dismiss(toast); });

    toast.appendChild(icon);
    toast.appendChild(body);
    toast.appendChild(close);

    if (autoClose > 0) {
      var progress = document.createElement('div');
      progress.className = 'Toastify__progress-bar';
      progress.style.animationDuration = autoClose + 'ms';
      toast.appendChild(progress);
      window.setTimeout(function () { dismiss(toast); }, autoClose);
    }

    container.appendChild(toast);
    trimQueue(container);
    window.requestAnimationFrame(function () { toast.classList.add('Toastify__toast--visible'); });
    return toast;
  }

  var api = {
    show: show,
    success: function (message, options) { return show(message, Object.assign({}, options, { type: 'success' })); },
    error: function (message, options) { return show(message, Object.assign({}, options, { type: 'error' })); },
    warning: function (message, options) { return show(message, Object.assign({}, options, { type: 'warning' })); },
    info: function (message, options) { return show(message, Object.assign({}, options, { type: 'info' })); },
    dismiss: dismiss,
    dismissAll: function () { document.querySelectorAll('.Toastify__toast').forEach(dismiss); }
  };

  window.appToast = api;
  window.showAlert = function (type, message) { return show(message, { type: type }); };
})(window, document);
