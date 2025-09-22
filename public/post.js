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
    const coverContainer = document.getElementById('cover-container');

    if (coverContainer && meta.cover) {
      if (meta.cover.includes('youtube.com')) {
        const videoId = new URL(meta.cover).searchParams.get('v');
        if (videoId) {
          const iframe = document.createElement('iframe');
          iframe.src = `https://www.youtube.com/embed/${videoId}`;
          iframe.className = 'w-full h-full';
          iframe.frameBorder = '0';
          iframe.allow =
            'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
          iframe.allowFullscreen = true;
          coverContainer.appendChild(iframe);
        }
      } else {
        const img = document.createElement('img');
        img.src = meta.cover;
        img.alt = meta.title;
        img.className = 'w-full h-full object-contain bg-white';
        coverContainer.appendChild(img);
      }
    }

    // 載入對應的 markdown 文章
    let md = await fetch(`/posts/${slug}.md`).then(r => r.text());

    // === Step 1: 抽出摘要區塊 ===
    const summaryRegex = /<!-- summary -->([\s\S]*?)<!-- endsummary -->/;
    const match = md.match(summaryRegex);
    let summaryHTML = "";
    if (match) {
      const rawSummary = match[1].trim();

      // 把每行拆成 <li>
      const summaryPoints = rawSummary
        .split(/\n+/)
        .filter(line => line.trim())
        .map(line => `<li>${line.replace(/^[-*]\s*/, "").trim()}</li>`)
        .join("");

      summaryHTML = `
  <div class="prose bg-pink-50 p-4 rounded-lg border-l-4 border-pink-400 mb-8 prose-headings:mt-0 prose-p:mt-2">
    <h2 class="text-xl font-bold text-pink-600 mb-3">重點摘要</h2>
    <ul class="list-disc pl-5 space-y-2 text-gray-700">
      ${summaryPoints}
    </ul>
  </div>
`;


      // 移除原始 summary
      md = md.replace(summaryRegex, "");
    }

    // === Step 2: 自動轉換「說話者」段落 ===
    const lines = md.split('\n');
    let processed = '';
    let currentSpeaker = null;
    let buffer = [];

    const isSpeakerLine = line => {
      const trimmed = line.trim();
      if (!trimmed) return false;
      if (trimmed.startsWith('#') || trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('> ')) return false;
      if (trimmed.length > 60) return false;
      if (/[。！？；，,.]/.test(trimmed)) return false;
      return true;
    };

    const flush = () => {
      if (currentSpeaker) {
        const content = buffer.join('\n').trim();
        const paragraphs = content
          ? content
              .split(/\n\s*\n/)
              .map(p => `<p>${p.trim()}</p>`)
              .join('\n')
          : '';
        processed += `\n<h3>${currentSpeaker}</h3>\n`;
        processed += paragraphs ? `<blockquote>\n${paragraphs}\n</blockquote>\n` : '<blockquote></blockquote>\n';
      } else if (buffer.length) {
        processed += buffer.join('\n');
        processed += '\n';
      }
      currentSpeaker = null;
      buffer = [];
    };

    for (const line of lines) {
      if (isSpeakerLine(line)) {
        flush();
        currentSpeaker = line.trim();
      } else {
        buffer.push(line);
      }
    }
    flush();

    md = processed.trim();

    // === Step 3: 組合輸出 ===
    content.innerHTML = summaryHTML + marked.parse(md);

  } catch (err) {
    document.getElementById('title').innerText = '載入文章失敗';
    console.error("讀取文章時出錯:", err);
    content.innerHTML = `<p class="text-red-500">載入文章失敗，請稍後再試。</p>`;
  }
}

document.addEventListener('DOMContentLoaded', loadPostPage);
