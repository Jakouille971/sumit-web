// SUM'IT — main.js

// Navigation active selon la page courante
document.addEventListener('DOMContentLoaded', () => {
  const links = document.querySelectorAll('.nav-link');
  const current = window.location.pathname.split('/').pop();
  links.forEach(link => {
    const href = (link.getAttribute('href') || '').split('/').pop();
    if (href === current) {
      links.forEach(l => l.classList.remove('active'));
      link.classList.add('active');
    }
  });
});

// Nav : passe en fond plein au scroll (la couleur vit dans le CSS, pas ici)
(function navScroll() {
  const update = () => {
    const nav = document.querySelector('.nav');
    if (nav) nav.classList.toggle('is-scrolled', window.scrollY > 40);
  };
  window.addEventListener('scroll', update, { passive: true });
  document.addEventListener('DOMContentLoaded', update);
})();
