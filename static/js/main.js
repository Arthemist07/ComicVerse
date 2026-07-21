// Theme Toggle
function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
  const btn = document.getElementById('themeToggle');
  if (btn) btn.textContent = next === 'dark' ? '🌙' : '☀️';
  if (typeof currentUser !== 'undefined' && currentUser) {
    fetch('/api/profile/update', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: `theme=${next}`
    });
  }
}

// Initialize theme
const savedTheme = localStorage.getItem('theme') || 'dark';
document.documentElement.setAttribute('data-theme', savedTheme);
const themeBtn = document.getElementById('themeToggle');
if (themeBtn) themeBtn.textContent = savedTheme === 'dark' ? '🌙' : '☀️';

// Toast Notification
function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

// Favorites Toggle
function toggleFavorite(comicId, btn) {
  fetch(`/comic/${comicId}/favorite`, { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.favorited) {
        btn.innerHTML = '♥ Favorited';
        btn.classList.add('favorited');
        showToast('Added to favorites!');
      } else {
        btn.innerHTML = '♡ Add to Favorites';
        btn.classList.remove('favorited');
        showToast('Removed from favorites');
      }
    })
    .catch(() => showToast('Please login first', 'error'));
}

// Notifications
function toggleNotifications() {
  const dropdown = document.getElementById('notifDropdown');
  dropdown.classList.toggle('show');
  if (dropdown.classList.contains('show')) {
    loadNotifications();
  }
}

function loadNotifications() {
  fetch('/api/notifications')
    .then(r => r.json())
    .then(notifs => {
      const container = document.getElementById('notifList');
      const badge = document.getElementById('notifBadge');
      const unread = notifs.filter(n => !n.is_read).length;
      badge.textContent = unread || '';
      badge.style.display = unread ? 'block' : 'none';
      container.innerHTML = notifs.length ? notifs.map(n => `
        <div class="notif-item ${n.is_read ? '' : 'unread'}" onclick="markRead(${n.id}); window.location='${n.link}'">
          <div style="font-size:14px">${n.message}</div>
          <div style="font-size:11px;color:var(--text-secondary);margin-top:4px">${new Date(n.created_at).toLocaleDateString()}</div>
        </div>
      `).join('') : '<div style="padding:24px;text-align:center;color:var(--text-secondary)">No notifications</div>';
    });
}

function markRead(id) {
  fetch(`/api/notifications/read/${id}`, { method: 'POST' });
}

function markAllRead() {
  fetch('/api/notifications/read-all', { method: 'POST' }).then(() => loadNotifications());
  showToast('All marked as read');
}

// Follow User
function toggleFollow(userId, btn) {
  fetch(`/api/follow/${userId}`, { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.following) {
        btn.textContent = 'Following';
        btn.classList.add('following');
      } else {
        btn.textContent = 'Follow';
        btn.classList.remove('following');
      }
    })
    .catch(e => showToast('Error', 'error'));
}

// Reader - Moving Panel / Zoom
let currentPage = 0;

function zoomPage(img) {
  img.classList.toggle('zoomed');
}

function prevPage() {
  const pages = document.querySelectorAll('.reader-page-img');
  if (currentPage > 0) {
    pages[currentPage].scrollIntoView({ behavior: 'smooth' });
    currentPage--;
  }
}

function nextPage() {
  const pages = document.querySelectorAll('.reader-page-img');
  if (currentPage < pages.length - 1) {
    currentPage++;
    pages[currentPage].scrollIntoView({ behavior: 'smooth' });
  }
}

// Keyboard shortcuts for reader
document.addEventListener('keydown', function(e) {
  if (e.key === 'ArrowLeft') prevPage();
  if (e.key === 'ArrowRight') nextPage();
});

// Search
let searchTimeout;
function searchComics(q) {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    if (q.length > 1) window.location.href = `/?q=${encodeURIComponent(q)}`;
  }, 500);
}

// Load history/favorites on profile
function loadHistory() {
  fetch('/api/history')
    .then(r => r.json())
    .then(data => {
      const el = document.getElementById('historyList');
      if (!el) return;
      el.innerHTML = data.map(h => `
        <a href="/read/${h.comic_id}/${h.chapter_id}" style="display:block;padding:8px 0;color:var(--text-primary);text-decoration:none">
          ${h.comic_title} - Ch. ${h.chapter_number}
        </a>
      `).join('') || '<p style="color:var(--text-secondary)">No reading history</p>';
    });
}

function loadFavorites() {
  fetch('/api/favorites')
    .then(r => r.json())
    .then(data => {
      const el = document.getElementById('favoritesList');
      if (!el) return;
      el.innerHTML = data.map(f => `
        <a href="/comic/${f.comic_id}" style="display:flex;align-items:center;gap:12px;padding:8px 0;color:var(--text-primary);text-decoration:none">
          <img src="${f.cover}" style="width:40px;height:56px;object-fit:cover;border-radius:4px">
          <span>${f.title}</span>
        </a>
      `).join('') || '<p style="color:var(--text-secondary)">No favorites yet</p>';
    });
}

// Genre selection
function filterGenre(genreId) {
  const url = new URL(window.location);
  if (genreId) url.searchParams.set('genre', genreId);
  else url.searchParams.delete('genre');
  window.location = url;
}

function sortComics(sort) {
  const url = new URL(window.location);
  url.searchParams.set('sort', sort);
  window.location = url;
}

// Admin - Page editor (simple rich text)
function insertPageUrls() {
  const urls = document.getElementById('pageUrls').value.trim().split('\n').filter(u => u);
  document.getElementById('pages').value = JSON.stringify(urls);
  showToast(`Added ${urls.length} pages`);
}

// User Menu
function toggleUserMenu() {
  document.getElementById('userDropdown').classList.toggle('show');
}

// Search overlay
function toggleSearch() {
  const overlay = document.getElementById('searchOverlay');
  const isHidden = overlay.style.display === 'none' || overlay.style.display === '';
  overlay.style.display = isHidden ? 'flex' : 'none';
  if (isHidden) setTimeout(() => document.getElementById('searchInput')?.focus(), 100);
  document.getElementById('searchResults').innerHTML = '';
}

function searchComics(q) {
  clearTimeout(searchTimeout);
  const results = document.getElementById('searchResults');
  if (q.length < 2) { results.innerHTML = ''; return; }
  searchTimeout = setTimeout(() => {
    fetch(`/api/search?q=${encodeURIComponent(q)}`)
      .then(r => r.json())
      .then(data => {
        results.innerHTML = data.map(c => `
          <a href="/comic/${c.id}" class="search-result-item" onclick="toggleSearch()">
            <img src="${c.cover}" onerror="this.style.display='none'">
            <div>
              <strong>${c.title_en}</strong>
              <div style="font-size:12px;color:var(--text-secondary)">${c.type} • ⭐ ${c.rating}</div>
            </div>
          </a>
        `).join('') || '<div style="color:var(--text-secondary);text-align:center;padding:20px">No comics found</div>';
      });
  }, 300);
}

// Overlay close on Escape and outside click
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    document.getElementById('searchOverlay').style.display = 'none';
    document.getElementById('userDropdown')?.classList.remove('show');
  }
});

// Auto-close dropdowns on click outside
document.addEventListener('click', function(e) {
  const notifBtn = document.getElementById('notifBtn');
  const dropdown = document.getElementById('notifDropdown');
  if (notifBtn && dropdown && !notifBtn.contains(e.target) && !dropdown.contains(e.target)) {
    dropdown.classList.remove('show');
  }
  const userBtn = document.querySelector('.user-menu-btn');
  const userDropdown = document.getElementById('userDropdown');
  if (userBtn && userDropdown && !userBtn.contains(e.target) && !userDropdown.contains(e.target)) {
    userDropdown.classList.remove('show');
  }
});
