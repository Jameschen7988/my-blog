document.addEventListener('DOMContentLoaded', () => {
  const menuToggle = document.getElementById('menu-toggle');
  const mobileMenu = document.getElementById('mobile-menu');

  if (!menuToggle || !mobileMenu) return;

  const closeMenu = () => {
    if (mobileMenu.classList.contains('hidden')) return;
    mobileMenu.classList.add('hidden');
    menuToggle.setAttribute('aria-expanded', 'false');
  };

  const toggleMenu = event => {
    if (event) event.stopPropagation();
    const isHidden = mobileMenu.classList.toggle('hidden');
    menuToggle.setAttribute('aria-expanded', String(!isHidden));
  };

  menuToggle.type = 'button';
  menuToggle.setAttribute('aria-controls', 'mobile-menu');
  menuToggle.setAttribute('aria-expanded', 'false');

  menuToggle.addEventListener('click', toggleMenu);
  mobileMenu.addEventListener('click', event => event.stopPropagation());

  mobileMenu.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', closeMenu);
  });

  document.addEventListener('click', closeMenu);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') closeMenu();
  });
});
