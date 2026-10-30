(function () {
  'use strict';

  const generateBtn = document.getElementById('generateBtn');
  const formError    = document.getElementById('formError');
  const emptyState   = document.getElementById('emptyState');
  const result       = document.getElementById('result');
  const loadingState = document.getElementById('loadingState');
  const captchaModal = document.getElementById('captchaModal');
  const cancelCaptcha = document.getElementById('cancelCaptcha');

  const siteKey = document.body.dataset.hcaptchaSiteKey || '';
  let captchaWidgetId = null;
  let isCaptchaReady = Boolean(window.hcaptcha);

  // ── Chip selection ──────────────────────────────────────────────
  document.querySelectorAll('.chip-group').forEach(group => {
    const hiddenInput = document.getElementById(group.dataset.field);
    group.querySelectorAll('.chip').forEach(chip => {
      chip.addEventListener('click', () => {
        group.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        if (hiddenInput) hiddenInput.value = chip.dataset.value;
      });
    });
  });

  // ── Color pickers ───────────────────────────────────────────────
  function syncColorPair(pickerId, textId) {
    const picker = document.getElementById(pickerId);
    const text   = document.getElementById(textId);
    if (!picker || !text) return;
    picker.addEventListener('input', () => { text.value = picker.value; });
    text.addEventListener('input', () => {
      if (/^#[0-9A-Fa-f]{6}$/.test(text.value)) picker.value = text.value;
    });
  }
  syncColorPair('primary_color', 'primary_color_text');
  syncColorPair('accent_color',  'accent_color_text');

  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  // ── hCaptcha Initialization ─────────────────────────────────────
  window.addEventListener('hcaptcha-ready', () => {
    isCaptchaReady = true;
  });

  // Trigger modal on generate click
  generateBtn && generateBtn.addEventListener('click', () => {
    formError.textContent = '';

    if (!siteKey) {
      formError.textContent = 'CAPTCHA is not configured. Set HCAPTCHA_SITE_KEY and HCAPTCHA_SECRET in .env.';
      return;
    }

    if (!isCaptchaReady || !window.hcaptcha) {
      formError.textContent = 'CAPTCHA is still loading or could not be reached. Check your connection and try again.';
      return;
    }

    captchaModal.classList.remove('hidden');

    if (captchaWidgetId === null) {
      try {
        captchaWidgetId = hcaptcha.render("hcaptchaWidget", {
          sitekey: siteKey,
          theme: "dark",
          size: "compact",
          callback: token => {
            captchaModal.classList.add("hidden");
            runGeneration(token);
          },
          "expired-callback": () => {
            captchaModal.classList.add("hidden");
            generateBtn.disabled = false;
            formError.textContent = "CAPTCHA expired. Please try again.";
          }
        });
      } catch (error) {
        captchaModal.classList.add('hidden');
        formError.textContent = 'CAPTCHA could not be displayed. Check the site key and allowed domain.';
        console.error("hCaptcha render error:", error);
      }
    } else {
      hcaptcha.reset(captchaWidgetId);
    }
  });

  cancelCaptcha && cancelCaptcha.addEventListener('click', () => {
    captchaModal.classList.add('hidden');
    generateBtn.disabled = false;
  });

  // ── Core Generation Function ────────────────────────────────────
  async function runGeneration(captchaToken) {
    generateBtn.disabled = true;
    emptyState   && emptyState.classList.add('hidden');
    result       && result.classList.add('hidden');
    loadingState && loadingState.classList.remove('hidden');

    const prefs = {
      style:         document.getElementById('style').value,
      material:      document.getElementById('material').value,
      occasion:      document.getElementById('occasion').value,
      primary_color: document.getElementById('primary_color').value,
      accent_color:  document.getElementById('accent_color').value,
      inspiration:   document.getElementById('inspiration').value.trim(),
      'h-captcha-response': captchaToken
    };

    try {
      const resp = await fetch('/generate', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(prefs),
      });
      const data = await resp.json();

      loadingState && loadingState.classList.add('hidden');

      if (data.error) {
        emptyState && emptyState.classList.remove('hidden');
        formError.textContent = data.error;
      } else {
        const c = data.concept;
        result && result.classList.remove('hidden');
        document.getElementById('resultName').textContent     = c.name || '';
        document.getElementById('resultTagline').textContent  = c.tagline || '';
        const conceptImage = document.getElementById('conceptImage');
        if (conceptImage) {
          conceptImage.src = data.image_url || '';
          conceptImage.hidden = !data.image_url;
        }
        document.getElementById('resultDesc').textContent     = c.description || '';
        document.getElementById('resultPrice').textContent    = c.retail_price || '';
        document.getElementById('resultAudience').textContent = c.target_audience || '';
        document.getElementById('resultTags').textContent     = (c.style_tags || []).join(' · ');
        document.getElementById('materialsList').innerHTML    = (c.materials || []).map(m => `<li>${escHtml(m)}</li>`).join('');
        document.getElementById('featuresList').innerHTML     = (c.features  || []).map(f => `<li>${escHtml(f)}</li>`).join('');
        document.getElementById('soleText').textContent       = c.sole_type || '—';
      }
    } catch (err) {
      loadingState && loadingState.classList.add('hidden');
      emptyState   && emptyState.classList.remove('hidden');
      formError.textContent = 'Network error: ' + err.message;
    }

    generateBtn.disabled = false;
  }

  const regenBtn = document.getElementById('regenBtn');
  regenBtn && regenBtn.addEventListener('click', () => {
    result       && result.classList.add('hidden');
    emptyState   && emptyState.classList.remove('hidden');
    formError.textContent = '';
  });

})();
