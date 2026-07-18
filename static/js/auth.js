document.addEventListener('DOMContentLoaded', () => {
    initPasswordToggles();
    initFormSubmit();
    initInputEffects();
    initRoleCards();
});

/* ==========================================================
   Password Toggle
========================================================== */

function initPasswordToggles() {
    const toggles = document.querySelectorAll('.password-toggle');

    toggles.forEach((button) => {
        button.addEventListener('click', () => {
            const input = button.parentElement.querySelector('input');

            const icon = button.querySelector('i');

            if (input.type === 'password') {
                input.type = 'text';

                icon.classList.remove('bi-eye');
                icon.classList.add('bi-eye-slash');
            } else {
                input.type = 'password';

                icon.classList.remove('bi-eye-slash');
                icon.classList.add('bi-eye');
            }
        });
    });
}

/* ==========================================================
   Submit Loading State
========================================================== */

function initFormSubmit() {
    const form = document.querySelector('form');

    if (!form) return;

    form.addEventListener('submit', () => {
        const button = form.querySelector("button[type='submit']");

        if (!button) return;

        button.disabled = true;

        button.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2"></span>
            Please wait...
        `;
    });
}

/* ==========================================================
   Input Focus Effect
========================================================== */

function initInputEffects() {
    const inputs = document.querySelectorAll('.form-control, .form-select');

    inputs.forEach((input) => {
        input.addEventListener('focus', () => {
            input.parentElement.classList.add('focused');
        });

        input.addEventListener('blur', () => {
            input.parentElement.classList.remove('focused');
        });
    });
}

/* ==========================================================
   Role Card Animation
========================================================== */

function initRoleCards() {
    const cards = document.querySelectorAll('.role-card');

    cards.forEach((card) => {
        card.addEventListener('click', () => {
            cards.forEach((c) => c.classList.remove('selected'));

            card.classList.add('selected');
        });
    });
}
