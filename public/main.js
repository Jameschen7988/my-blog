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
    event?.stopPropagation();
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

// ==================== 首頁文章卡片載入 ====================
async function loadHomePage() {
  const grid = document.getElementById('card-grid');
  if (!grid) return;

  // 初始提示
  grid.innerHTML = `<p class="text-gray-500">載入中...</p>`;

  try {
    const posts = await fetch('/posts/posts.json').then(r => r.json());
    grid.innerHTML = posts.map(p => {
      let coverMarkup = '';

      if (p.cover) {
        try {
          const url = new URL(p.cover, location.origin);
          let videoId = null;

          if (url.hostname.includes('youtube.com')) {
            videoId = url.searchParams.get('v');
          } else if (url.hostname === 'youtu.be') {
            videoId = url.pathname.replace('/', '');
          }

          if (videoId) {
            coverMarkup = `
        <div class="relative aspect-video bg-black">
          <iframe
            src="https://www.youtube.com/embed/${videoId}"
            class="absolute inset-0 w-full h-full"
            title="${p.title}"
            frameborder="0"
            loading="lazy"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen
          ></iframe>
        </div>
      `;
          }
        } catch (err) {
          console.warn('無法解析封面網址', p.cover, err);
        }
      }

      if (!coverMarkup && p.cover) {
        coverMarkup = `<img src="${p.cover}" alt="${p.title}" class="w-full bg-white">`;
      }

      return `
      <article class="overflow-hidden border border-gray-200 rounded-lg shadow hover:shadow-lg">
        ${coverMarkup}
        <div class="p-6">
          <h3 class="text-xl font-bold mb-2">${p.title}</h3>
          <p class="text-gray-700 mb-4 text-sm">${p.excerpt}</p>
          <a href="/post.html?slug=${p.slug}" class="text-sm font-semibold hover:underline">Read More</a>
        </div>
      </article>
    `;
    }).join('');
  } catch (err) {
    console.error("載入文章失敗:", err);
    grid.innerHTML = `<p class="text-red-500">無法載入文章</p>`;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initMobileNavigation();
  loadHomePage();
});
