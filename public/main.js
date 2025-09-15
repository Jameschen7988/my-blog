// ==================== 首頁文章卡片載入 ====================
async function loadHomePage() {
  const grid = document.getElementById('card-grid');
  if (!grid) return;

  // 初始提示
  grid.innerHTML = `<p class="text-gray-500">載入中...</p>`;

  try {
    const posts = await fetch('/posts/posts.json').then(r => r.json());
    grid.innerHTML = posts.map(p => `
      <article class="overflow-hidden border border-gray-200 rounded-lg shadow hover:shadow-lg">
        <img src="${p.cover}" alt="${p.title}" class="w-full bg-white">
        <div class="p-6">
          <h3 class="text-xl font-bold mb-2">${p.title}</h3>
          <p class="text-gray-700 mb-4 text-sm">${p.excerpt}</p>
          <a href="/post.html?slug=${p.slug}" class="text-sm font-semibold hover:underline">Read More</a>
        </div>
      </article>
    `).join('');
  } catch (err) {
    console.error("載入文章失敗:", err);
    grid.innerHTML = `<p class="text-red-500">無法載入文章</p>`;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadHomePage();
});
