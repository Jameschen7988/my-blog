function initMobileNavigation() {
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
}

async function renderCategoryPage() {
  const container = document.getElementById('category-sections');
  if (!container) return;

  container.innerHTML = `<p class="text-gray-500">載入中...</p>`;

  try {
    const posts = await fetch('/posts/posts.json').then(res => res.json());

    const groups = new Map();

    posts.forEach(post => {
      const category = (post.tags && post.tags[0]) || '未分類';
      if (!groups.has(category)) groups.set(category, []);
      groups.get(category).push(post);
    });

    const sections = Array.from(groups.entries()).map(([category, items]) => {
      items.sort((a, b) => new Date(b.date) - new Date(a.date));

      const links = items
        .map(item => `<li><a href="/post.html?slug=${item.slug}" class="text-pink-600 hover:text-pink-500 hover:underline">${item.title}</a></li>`)
        .join('');

      return `
        <section>
          <h2 class="text-xl font-semibold mb-3">${category}</h2>
          <ul class="list-disc pl-5 space-y-2 text-sm md:text-base">${links}</ul>
        </section>
      `;
    });

    container.innerHTML = sections.join('');
  } catch (err) {
    console.error('載入分類頁面失敗:', err);
    container.innerHTML = `<p class="text-red-500">無法載入分類資料。</p>`;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initMobileNavigation();
  renderCategoryPage();
});
