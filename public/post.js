async function loadPostPage() {
  const content = document.getElementById('content');
  if (!content) return;

  const params = new URLSearchParams(location.search);
  const slug = params.get('slug');
  if (!slug) {
    document.getElementById('title').innerText = '未找到文章';
    return;
  }

  try {
    const posts = await fetch('/posts/posts.json').then(r => r.json());
    const meta = posts.find(p => p.slug === slug);

    if (!meta) {
      document.getElementById('title').innerText = '未找到文章';
      return;
    }

    // 設定標題與封面
    document.getElementById('title').innerText = meta.title;
    const cover = document.getElementById('cover');
    if (cover) {
      cover.src = meta.cover;
      cover.alt = meta.title;
    }

    // 載入對應的 markdown 文章
    const md = await fetch(`/posts/${slug}.md`).then(r => r.text());
    content.innerHTML = marked.parse(md);
  } catch (err) {
    document.getElementById('title').innerText = '載入文章失敗';
    console.error("讀取文章時出錯:", err);
    content.innerHTML = `<p class="text-red-500">載入文章失敗，請稍後再試。</p>`;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadPostPage();
});

