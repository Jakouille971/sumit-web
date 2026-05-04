// SUM'IT — main.js

// Navigation active selon la page courante
document.addEventListener('DOMContentLoaded', () => {
  const links = document.querySelectorAll('.nav-link');
  const current = window.location.pathname.split('/').pop();
  links.forEach(link => {
    const href = link.getAttribute('href').split('/').pop();
    if (href === current) {
      links.forEach(l => l.classList.remove('active'));
      link.classList.add('active');
    }
  });
});

// Navbar scroll effect
window.addEventListener('scroll', () => {
  const nav = document.querySelector('.nav');
  if (nav) {
    if (window.scrollY > 60) {
      nav.style.background = 'rgba(10, 21, 32, 0.98)';
    } else {
      nav.style.background = 'rgba(13, 27, 42, 0.92)';
    }
  }
});
