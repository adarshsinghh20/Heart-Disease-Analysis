/**
 * HDInsight – main.js
 * Global JavaScript for the Heart Disease Analysis Platform
 */

'use strict';

// ── Plotly global config ──────────────────────────────────────────
const PLOTLY_CONFIG = {
  responsive: true,
  displayModeBar: true,
  modeBarButtonsToRemove: ['lasso2d', 'select2d', 'toggleSpikelines'],
  toImageButtonOptions: {
    format: 'png',
    filename: 'hdinsight_chart',
    height: 600,
    width: 1000,
    scale: 2
  }
};

// ── Tooltip init (Bootstrap) ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltips.forEach(el => new bootstrap.Tooltip(el));

  // Animate KPI numbers on load
  animateCounters();

  // Active nav link highlight based on current path
  highlightNav();

  // Story scroll dots
  setupStoryScrollSpy();
});

// ── Animated counters ─────────────────────────────────────────────
function animateCounters() {
  document.querySelectorAll('.kpi-value, .stat-value').forEach(el => {
    const raw = el.textContent.replace(/[,%]/g, '').trim();
    const num = parseFloat(raw);
    if (isNaN(num) || raw.includes('—')) return;
    const isSuffix = el.textContent.includes('%');
    const isComma  = el.textContent.includes(',');
    let start = 0;
    const duration = 1000;
    const step = num / (duration / 16);
    const timer = setInterval(() => {
      start = Math.min(start + step, num);
      let display = start % 1 === 0 ? Math.round(start) : start.toFixed(1);
      if (isComma) display = Number(display).toLocaleString();
      el.textContent = display + (isSuffix ? '%' : '');
      if (start >= num) clearInterval(timer);
    }, 16);
  });
}

// ── Story scroll spy ──────────────────────────────────────────────
function setupStoryScrollSpy() {
  const dots = document.querySelectorAll('.story-nav-dot');
  if (!dots.length) return;
  const scenes = document.querySelectorAll('.story-scene');
  if (!scenes.length) return;

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const idx = Array.from(scenes).indexOf(entry.target);
        dots.forEach((d, i) => d.classList.toggle('active', i === idx));
      }
    });
  }, { threshold: 0.4 });

  scenes.forEach(s => observer.observe(s));
}

// ── Active nav highlighting ───────────────────────────────────────
function highlightNav() {
  const path = window.location.pathname;
  document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
    try {
      const href = new URL(link.href).pathname;
      if (href === path) link.classList.add('active');
    } catch (_) {}
  });
}

// ── Chart resize on window resize ────────────────────────────────
let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    document.querySelectorAll('.chart-container').forEach(el => {
      if (el.id) {
        try { Plotly.relayout(el.id, { autosize: true }); } catch(_) {}
      }
    });
  }, 250);
});

// ── Export chart helper ───────────────────────────────────────────
window.exportChart = function(divId, filename='chart') {
  try {
    Plotly.downloadImage(divId, { format: 'png', filename, width: 1200, height: 700 });
  } catch(e) {
    console.warn('Export failed:', e);
  }
};

// ── Utility: debounce ─────────────────────────────────────────────
window.debounce = function(fn, delay) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), delay);
  };
};
