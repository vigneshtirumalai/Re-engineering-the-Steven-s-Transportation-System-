/* ==========================================================================
   GalliMaps — Bangalore inner-road navigator
   --------------------------------------------------------------------------
   The whole trick lives in scoreRoute(): we ask a free router (OSRM) for
   several alternative paths, measure how much of each one runs on big
   arterial roads, and prefer the calmest one that isn't absurdly slower.
   No API keys, no backend. Everything runs in the browser.
   ========================================================================== */

(() => {
  'use strict';

  // ---- Bangalore constants ------------------------------------------------
  const BLR_CENTER = [12.9716, 77.5946];
  // viewbox (left,top,right,bottom) to bias search toward Bengaluru
  const BLR_VIEWBOX = '77.35,13.20,77.85,12.75';

  // Known arterials / ring roads / highways that carry the city's worst
  // traffic. If a route step's name contains one of these, we count that
  // distance as "main-road exposure". Lowercased, matched as substrings.
  const BLR_ARTERIALS = [
    'outer ring road', 'orr', 'inner ring road',
    'hosur road', 'hosur main road', 'nice road', 'nice ring road',
    'old airport road', 'hal airport road', 'airport road',
    'old madras road', 'sarjapur road', 'sarjapura road',
    'bannerghatta road', 'bannerghatta main road',
    'kanakapura road', 'mysore road', 'magadi road', 'tumkur road',
    'ballari road', 'bellary road', 'hebbal',
    'marathahalli', 'silk board', 'whitefield main road',
    'sarjapur main road', 'varthur road',
    'cmh road', '100 feet road', '80 feet road', '60 feet road',
    'double road', 'nrupathunga road', 'kasturba road',
    'mg road', 'mahatma gandhi road', 'residency road',
    'richmond road', 'brigade road', 'commercial street',
    'jc road', 'kh road', 'k h road', 'hosur',
    'vellara junction', 'st marks road', 'st mark\'s road',
    'race course road', 'sheshadri road', 'sankey road',
    'chord road', 'west of chord road', 'dr rajkumar road',
    'sampige road', 'margosa road', 'bull temple road',
    'palace road', 'cunningham road', 'infantry road',
    'queens road', 'millers road', 'coles road', 'wheeler road',
    'intermediate ring road', 'domlur',
  ];

  // Speed heuristic: a step covering a long distance at a high average speed
  // is almost certainly a big road, even if we don't recognise its name.
  const FAST_SPEED_KMPH = 42;     // sustained speed that implies an arterial
  const FAST_MIN_METERS = 400;    // ...only over a meaningful stretch

  // ---- State --------------------------------------------------------------
  let map, startMarker, endMarker;
  let routeLayers = [];           // Leaflet polylines, index-aligned to `routes`
  let routes = [];                // scored route objects
  let selectedIdx = 0;
  const points = { from: null, to: null }; // {lat, lon, label}

  // ---- DOM ----------------------------------------------------------------
  const $ = (id) => document.getElementById(id);
  const el = {
    from: $('from'), to: $('to'),
    fromSuggest: $('from-suggest'), toSuggest: $('to-suggest'),
    go: $('go'), swap: $('swap'), useLocation: $('use-location'),
    budget: $('budget'), budgetLabel: $('budget-label'),
    results: $('results'), cards: $('route-cards'),
    empty: $('empty'), status: $('status'),
    aboutToggle: $('about-toggle'), about: $('about'),
  };

  // ==========================================================================
  //  MAP
  // ==========================================================================
  function initMap() {
    map = L.map('map', { zoomControl: true, attributionControl: true })
           .setView(BLR_CENTER, 12);

    // Carto dark tiles read well against the panel; fall back to OSM style.
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      subdomains: 'abcd',
      maxZoom: 20,
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    }).addTo(map);
  }

  // ==========================================================================
  //  GEOCODING (Nominatim) — with lightweight debounce + Bangalore bias
  // ==========================================================================
  function debounce(fn, ms) {
    let t;
    return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
  }

  async function geocode(query) {
    const url = 'https://nominatim.openstreetmap.org/search'
      + '?format=json&addressdetails=1&limit=6&countrycodes=in'
      + '&viewbox=' + BLR_VIEWBOX + '&bounded=1'
      + '&q=' + encodeURIComponent(query);
    const res = await fetch(url, { headers: { 'Accept-Language': 'en' } });
    if (!res.ok) throw new Error('search failed');
    return res.json();
  }

  function renderSuggestions(listEl, items, which) {
    listEl.innerHTML = '';
    items.forEach((item) => {
      const li = document.createElement('li');
      const parts = item.display_name.split(',');
      const primary = parts.slice(0, 2).join(',');
      const secondary = parts.slice(2, 5).join(',').trim();
      li.innerHTML = `${primary}<small>${secondary}</small>`;
      li.addEventListener('mousedown', (e) => {
        e.preventDefault();
        const label = parts.slice(0, 3).join(',');
        points[which] = { lat: +item.lat, lon: +item.lon, label };
        (which === 'from' ? el.from : el.to).value = label;
        listEl.innerHTML = '';
        placePin(which);
      });
      listEl.appendChild(li);
    });
  }

  function wireSearch(inputEl, listEl, which) {
    const run = debounce(async () => {
      const q = inputEl.value.trim();
      if (q.length < 3) { listEl.innerHTML = ''; return; }
      try {
        const items = await geocode(q);
        renderSuggestions(listEl, items, which);
      } catch { /* silent — search is best-effort */ }
    }, 300);
    inputEl.addEventListener('input', run);
    inputEl.addEventListener('blur', () => setTimeout(() => { listEl.innerHTML = ''; }, 150));
  }

  // ==========================================================================
  //  PINS
  // ==========================================================================
  function pinIcon(color) {
    return L.divIcon({
      className: 'pin',
      html: `<div style="width:18px;height:18px;border-radius:50% 50% 50% 0;
             background:${color};transform:rotate(-45deg);
             border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.5)"></div>`,
      iconSize: [18, 18],
      iconAnchor: [9, 18],
    });
  }

  function placePin(which) {
    const p = points[which];
    if (!p) return;
    const latlng = [p.lat, p.lon];
    if (which === 'from') {
      if (startMarker) startMarker.setLatLng(latlng);
      else startMarker = L.marker(latlng, { icon: pinIcon('#3fb950') }).addTo(map);
    } else {
      if (endMarker) endMarker.setLatLng(latlng);
      else endMarker = L.marker(latlng, { icon: pinIcon('#f85149') }).addTo(map);
    }
    if (points.from && points.to) {
      map.fitBounds(L.latLngBounds([points.from.lat, points.from.lon],
                                   [points.to.lat, points.to.lon]).pad(0.25));
    } else {
      map.setView(latlng, 14);
    }
  }

  // ==========================================================================
  //  ROUTING (OSRM public server) + SCORING
  // ==========================================================================
  async function fetchRoutes() {
    const { from, to } = points;
    const coords = `${from.lon},${from.lat};${to.lon},${to.lat}`;
    const url = `https://router.project-osrm.org/route/v1/driving/${coords}`
      + '?alternatives=3&overview=full&geometries=geojson&steps=true&annotations=true';
    const res = await fetch(url);
    if (!res.ok) throw new Error('routing failed');
    const data = await res.json();
    if (data.code !== 'Ok' || !data.routes || !data.routes.length) {
      throw new Error('no route found');
    }
    return data.routes;
  }

  /**
   * Score a single OSRM route for "main-road exposure".
   * Returns meters spent on big roads and a 0..1 fraction of the trip.
   */
  function scoreRoute(route) {
    let mainMeters = 0;
    const hitNames = new Set();

    for (const leg of route.legs) {
      for (const step of leg.steps) {
        const dist = step.distance || 0;
        if (dist <= 0) continue;

        const name = (step.name || '').toLowerCase();
        const ref  = (step.ref  || '').toLowerCase();

        // 1) Named Bangalore arterial / ring road
        let isMain = false;
        for (const art of BLR_ARTERIALS) {
          if (name.includes(art)) { isMain = true; hitNames.add(titleCase(step.name)); break; }
        }

        // 2) Highway reference (NH 44, SH 35, etc.)
        if (!isMain && /\b(nh|sh|nice|orr)\b/.test(ref)) {
          isMain = true;
          if (step.name) hitNames.add(titleCase(step.name));
          else if (step.ref) hitNames.add(step.ref.toUpperCase());
        }

        // 3) Speed proxy: long, fast segment ⇒ big road
        if (!isMain && step.duration > 0) {
          const kmph = (dist / step.duration) * 3.6;
          if (kmph >= FAST_SPEED_KMPH && dist >= FAST_MIN_METERS) {
            isMain = true;
            if (step.name) hitNames.add(titleCase(step.name));
          }
        }

        if (isMain) mainMeters += dist;
      }
    }

    const fraction = route.distance > 0 ? mainMeters / route.distance : 0;
    return {
      distance: route.distance,          // meters
      duration: route.duration,          // seconds
      geometry: route.geometry,          // GeoJSON LineString
      mainMeters,
      mainFraction: fraction,
      mainRoads: [...hitNames].slice(0, 4),
    };
  }

  /**
   * Rank routes so the calmest acceptable one comes first.
   * "Acceptable" = within the user's time budget vs. the fastest option.
   */
  function rankRoutes(scored) {
    const fastest = scored.reduce((a, b) => (a.duration <= b.duration ? a : b));
    const budgetPct = +el.budget.value;                 // e.g. 50 => +50%
    const maxDuration = fastest.duration * (1 + budgetPct / 100);

    // Tag each route
    scored.forEach((r) => {
      r.isFastest = r === fastest;
      r.withinBudget = r.duration <= maxDuration + 1; // small epsilon
      r.extraPct = Math.round((r.duration / fastest.duration - 1) * 100);
    });

    // Preference: routes within budget, calmest first; then everything else
    // by calmness. The fastest is always kept as a comparison option.
    const withinBudget = scored.filter((r) => r.withinBudget)
      .sort((a, b) => a.mainFraction - b.mainFraction || a.duration - b.duration);
    const overBudget = scored.filter((r) => !r.withinBudget)
      .sort((a, b) => a.mainFraction - b.mainFraction);

    const ordered = [...withinBudget, ...overBudget];

    // Label the recommended (first) and the fastest
    ordered.forEach((r, i) => { r.rank = i; });
    return { ordered, fastest };
  }

  // ==========================================================================
  //  RENDER ROUTES
  // ==========================================================================
  function clearRouteLayers() {
    routeLayers.forEach((l) => map.removeLayer(l));
    routeLayers = [];
  }

  function drawRoutes() {
    clearRouteLayers();
    // Draw non-selected first (dim), selected last (bright, on top)
    routes.forEach((r, i) => {
      if (i === selectedIdx) return;
      routeLayers[i] = L.geoJSON(r.geometry, {
        style: { color: '#5b6570', weight: 5, opacity: 0.55 },
      }).addTo(map);
      routeLayers[i].on('click', () => selectRoute(i));
    });
    const sel = routes[selectedIdx];
    const selColor = sel.isFastest ? '#f0883e' : '#3fb950';
    routeLayers[selectedIdx] = L.geoJSON(sel.geometry, {
      style: { color: selColor, weight: 7, opacity: 0.95 },
    }).addTo(map);

    const coords = sel.geometry.coordinates.map((c) => [c[1], c[0]]);
    map.fitBounds(L.latLngBounds(coords).pad(0.15));
  }

  function selectRoute(i) {
    selectedIdx = i;
    drawRoutes();
    renderCards();
  }

  function renderCards() {
    el.cards.innerHTML = '';
    routes.forEach((r, i) => {
      const card = document.createElement('div');
      card.className = 'route-card' + (i === selectedIdx ? ' selected' : '')
        + (r.isFastest ? ' is-fastest' : '');

      const title = r.rank === 0 ? 'Quietest route'
        : r.isFastest ? 'Fastest route'
        : `Alternative ${i}`;
      const badge = r.rank === 0
        ? '<span class="route-badge badge-quiet">Recommended</span>'
        : r.isFastest ? '<span class="route-badge badge-fast">Fastest</span>' : '';

      const km = (r.distance / 1000).toFixed(1);
      const min = Math.round(r.duration / 60);
      const exposurePct = Math.round(r.mainFraction * 100);
      const extra = r.extraPct > 0 ? `+${r.extraPct}% time` : 'quickest';

      const roadsNote = r.mainRoads.length
        ? `Uses: ${r.mainRoads.join(', ')}`
        : 'Stays on smaller roads throughout';

      card.innerHTML = `
        <div class="route-top">
          <span class="route-title">${title}</span>
          ${badge}
        </div>
        <div class="route-stats">
          <div class="stat"><b>${min} min</b><span>${extra}</span></div>
          <div class="stat"><b>${km} km</b><span>distance</span></div>
          <div class="stat"><b>${exposurePct}%</b><span>on main roads</span></div>
        </div>
        <div class="exposure">
          <div class="exposure-bar">
            <div class="exposure-fill" style="width:${exposurePct}%"></div>
          </div>
          <div class="exposure-label">
            <span>${roadsNote}</span>
          </div>
        </div>`;
      card.addEventListener('click', () => selectRoute(i));
      el.cards.appendChild(card);
    });
  }

  // ==========================================================================
  //  MAIN FLOW
  // ==========================================================================
  async function findRoute() {
    if (!points.from || !points.to) {
      showStatus('Pick a start and a destination from the suggestions first.', true);
      return;
    }
    setBusy(true);
    hideStatus();
    try {
      const raw = await fetchRoutes();
      const scored = raw.map(scoreRoute);
      const { ordered } = rankRoutes(scored);
      routes = ordered;
      selectedIdx = 0;

      el.empty.hidden = true;
      el.results.hidden = false;
      drawRoutes();
      renderCards();
    } catch (err) {
      showStatus(prettyError(err), true);
    } finally {
      setBusy(false);
    }
  }

  function recomputeRanking() {
    if (!routes.length) return;
    // Re-rank the already-scored routes when the budget slider moves.
    const scored = routes.map((r) => ({ ...r }));
    const { ordered } = rankRoutes(scored);
    routes = ordered;
    selectedIdx = 0;
    drawRoutes();
    renderCards();
  }

  // ==========================================================================
  //  HELPERS
  // ==========================================================================
  function titleCase(s) {
    if (!s) return s;
    return s.replace(/\w\S*/g, (t) => t.charAt(0).toUpperCase() + t.slice(1).toLowerCase());
  }
  function setBusy(b) {
    el.go.disabled = b;
    el.go.textContent = b ? 'Finding quiet roads…' : 'Find quiet route';
  }
  function showStatus(msg, isErr) {
    el.status.textContent = msg;
    el.status.hidden = false;
    el.status.classList.toggle('err', !!isErr);
  }
  function hideStatus() { el.status.hidden = true; }
  function prettyError(err) {
    const m = (err && err.message) || '';
    if (m.includes('no route')) return 'No drivable route found between those points.';
    if (m.includes('routing')) return 'The routing service is busy — try again in a moment.';
    return 'Something went wrong. Check your connection and try again.';
  }

  // ==========================================================================
  //  EVENTS
  // ==========================================================================
  function wireEvents() {
    wireSearch(el.from, el.fromSuggest, 'from');
    wireSearch(el.to, el.toSuggest, 'to');

    el.go.addEventListener('click', findRoute);

    el.budget.addEventListener('input', () => {
      el.budgetLabel.textContent = '+' + el.budget.value + '%';
    });
    el.budget.addEventListener('change', recomputeRanking);

    el.swap.addEventListener('click', () => {
      [points.from, points.to] = [points.to, points.from];
      [el.from.value, el.to.value] = [el.to.value, el.from.value];
      if (points.from) placePin('from');
      if (points.to) placePin('to');
    });

    el.useLocation.addEventListener('click', () => {
      if (!navigator.geolocation) { showStatus('Geolocation not available.', true); return; }
      el.from.value = 'Locating…';
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          points.from = { lat: pos.coords.latitude, lon: pos.coords.longitude, label: 'My location' };
          el.from.value = 'My location';
          placePin('from');
        },
        () => { el.from.value = ''; showStatus('Could not get your location.', true); },
        { enableHighAccuracy: true, timeout: 8000 }
      );
    });

    el.aboutToggle.addEventListener('click', () => {
      el.about.hidden = !el.about.hidden;
    });

    // Enter to search
    [el.from, el.to].forEach((input) =>
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && points.from && points.to) findRoute();
      })
    );
  }

  // ---- Boot ---------------------------------------------------------------
  initMap();
  wireEvents();
})();
