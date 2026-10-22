/**
 * PyAnimeIndo Web - Netflix-Style Application Logic
 */

const API_BASE = ''; // Same origin

// Application State
const state = {
  provider: localStorage.getItem('pyanimeindo_provider') || 'samehadaku',
  currentView: 'home',
  ongoing: [],
  schedule: {},
  genres: [],
  saved: [],
  history: [],
  activeAnime: null,
  activeEpisode: null,
  activeQuality: '720p',
  qualities: {},
  searchDebounce: null,
};

// DOM Cache
const dom = {
  navbar: document.getElementById('navbar'),
  providerBtns: document.querySelectorAll('.provider-btn'),
  navItems: document.querySelectorAll('.nav-item, .mobile-nav-item'),
  searchInput: document.getElementById('searchInput'),
  
  // Views
  viewHome: document.getElementById('viewHome'),
  viewSchedule: document.getElementById('viewSchedule'),
  viewGenres: document.getElementById('viewGenres'),
  viewMyList: document.getElementById('viewMyList'),
  viewHistory: document.getElementById('viewHistory'),
  viewSearch: document.getElementById('viewSearch'),
  
  // Billboard
  billboard: document.getElementById('billboard'),
  billboardTitle: document.getElementById('billboardTitle'),
  billboardEps: document.getElementById('billboardEps'),
  billboardDay: document.getElementById('billboardDay'),
  billboardSynopsis: document.getElementById('billboardSynopsis'),
  billboardPlayBtn: document.getElementById('billboardPlayBtn'),
  billboardInfoBtn: document.getElementById('billboardInfoBtn'),
  billboardSaveBtn: document.getElementById('billboardSaveBtn'),
  
  // Rows
  rowOngoing: document.getElementById('rowOngoing'),
  rowToday: document.getElementById('rowToday'),
  rowSaved: document.getElementById('rowSaved'),
  rowHistory: document.getElementById('rowHistory'),
  
  // Modals
  detailModal: document.getElementById('detailModal'),
  playerModal: document.getElementById('playerModal'),
  
  // Toast
  toast: document.getElementById('toast'),
  toastText: document.getElementById('toastText'),
};

// ==========================================================================
// Initialization
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
  setupNavbar();
  setupProviderToggle();
  setupNavigation();
  setupSearch();
  setupModals();
  loadInitialData();
});

function setupNavbar() {
  window.addEventListener('scroll', () => {
    if (window.scrollY > 40) {
      dom.navbar.classList.add('scrolled');
    } else {
      dom.navbar.classList.remove('scrolled');
    }
  });
}

function setupProviderToggle() {
  dom.providerBtns.forEach(btn => {
    if (btn.dataset.provider === state.provider) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }

    btn.addEventListener('click', () => {
      const p = btn.dataset.provider;
      if (state.provider !== p) {
        state.provider = p;
        localStorage.setItem('pyanimeindo_provider', p);
        dom.providerBtns.forEach(b => b.classList.toggle('active', b.dataset.provider === p));
        showToast(`Provider berganti ke: ${p === 'samehadaku' ? 'Samehadaku' : 'Otakudesu'}`);
        loadInitialData();
      }
    });
  });
}

function setupNavigation() {
  dom.navItems.forEach(item => {
    item.addEventListener('click', () => {
      const view = item.dataset.view;
      if (view) {
        switchView(view);
      }
    });
  });
}

function switchView(viewName) {
  state.currentView = viewName;
  
  // Update active state in nav
  dom.navItems.forEach(item => {
    item.classList.toggle('active', item.dataset.view === viewName);
  });

  // Hide all views
  [
    dom.viewHome, dom.viewSchedule, dom.viewGenres, 
    dom.viewMyList, dom.viewHistory, dom.viewSearch
  ].forEach(el => el && (el.style.display = 'none'));

  window.scrollTo({ top: 0, behavior: 'smooth' });

  if (viewName === 'home') {
    dom.viewHome.style.display = 'block';
  } else if (viewName === 'schedule') {
    dom.viewSchedule.style.display = 'block';
    renderScheduleView();
  } else if (viewName === 'genres') {
    dom.viewGenres.style.display = 'block';
    renderGenresView();
  } else if (viewName === 'mylist') {
    dom.viewMyList.style.display = 'block';
    renderMyListView();
  } else if (viewName === 'history') {
    dom.viewHistory.style.display = 'block';
    renderHistoryView();
  } else if (viewName === 'search') {
    dom.viewSearch.style.display = 'block';
  }
}

// ==========================================================================
// Data Fetching & Rendering
// ==========================================================================
async function loadInitialData() {
  showLoadingInRow(dom.rowOngoing);
  showLoadingInRow(dom.rowToday);

  try {
    // 1. Fetch Ongoing Anime
    const ongoingRes = await fetch(`${API_BASE}/api/ongoing?page=1&provider=${state.provider}`);
    const ongoingData = await ongoingRes.json();
    if (ongoingData.success && ongoingData.data.length > 0) {
      state.ongoing = ongoingData.data;
      renderBillboard(state.ongoing[0]);
      renderCardRow(dom.rowOngoing, state.ongoing);
    }

    // 2. Fetch Schedule
    const schedRes = await fetch(`${API_BASE}/api/schedule?provider=${state.provider}`);
    const schedData = await schedRes.json();
    if (schedData.success) {
      state.schedule = schedData.data;
      renderTodayRow();
    }

    // 3. Fetch Saved & History
    await fetchSavedList();
    await fetchHistoryList();

    // 4. Fetch Genres list in background
    const genreRes = await fetch(`${API_BASE}/api/genres?provider=${state.provider}`);
    const genreData = await genreRes.json();
    if (genreData.success) {
      state.genres = genreData.data;
    }
  } catch (err) {
    console.error('Error loading initial data:', err);
    showToast('Gagal memuat data dari server.');
  }
}

// Render Billboard
function renderBillboard(anime) {
  if (!anime) return;
  
  dom.billboard.style.backgroundImage = `url('${anime.img}')`;
  dom.billboardTitle.textContent = anime.title;
  dom.billboardEps.textContent = anime.eps || 'Rilis Baru';
  dom.billboardDay.textContent = anime.hari ? `Hari ${anime.hari}` : 'Sedang Tayang';
  
  // Set fallback or teaser synopsis
  dom.billboardSynopsis.textContent = `Saksikan serial anime terbaru ${anime.title} subtitle Indonesia kualitas jernih hingga 1080p tanpa jeda iklan.`;

  dom.billboardPlayBtn.onclick = () => openDetailModal(anime.url, true);
  dom.billboardInfoBtn.onclick = () => openDetailModal(anime.url);
  dom.billboardSaveBtn.onclick = () => toggleBookmark(anime);
  
  updateSaveBtnState(dom.billboardSaveBtn, anime.url);
}

// Render Horizontal Card Row
function renderCardRow(container, items) {
  container.innerHTML = '';
  if (!items || items.length === 0) {
    container.innerHTML = '<div class="empty-state" style="padding: 20px;"><p>Belum ada data tersedia.</p></div>';
    return;
  }

  items.forEach(anime => {
    const card = document.createElement('div');
    card.className = 'anime-card';
    card.innerHTML = `
      <img class="card-poster" src="${anime.img}" alt="${anime.title}" loading="lazy" onerror="this.src='https://via.placeholder.com/200x300?text=Anime+Indo'"/>
      <div class="card-badges">
        ${anime.hari ? `<span class="card-day-badge">${anime.hari}</span>` : ''}
        ${anime.eps ? `<span class="card-eps-badge">${anime.eps}</span>` : ''}
      </div>
      <div class="card-gradient-overlay">
        <h4 class="card-title">${anime.title}</h4>
        <div class="card-meta-row">
          <span class="badge-match">98% Cocok</span>
          <span class="card-rating">★ 4.8</span>
        </div>
      </div>
    `;
    card.addEventListener('click', () => openDetailModal(anime.url));
    container.appendChild(card);
  });
}

function renderTodayRow() {
  const dayNames = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];
  const todayDay = dayNames[new Date().getDay()];
  const todayAnime = state.schedule[todayDay] || [];
  
  const todayTitle = document.getElementById('todayRowTitle');
  if (todayTitle) {
    todayTitle.textContent = `Jadwal Rilis Hari Ini (${todayDay})`;
  }

  if (todayAnime.length > 0) {
    renderCardRow(dom.rowToday, todayAnime);
  } else {
    // If today is empty, show Monday or any populated day
    const anyDay = Object.keys(state.schedule).find(d => state.schedule[d]?.length > 0) || 'Senin';
    renderCardRow(dom.rowToday, state.schedule[anyDay] || []);
  }
}

// Horizontal Scroll Slider Helpers
window.slideRow = function(trackId, direction) {
  const track = document.getElementById(trackId);
  if (track) {
    const scrollAmount = track.clientWidth * 0.75;
    track.scrollBy({ left: direction * scrollAmount, behavior: 'smooth' });
  }
};

// ==========================================================================
// Anime Detail Modal
// ==========================================================================
async function openDetailModal(url, autoPlay = false) {
  dom.detailModal.classList.add('active');
  const modalHero = document.getElementById('modalHero');
  const modalTitle = document.getElementById('modalTitle');
  const modalSynopsis = document.getElementById('modalSynopsis');
  const modalMetaList = document.getElementById('modalMetaList');
  const modalEpisodesGrid = document.getElementById('modalEpisodesGrid');
  const modalSaveBtn = document.getElementById('modalSaveBtn');
  const modalPlayLatestBtn = document.getElementById('modalPlayLatestBtn');

  // Loading state
  modalTitle.textContent = 'Memuat data anime...';
  modalSynopsis.textContent = 'Mengambil sinopsis dan daftar episode langsung dari server...';
  modalEpisodesGrid.innerHTML = '<div class="netflix-spinner" style="margin: 20px auto;"></div>';
  modalMetaList.innerHTML = '';

  try {
    const res = await fetch(`${API_BASE}/api/episodes?url=${encodeURIComponent(url)}`);
    const json = await res.json();
    if (!json.success || !json.data) {
      modalTitle.textContent = 'Gagal memuat detail anime';
      return;
    }

    const data = json.data;
    state.activeAnime = { ...data, url: url };

    // Header & Meta
    modalHero.style.backgroundImage = `url('${data.cover}')`;
    modalTitle.textContent = data.title;
    modalSynopsis.textContent = data.sinopsis || 'Sinopsis belum tersedia untuk anime ini.';

    // Parse info metadata lines
    let metaHtml = '';
    if (data.info) {
      data.info.split('\n').forEach(line => {
        if (line.includes(':')) {
          const [key, val] = line.split(':');
          if (val && val.trim()) {
            metaHtml += `
              <div class="modal-meta-item">
                <span class="modal-meta-label">${key.trim()}</span>
                <span class="modal-meta-value">${val.trim()}</span>
              </div>
            `;
          }
        }
      });
    }
    modalMetaList.innerHTML = metaHtml;

    // Save Button
    modalSaveBtn.onclick = () => toggleBookmark(state.activeAnime);
    updateSaveBtnState(modalSaveBtn, url);

    // Render Episodes
    modalEpisodesGrid.innerHTML = '';
    if (data.episodes && data.episodes.length > 0) {
      modalPlayLatestBtn.style.display = 'inline-flex';
      modalPlayLatestBtn.onclick = () => {
        closeModal(dom.detailModal);
        playEpisode(data.episodes[0].url, data.title, data.episodes[0].title);
      };

      data.episodes.forEach(ep => {
        const epBtn = document.createElement('button');
        epBtn.className = 'episode-btn';
        
        // Check if episode is watched
        const isWatched = isEpisodeWatched(url, ep.url);
        if (isWatched) {
          epBtn.classList.add('watched');
        }

        epBtn.innerHTML = `
          <span>${ep.title}</span>
          ${ep.date ? `<span class="episode-date">${ep.date}</span>` : ''}
        `;
        epBtn.addEventListener('click', () => {
          closeModal(dom.detailModal);
          playEpisode(ep.url, data.title, ep.title);
        });
        modalEpisodesGrid.appendChild(epBtn);
      });

      if (autoPlay) {
        closeModal(dom.detailModal);
        playEpisode(data.episodes[0].url, data.title, data.episodes[0].title);
      }
    } else {
      modalPlayLatestBtn.style.display = 'none';
      modalEpisodesGrid.innerHTML = '<p class="empty-state" style="padding: 10px;">Episode belum tersedia atau rilis mendatang.</p>';
    }

  } catch (err) {
    console.error('Error fetching anime detail:', err);
    modalTitle.textContent = 'Koneksi bermasalah';
  }
}

// ==========================================================================
// Video Player Modal with Auto-Refresh & Multi-Server Failover
// ==========================================================================

let activePlayback = {
  candidates: [],
  currentIndex: 0,
  epUrl: '',
  animeTitle: '',
  epTitle: '',
  watchdogTimer: null,
  stallTimer: null,
  isResolvedPlaying: false
};

function clearPlaybackTimers() {
  if (activePlayback.watchdogTimer) {
    clearTimeout(activePlayback.watchdogTimer);
    activePlayback.watchdogTimer = null;
  }
  if (activePlayback.stallTimer) {
    clearTimeout(activePlayback.stallTimer);
    activePlayback.stallTimer = null;
  }
}

function showPlayerAlert(text, isSpinning = true) {
  const alertEl = document.getElementById('playerAlertBanner');
  const alertText = document.getElementById('playerAlertText');
  if (alertEl && alertText) {
    alertText.textContent = text;
    const icon = alertEl.querySelector('i');
    if (icon) {
      icon.className = isSpinning ? 'fa fa-sync-alt fa-spin' : 'fa fa-check-circle';
      icon.style.color = isSpinning ? 'var(--primary)' : 'var(--green-match)';
    }
    alertEl.style.display = 'flex';
  }
}

function hidePlayerAlert() {
  const alertEl = document.getElementById('playerAlertBanner');
  if (alertEl) {
    alertEl.style.display = 'none';
  }
}

async function playEpisode(epUrl, animeTitle, epTitle, forcedQuality = null) {
  clearPlaybackTimers();
  dom.playerModal.classList.add('active');

  const playerWrapper = document.getElementById('playerWrapper');
  const playerAnimeName = document.getElementById('playerAnimeName');
  const playerEpTitle = document.getElementById('playerEpTitle');
  const playerQualityPills = document.getElementById('playerQualityPills');
  const playerServerPills = document.getElementById('playerServerPills');
  const playerServerBadge = document.getElementById('playerServerBadge');
  const playerDownloadTags = document.getElementById('playerDownloadTags');
  const btnRefreshServer = document.getElementById('btnRefreshServer');

  playerAnimeName.textContent = animeTitle;
  playerEpTitle.textContent = epTitle;

  const chosenQuality = forcedQuality || state.activeQuality || '720p';
  state.activeQuality = chosenQuality;

  playerWrapper.innerHTML = `
    <div class="player-alert-banner" id="playerAlertBanner" style="display: flex;">
      <i class="fa fa-sync-alt fa-spin"></i>
      <span id="playerAlertText">Mencari server video terbaik untuk resolusi ${chosenQuality.toUpperCase()}...</span>
    </div>
    <div class="spinner-container" style="height: 100%;">
      <div class="netflix-spinner"></div>
      <p style="color: #fff; font-size: 0.95rem; margin-top: 14px; font-weight: 600;">
        Menyiapkan stream kualitas ${chosenQuality.toUpperCase()}...
      </p>
    </div>
  `;

  if (playerServerBadge) {
    playerServerBadge.innerHTML = `<i class="fa fa-server" style="color: var(--primary);"></i> Menghubungkan...`;
  }
  playerQualityPills.innerHTML = '';
  if (playerServerPills) playerServerPills.innerHTML = '';
  playerDownloadTags.innerHTML = '';

  state.activeEpisode = { epUrl, animeTitle, epTitle };
  activePlayback = {
    candidates: [],
    currentIndex: 0,
    epUrl,
    animeTitle,
    epTitle,
    watchdogTimer: null,
    stallTimer: null,
    isResolvedPlaying: false
  };

  // Setup Refresh Server Button
  if (btnRefreshServer) {
    btnRefreshServer.onclick = () => {
      btnRefreshServer.classList.add('rotating');
      setTimeout(() => btnRefreshServer.classList.remove('rotating'), 800);
      tryNextCandidate('Beralih ke server berikutnya sesuai permintaan pengguna...');
    };
  }

  // Save history
  recordHistory(epUrl, animeTitle, epTitle);

  try {
    const res = await fetch(`${API_BASE}/api/stream-candidates?ep_url=${encodeURIComponent(epUrl)}&quality=${chosenQuality}`);
    const data = await res.json();

    if (!data.success || !data.candidates || data.candidates.length === 0) {
      throw new Error(data.error || 'Tidak ada server streaming yang tersedia');
    }

    activePlayback.candidates = data.candidates;
    activePlayback.currentIndex = 0;
    state.qualities = data.downloads || {};

    // Render Quality Pills
    const availableQualities = data.available_qualities || ['1080p', '720p', '480p', '360p'];
    availableQualities.forEach(q => {
      const pill = document.createElement('button');
      pill.className = `q-pill ${q === chosenQuality ? 'active' : ''}`;
      pill.textContent = q.toUpperCase();
      pill.onclick = () => {
        document.querySelectorAll('.q-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        playEpisode(epUrl, animeTitle, epTitle, q);
      };
      playerQualityPills.appendChild(pill);
    });

    // Render Server Pills
    renderServerPills();

    // Render Download Links
    let dlHtml = '';
    Object.entries(state.qualities).forEach(([q, link]) => {
      if (link && typeof link === 'string' && link.startsWith('http')) {
        dlHtml += `
          <a href="${link}" target="_blank" rel="noopener noreferrer" class="dl-link-btn">
            <i class="fa fa-download"></i> ${q}
          </a>
        `;
      }
    });
    playerDownloadTags.innerHTML = dlHtml || '<span style="color: #666; font-size: 0.8rem;">Link unduhan alternatif tersedia</span>';

    // Mount Candidate 0
    mountCurrentCandidate();

  } catch (err) {
    console.error('Error fetching stream candidates:', err);
    playerWrapper.innerHTML = `
      <div class="empty-state" style="padding: 40px;">
        <i class="fa fa-exclamation-triangle" style="color: var(--primary); font-size: 2.2rem; margin-bottom: 12px;"></i>
        <h3 style="color: #fff; margin-bottom: 8px;">Gagal Menghubungi Server Video</h3>
        <p style="color: var(--text-dim); margin-bottom: 20px;">${err.message || 'Server anime sedang sibuk atau offline.'}</p>
        <button class="btn btn-primary" onclick="playEpisode('${epUrl}', '${animeTitle.replace(/'/g, "\\'")}', '${epTitle.replace(/'/g, "\\'")}')">
          <i class="fa fa-redo"></i> Coba Refresh Kembali
        </button>
      </div>
    `;
  }
}

function renderServerPills() {
  const container = document.getElementById('playerServerPills');
  const badge = document.getElementById('playerServerBadge');
  if (!container || !activePlayback.candidates.length) return;

  container.innerHTML = '';
  const current = activePlayback.candidates[activePlayback.currentIndex];

  if (badge && current) {
    badge.innerHTML = `<i class="fa fa-server" style="color: var(--primary);"></i> Server ${activePlayback.currentIndex + 1}/${activePlayback.candidates.length}: <strong>${current.name}</strong>`;
  }

  activePlayback.candidates.forEach((cand, idx) => {
    const btn = document.createElement('button');
    btn.className = `s-pill ${idx === activePlayback.currentIndex ? 'active' : ''}`;
    let shortLabel = `Server ${idx + 1}`;
    if (cand.type === 'iframe') {
      shortLabel += ' (Embed CDN)';
    } else if (cand.id.includes('proxy')) {
      shortLabel += ` (Proxy ${cand.quality.toUpperCase()})`;
    } else {
      shortLabel += ` (Direct ${cand.quality.toUpperCase()})`;
    }
    btn.textContent = shortLabel;
    btn.title = cand.name;
    btn.onclick = () => {
      clearPlaybackTimers();
      activePlayback.currentIndex = idx;
      mountCurrentCandidate();
    };
    container.appendChild(btn);
  });
}

function mountCurrentCandidate() {
  clearPlaybackTimers();
  const playerWrapper = document.getElementById('playerWrapper');
  const current = activePlayback.candidates[activePlayback.currentIndex];

  if (!current) {
    playerWrapper.innerHTML = `
      <div class="empty-state" style="padding: 40px;">
        <i class="fa fa-info-circle" style="color: var(--primary); font-size: 2rem; margin-bottom: 12px;"></i>
        <p>Semua server video telah dicoba. Silakan gunakan link unduhan di bawah atau ganti resolusi.</p>
        <button class="btn btn-primary" style="margin-top: 14px;" onclick="playEpisode(activePlayback.epUrl, activePlayback.animeTitle, activePlayback.epTitle, '480p')">
          <i class="fa fa-play"></i> Coba Kualitas 480p
        </button>
      </div>
    `;
    return;
  }

  renderServerPills();
  showPlayerAlert(`Menghubungkan ke ${current.name}...`, true);

  if (current.type === 'video') {
    // HTML5 Video with auto-fallback watchdog
    playerWrapper.innerHTML = `
      <div class="player-alert-banner" id="playerAlertBanner">
        <i class="fa fa-sync-alt fa-spin"></i>
        <span id="playerAlertText">Menghubungkan ke ${current.name}...</span>
      </div>
      <video id="activeVideoPlayer" class="player-element" controls autoplay playsinline controlsList="nodownload">
        <source src="${current.url}" type="video/mp4">
        Browser Anda tidak mendukung pemutar video HTML5.
      </video>
    `;

    const video = document.getElementById('activeVideoPlayer');
    activePlayback.isResolvedPlaying = false;

    // Success listeners
    const onPlaybackStarted = () => {
      if (!activePlayback.isResolvedPlaying) {
        activePlayback.isResolvedPlaying = true;
        clearPlaybackTimers();
        showPlayerAlert(`Sedang memutar dari ${current.name}`, false);
        setTimeout(hidePlayerAlert, 2500);
      }
    };

    video.addEventListener('playing', onPlaybackStarted);
    video.addEventListener('timeupdate', () => {
      if (video.currentTime > 0.3) {
        onPlaybackStarted();
      }
    });

    // Error listener: instant failover
    video.addEventListener('error', (e) => {
      console.warn('Video error on candidate:', current.name, e);
      if (!activePlayback.isResolvedPlaying) {
        tryNextCandidate(`Server ${current.name} gagal memuat video. Mencari server cadangan...`);
      }
    });

    // Stalled / Waiting listener: 4.5-second timeout
    video.addEventListener('stalled', () => {
      if (!activePlayback.isResolvedPlaying) {
        if (!activePlayback.stallTimer) {
          activePlayback.stallTimer = setTimeout(() => {
            if (!activePlayback.isResolvedPlaying && (video.paused || video.currentTime === 0)) {
              tryNextCandidate(`Server ${current.name} mengalami freeze/stalled. Mengganti server...`);
            }
          }, 4500);
        }
      }
    });

    video.addEventListener('waiting', () => {
      if (!activePlayback.isResolvedPlaying) {
        if (!activePlayback.stallTimer) {
          activePlayback.stallTimer = setTimeout(() => {
            if (!activePlayback.isResolvedPlaying && (video.paused || video.currentTime === 0)) {
              tryNextCandidate(`Server ${current.name} tidak merespons. Mengganti server...`);
            }
          }, 4500);
        }
      }
    });

    // Watchdog timer: If within 6 seconds the video hasn't played, auto-failover
    activePlayback.watchdogTimer = setTimeout(() => {
      if (!activePlayback.isResolvedPlaying && video.currentTime === 0) {
        console.warn('Watchdog timeout on candidate:', current.name);
        tryNextCandidate(`Koneksi ${current.name} lambat/terputus. Mencari server pengganti...`);
      }
    }, 6000);

  } else {
    // Embed iframe (Blogger / Desustream / Official CDN)
    playerWrapper.innerHTML = `
      <div class="player-alert-banner" id="playerAlertBanner">
        <i class="fa fa-check-circle" style="color: var(--green-match);"></i>
        <span id="playerAlertText">Terhubung ke ${current.name}</span>
      </div>
      <iframe id="activeIframePlayer" class="player-element" src="${current.url}" allowfullscreen frameborder="0" allow="autoplay; fullscreen; picture-in-picture"></iframe>
    `;
    setTimeout(hidePlayerAlert, 3000);
  }
}

function tryNextCandidate(reason) {
  clearPlaybackTimers();
  activePlayback.currentIndex++;
  if (activePlayback.currentIndex < activePlayback.candidates.length) {
    const nextCand = activePlayback.candidates[activePlayback.currentIndex];
    showToast(`🔄 ${reason || 'Mencari server cadangan...'}`);
    showPlayerAlert(`🔄 Mencoba Server ${activePlayback.currentIndex + 1}: ${nextCand.name}...`, true);
    mountCurrentCandidate();
  } else {
    // If all candidates in current resolution exhausted:
    if (state.activeQuality !== '480p') {
      showToast('Semua server untuk resolusi ini sibuk. Mencoba kualitas 480p otomatis...');
      playEpisode(activePlayback.epUrl, activePlayback.animeTitle, activePlayback.epTitle, '480p');
    } else {
      showToast('Semua server telah dicoba.');
      mountCurrentCandidate();
    }
  }
}


// ==========================================================================
// Views: Schedule, Genres, Bookmarks, History, Search
// ==========================================================================

// Schedule View
function renderScheduleView() {
  const container = document.getElementById('scheduleTabsContainer');
  const grid = document.getElementById('scheduleGrid');
  const days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"];
  
  container.innerHTML = '';
  days.forEach((day, index) => {
    const pill = document.createElement('button');
    pill.className = `tab-pill ${index === 0 ? 'active' : ''}`;
    pill.textContent = day;
    pill.onclick = () => {
      document.querySelectorAll('#scheduleTabsContainer .tab-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      renderScheduleDay(day);
    };
    container.appendChild(pill);
  });

  renderScheduleDay('Senin');
}

function renderScheduleDay(day) {
  const grid = document.getElementById('scheduleGrid');
  const animeList = state.schedule[day] || [];
  grid.innerHTML = '';
  
  if (animeList.length === 0) {
    grid.innerHTML = '<div class="empty-state" style="grid-column: 1 / -1;"><p>Tidak ada rilis anime untuk hari ini.</p></div>';
    return;
  }

  animeList.forEach(anime => {
    const card = document.createElement('div');
    card.className = 'anime-card';
    card.style.flex = 'auto';
    card.style.height = '260px';
    card.innerHTML = `
      <img class="card-poster" src="${anime.img}" alt="${anime.title}" loading="lazy"/>
      <div class="card-badges">
        <span class="card-day-badge">${day}</span>
        ${anime.eps ? `<span class="card-eps-badge">${anime.eps}</span>` : ''}
      </div>
      <div class="card-gradient-overlay">
        <h4 class="card-title">${anime.title}</h4>
      </div>
    `;
    card.onclick = () => openDetailModal(anime.url);
    grid.appendChild(card);
  });
}

// Genres View
function renderGenresView() {
  const chipsContainer = document.getElementById('genreChipsContainer');
  const grid = document.getElementById('genreGrid');
  chipsContainer.innerHTML = '';
  
  if (!state.genres || state.genres.length === 0) {
    chipsContainer.innerHTML = '<p class="empty-state">Memuat genre...</p>';
    return;
  }

  state.genres.forEach((genre, index) => {
    const chip = document.createElement('button');
    chip.className = `genre-chip ${index === 0 ? 'active' : ''}`;
    chip.textContent = genre.name;
    chip.onclick = () => {
      document.querySelectorAll('.genre-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      fetchGenreAnime(genre.path, genre.name);
    };
    chipsContainer.appendChild(chip);
  });

  if (state.genres.length > 0) {
    fetchGenreAnime(state.genres[0].path, state.genres[0].name);
  }
}

async function fetchGenreAnime(genrePath, genreName) {
  const grid = document.getElementById('genreGrid');
  const title = document.getElementById('genreSelectedTitle');
  if (title) title.textContent = `Anime Kategori: ${genreName}`;

  grid.innerHTML = '<div class="netflix-spinner" style="grid-column: 1 / -1; margin: 40px auto;"></div>';

  try {
    const res = await fetch(`${API_BASE}/api/genre-anime?path=${encodeURIComponent(genrePath)}&provider=${state.provider}`);
    const json = await res.json();
    grid.innerHTML = '';

    if (json.success && json.data.length > 0) {
      json.data.forEach(anime => {
        const card = document.createElement('div');
        card.className = 'anime-card';
        card.style.flex = 'auto';
        card.style.height = '260px';
        card.innerHTML = `
          <img class="card-poster" src="${anime.img}" alt="${anime.title}" loading="lazy"/>
          <div class="card-badges">
            ${anime.eps ? `<span class="card-eps-badge">${anime.eps}</span>` : ''}
          </div>
          <div class="card-gradient-overlay">
            <h4 class="card-title">${anime.title}</h4>
          </div>
        `;
        card.onclick = () => openDetailModal(anime.url);
        grid.appendChild(card);
      });
    } else {
      grid.innerHTML = '<div class="empty-state" style="grid-column: 1 / -1;"><p>Tidak ada anime di genre ini.</p></div>';
    }
  } catch (err) {
    console.error('Error fetching genre anime:', err);
    grid.innerHTML = '<div class="empty-state" style="grid-column: 1 / -1;"><p>Gagal memuat anime genre.</p></div>';
  }
}

// My List / Bookmarks View
async function fetchSavedList() {
  try {
    const res = await fetch(`${API_BASE}/api/saved`);
    const json = await res.json();
    if (json.success) {
      state.saved = json.data || [];
      renderCardRow(dom.rowSaved, state.saved);
    }
  } catch (err) {
    console.error('Error fetching saved anime:', err);
  }
}

function renderMyListView() {
  const grid = document.getElementById('myListGrid');
  grid.innerHTML = '';
  
  if (state.saved.length === 0) {
    grid.innerHTML = `
      <div class="empty-state" style="grid-column: 1 / -1;">
        <i class="fa fa-bookmark"></i>
        <h3>Belum Ada Anime Tersimpan</h3>
        <p style="margin-top: 8px;">Simpan anime favorit Anda dengan menekan tombol "+ Daftar Saya".</p>
      </div>
    `;
    return;
  }

  state.saved.forEach(anime => {
    const card = document.createElement('div');
    card.className = 'anime-card';
    card.style.flex = 'auto';
    card.style.height = '260px';
    card.innerHTML = `
      <img class="card-poster" src="${anime.img || anime.cover}" alt="${anime.title}" loading="lazy"/>
      <div class="card-gradient-overlay">
        <h4 class="card-title">${anime.title}</h4>
      </div>
    `;
    card.onclick = () => openDetailModal(anime.url);
    grid.appendChild(card);
  });
}

// History View
async function fetchHistoryList() {
  try {
    const res = await fetch(`${API_BASE}/api/history`);
    const json = await res.json();
    if (json.success) {
      state.history = json.data || [];
      renderCardRow(dom.rowHistory, state.history);
    }
  } catch (err) {
    console.error('Error fetching history:', err);
  }
}

function renderHistoryView() {
  const grid = document.getElementById('historyGrid');
  grid.innerHTML = '';

  if (state.history.length === 0) {
    grid.innerHTML = `
      <div class="empty-state" style="grid-column: 1 / -1;">
        <i class="fa fa-history"></i>
        <h3>Belum Ada Riwayat Menonton</h3>
        <p style="margin-top: 8px;">Episode yang Anda tonton akan otomatis tercatat di sini.</p>
      </div>
    `;
    return;
  }

  state.history.forEach(item => {
    const card = document.createElement('div');
    card.className = 'anime-card';
    card.style.flex = 'auto';
    card.style.height = '260px';
    card.innerHTML = `
      <img class="card-poster" src="${item.img || item.cover}" alt="${item.title}" loading="lazy"/>
      <div class="card-badges">
        <span class="card-eps-badge" style="background: var(--green-match);">✓ Terakhir Nonton</span>
      </div>
      <div class="card-gradient-overlay">
        <h4 class="card-title">${item.title}</h4>
      </div>
    `;
    card.onclick = () => openDetailModal(item.url);
    grid.appendChild(card);
  });
}

// ==========================================================================
// Search Implementation
// ==========================================================================
function setupSearch() {
  dom.searchInput.addEventListener('input', (e) => {
    const val = e.target.value.trim();
    clearTimeout(state.searchDebounce);
    if (!val) {
      if (state.currentView === 'search') {
        switchView('home');
      }
      return;
    }

    state.searchDebounce = setTimeout(() => {
      performSearch(val);
    }, 350);
  });
}

async function performSearch(query) {
  switchView('search');
  const grid = document.getElementById('searchGrid');
  const title = document.getElementById('searchQueryTitle');
  if (title) title.textContent = `Hasil Pencarian: "${query}"`;

  grid.innerHTML = '<div class="netflix-spinner" style="grid-column: 1 / -1; margin: 40px auto;"></div>';

  try {
    const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}&provider=${state.provider}`);
    const json = await res.json();
    grid.innerHTML = '';

    if (json.success && json.data.length > 0) {
      json.data.forEach(anime => {
        const card = document.createElement('div');
        card.className = 'anime-card';
        card.style.flex = 'auto';
        card.style.height = '260px';
        card.innerHTML = `
          <img class="card-poster" src="${anime.img}" alt="${anime.title}" loading="lazy" onerror="this.src='https://via.placeholder.com/200x300?text=Anime'"/>
          <div class="card-gradient-overlay">
            <h4 class="card-title">${anime.title}</h4>
          </div>
        `;
        card.onclick = () => openDetailModal(anime.url);
        grid.appendChild(card);
      });
    } else {
      grid.innerHTML = '<div class="empty-state" style="grid-column: 1 / -1;"><p>Tidak ada hasil untuk pencarian ini.</p></div>';
    }
  } catch (err) {
    console.error('Search error:', err);
    grid.innerHTML = '<div class="empty-state" style="grid-column: 1 / -1;"><p>Gagal melakukan pencarian.</p></div>';
  }
}

// ==========================================================================
// Bookmarks / Saved List Logic
// ==========================================================================
async function toggleBookmark(anime) {
  if (!anime || !anime.url) return;
  const isSaved = state.saved.some(item => item.url === anime.url);

  try {
    if (isSaved) {
      await fetch(`${API_BASE}/api/saved?url=${encodeURIComponent(anime.url)}`, { method: 'DELETE' });
      state.saved = state.saved.filter(item => item.url !== anime.url);
      showToast('Dihapus dari Daftar Tontonan');
    } else {
      const payload = {
        title: anime.title,
        url: anime.url,
        img: anime.img || anime.cover || '',
        hari: anime.hari || '',
        eps: anime.eps || ''
      };
      await fetch(`${API_BASE}/api/saved`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      state.saved.push(payload);
      showToast('Ditambahkan ke Daftar Tontonan');
    }

    renderCardRow(dom.rowSaved, state.saved);
    updateSaveBtnState(dom.billboardSaveBtn, anime.url);
    const modalSaveBtn = document.getElementById('modalSaveBtn');
    if (modalSaveBtn) updateSaveBtnState(modalSaveBtn, anime.url);

    if (state.currentView === 'mylist') {
      renderMyListView();
    }
  } catch (err) {
    console.error('Bookmark error:', err);
  }
}

function updateSaveBtnState(btn, url) {
  if (!btn || !url) return;
  const isSaved = state.saved.some(item => item.url === url);
  if (isSaved) {
    btn.innerHTML = '<i class="fa fa-check"></i> Tersimpan';
    btn.style.borderColor = 'var(--green-match)';
    btn.style.color = 'var(--green-match)';
  } else {
    btn.innerHTML = '<i class="fa fa-plus"></i> Daftar Saya';
    btn.style.borderColor = '';
    btn.style.color = '';
  }
}

// ==========================================================================
// History Helpers
// ==========================================================================
async function recordHistory(epUrl, animeTitle, epTitle) {
  try {
    const payload = {
      title: animeTitle,
      url: state.activeAnime?.url || epUrl,
      ep_url: epUrl,
      img: state.activeAnime?.cover || '',
    };
    await fetch(`${API_BASE}/api/history`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    fetchHistoryList();
  } catch (err) {
    console.error('History save error:', err);
  }
}

function isEpisodeWatched(animeUrl, epUrl) {
  const item = state.history.find(h => h.url === animeUrl);
  if (item && item.history) {
    return item.history.includes(epUrl);
  }
  return false;
}

// ==========================================================================
// Modal Handlers & Toast
// ==========================================================================
function setupModals() {
  document.querySelectorAll('.modal-close-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const modal = e.target.closest('.modal-backdrop');
      if (modal) closeModal(modal);
    });
  });

  // Close modal when clicking backdrop outside dialog
  document.querySelectorAll('.modal-backdrop').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeModal(modal);
      }
    });
  });

  // ESC key listener
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeModal(dom.detailModal);
      closeModal(dom.playerModal);
    }
  });
}

function closeModal(modal) {
  if (!modal) return;
  modal.classList.remove('active');
  
  // If player modal closed, stop video and clear timers
  if (modal === dom.playerModal) {
    clearPlaybackTimers();
    activePlayback.isResolvedPlaying = true;
    const playerWrapper = document.getElementById('playerWrapper');
    if (playerWrapper) playerWrapper.innerHTML = '';
  }
}


function showLoadingInRow(container) {
  container.innerHTML = `
    <div style="display: flex; gap: 12px; padding: 10px 0;">
      ${Array(5).fill(0).map(() => `
        <div class="anime-card" style="background: #1f1f23; opacity: 0.6; display: flex; align-items: center; justify-content: center;">
          <div class="netflix-spinner" style="width: 24px; height: 24px;"></div>
        </div>
      `).join('')}
    </div>
  `;
}

function showToast(message) {
  if (!dom.toast) return;
  dom.toastText.textContent = message;
  dom.toast.classList.add('show');
  setTimeout(() => {
    dom.toast.classList.remove('show');
  }, 3200);
}
