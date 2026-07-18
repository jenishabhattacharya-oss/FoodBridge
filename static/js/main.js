// Navbar transparency on scroll
const nav = document.getElementById('mainNav');

if (nav) {
    window.addEventListener('scroll', () => {
        nav.classList.toggle('scrolled', window.scrollY > 60);
    });
}

// Reveal animations
const observer = new IntersectionObserver(
    (entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    },
    {
        threshold: 0.1,
    }
);

document.querySelectorAll('.reveal').forEach((element) => observer.observe(element));

// Bootstrap ScrollSpy
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('mainNav')) {
        new bootstrap.ScrollSpy(document.body, {
            target: '#mainNav',
            offset: 90,
        });
    }
});
