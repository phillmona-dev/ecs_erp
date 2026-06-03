/* ═══════════════════════════════════════════════════
   ECS Login — Micro-interactions & Animations
   phillipos1212@gmail.com © 2025
   ═══════════════════════════════════════════════════ */

(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        initLoginInteractions();
        initLauncherSearch();
        initGlowParallax();
    });

    function initLoginInteractions() {
        if (!document.querySelector('.ecs-glass-card')) return;

        /* ── 1. Password Show/Hide Toggle ──────────────── */
        const toggle = document.getElementById('ecs-pw-toggle');
        const pwInput = document.getElementById('password');
        const pwIcon  = document.getElementById('ecs-pw-icon');

        if (toggle && pwInput && pwIcon) {
            toggle.addEventListener('click', function () {
                const isHidden = pwInput.type === 'password';
                pwInput.type = isHidden ? 'text' : 'password';
                pwIcon.className = isHidden ? 'fa fa-eye-slash' : 'fa fa-eye';
                toggle.setAttribute('aria-label', isHidden ? 'Hide password' : 'Show password');
            });
        }

        /* ── 2. Submit Button Loading State ────────────── */
        const form   = document.querySelector('.ecs-login-form');
        const btn    = document.getElementById('ecs-signin-btn');

        if (form && btn) {
            form.addEventListener('submit', function () {
                btn.classList.add('ecs-loading');
                btn.disabled = true;
                // Safety reset after 8s in case of error
                setTimeout(() => {
                    btn.classList.remove('ecs-loading');
                    btn.disabled = false;
                }, 8000);
            });
        }
    }

    function initLauncherSearch() {
        const searchPanel = document.querySelector('.ecs-search-panel');
        const searchInput = document.getElementById('ecs-app-search');
        const clearButton = document.getElementById('ecs-app-search-clear');
        const resetButton = document.getElementById('ecs-reset-search');
        const countElement = document.getElementById('ecs-visible-count');
        const noResults = document.getElementById('ecs-no-results');
        const cards = Array.from(document.querySelectorAll('.ecs-app-card'));
        const chips = Array.from(document.querySelectorAll('.ecs-filter-chip'));

        if (!searchPanel || !searchInput || !cards.length) return;

        let activeFilter = 'all';

        const applyFilters = function () {
            const query = searchInput.value.trim().toLowerCase();
            let visibleCount = 0;

            cards.forEach(function (card) {
                const searchText = (card.dataset.search || '').toLowerCase();
                const category = card.dataset.category || 'other';
                const matchesFilter = activeFilter === 'all' || category === activeFilter;
                const matchesQuery = !query || searchText.includes(query);
                const isVisible = matchesFilter && matchesQuery;

                card.classList.toggle('is-hidden', !isVisible);
                if (isVisible) visibleCount += 1;
            });

            if (countElement) countElement.textContent = String(visibleCount);
            if (clearButton) clearButton.classList.toggle('is-visible', Boolean(query));
            if (noResults) noResults.hidden = visibleCount !== 0;
        };

        chips.forEach(function (chip) {
            chip.addEventListener('click', function () {
                activeFilter = chip.dataset.filter || 'all';
                chips.forEach(function (item) {
                    item.classList.toggle('is-active', item === chip);
                });
                applyFilters();
            });
        });

        searchInput.addEventListener('input', applyFilters);

        if (clearButton) {
            clearButton.addEventListener('click', function () {
                searchInput.value = '';
                searchInput.focus();
                applyFilters();
            });
        }

        if (resetButton) {
            resetButton.addEventListener('click', function () {
                activeFilter = 'all';
                searchInput.value = '';
                chips.forEach(function (chip) {
                    chip.classList.toggle('is-active', chip.dataset.filter === 'all');
                });
                searchInput.focus();
                applyFilters();
            });
        }

        document.addEventListener('keydown', function (event) {
            const isTyping = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName);
            if (event.key === '/' && !isTyping) {
                event.preventDefault();
                searchInput.focus();
            }
            if (event.key === 'Escape' && document.activeElement === searchInput) {
                searchInput.value = '';
                applyFilters();
            }
        });

        applyFilters();
    }

    function initGlowParallax() {
        const glow = document.querySelector('.ecs-bg-glow');
        const glowLeft = document.querySelector('.ecs-bg-glow-left');
        const glowCard = document.querySelector('.ecs-bg-glow-card');

        if (!glow && !glowLeft && !glowCard) return;
        
        document.addEventListener('mousemove', function (e) {
            const cx = window.innerWidth  / 2;
            const cy = window.innerHeight / 2;
            const dx = (e.clientX - cx) / cx;
            const dy = (e.clientY - cy) / cy;
            
            if (glow)     glow.style.transform     = `translate(${dx * 25}px, ${dy * 25}px)`;
            if (glowLeft) glowLeft.style.transform = `translate(${dx * -15}px, ${dy * -15}px)`;
            if (glowCard) glowCard.style.transform = `translate(${dx * 10}px, ${dy * 10}px) translate(-50%, -50%)`;
        });
    }
})();
