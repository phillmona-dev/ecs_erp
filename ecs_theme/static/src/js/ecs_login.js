/* ═══════════════════════════════════════════════════
   ECS Login — Micro-interactions & Animations
   phillipos1212@gmail.com © 2025
   ═══════════════════════════════════════════════════ */

(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        // Only run on login page
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

        /* ── 3. Glow Parallax on Mouse Move ────────────── */
        const glow = document.querySelector('.ecs-bg-glow');
        const glowLeft = document.querySelector('.ecs-bg-glow-left');
        const glowCard = document.querySelector('.ecs-bg-glow-card');
        
        document.addEventListener('mousemove', function (e) {
            const cx = window.innerWidth  / 2;
            const cy = window.innerHeight / 2;
            const dx = (e.clientX - cx) / cx;
            const dy = (e.clientY - cy) / cy;
            
            if (glow)     glow.style.transform     = `translate(${dx * 25}px, ${dy * 25}px)`;
            if (glowLeft) glowLeft.style.transform = `translate(${dx * -15}px, ${dy * -15}px)`;
            if (glowCard) glowCard.style.transform = `translate(${dx * 10}px, ${dy * 10}px) translate(-50%, -50%)`;
        });
    });
})();
