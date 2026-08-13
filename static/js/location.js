(() => {
  const defaultCenter = [12.9716, 77.5946];
  const csrf = () => document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '';
  document.querySelectorAll('[data-location-picker]').forEach((picker) => {
    if (!window.L) return;
    const address = picker.querySelector('textarea, input[name$="address"]');
    const latitude = picker.querySelector('input[name$="latitude"]');
    const longitude = picker.querySelector('input[name$="longitude"]');
    const label = picker.querySelector('input[name$="place_label"]');
    const confirmation = picker.querySelector('[data-location-confirmation]');
    let map = L.map(picker.querySelector('[data-location-map]')).setView(defaultCenter, 11);
    L.tileLayer(document.body.dataset.mapTile, {attribution: document.body.dataset.mapAttribution}).addTo(map);
    let marker;
    const setPoint = (lat, lng, text) => {
      const point = [Number(lat), Number(lng)];
      if (!Number.isFinite(point[0]) || !Number.isFinite(point[1])) return;
      if (!marker) marker = L.marker(point, {draggable: true}).addTo(map).on('dragend', () => setPoint(marker.getLatLng().lat, marker.getLatLng().lng, label.value || address.value));
      else marker.setLatLng(point);
      latitude.value = point[0].toFixed(6); longitude.value = point[1].toFixed(6);
      if (text) { label.value = text; if (!address.value) address.value = text; }
      confirmation.hidden = false; confirmation.querySelector('span').textContent = `Pinned: ${label.value || address.value || 'selected location'}`;
      map.setView(point, 16);
    };
    if (latitude.value && longitude.value) setPoint(latitude.value, longitude.value, label.value || address.value);
    picker.querySelector('[data-use-location]').addEventListener('click', () => navigator.geolocation?.getCurrentPosition(
      position => setPoint(position.coords.latitude, position.coords.longitude, 'Current location'),
      () => picker.querySelector('[data-location-results]').textContent = 'GPS could not be accessed. Search or enter an address manually.',
      {enableHighAccuracy: true, timeout: 10000}
    ));
    let timer;
    picker.querySelector('[data-location-search]').addEventListener('input', (event) => {
      clearTimeout(timer); const query = event.target.value.trim(); const results = picker.querySelector('[data-location-results]');
      if (query.length < 3) return results.replaceChildren();
      timer = setTimeout(async () => {
        try { results.textContent = 'Searching nearby places…'; const endpoint = new URL(picker.dataset.geocodeUrl, window.location.origin); endpoint.searchParams.set('q', query); if (latitude.value && longitude.value) { endpoint.searchParams.set('lat', latitude.value); endpoint.searchParams.set('lon', longitude.value); } const response = await fetch(endpoint); const data = await response.json();
          if (!response.ok) throw new Error(data.detail || 'Search is unavailable');
          const places = data.results || [];
          if (!places.length) { results.textContent = 'No matching places found. Try a more specific address.'; return; }
          results.replaceChildren(...places.map(place => { const button = document.createElement('button'); const icon = document.createElement('i'); const content = document.createElement('span'); const text = document.createElement('span'); button.type = 'button'; button.className = 'location-picker__result'; icon.className = 'bi bi-geo-alt'; text.textContent = place.label; content.append(text); if (place.distance_km !== undefined) { const distance = document.createElement('small'); distance.textContent = `${place.distance_km} km away`; content.append(distance); } button.append(icon, content); button.onclick = () => { address.value = place.label; setPoint(place.latitude, place.longitude, place.label); results.replaceChildren(); }; return button; }));
        } catch (error) { results.textContent = error.message || 'Search is unavailable; enter the address manually.'; }
      }, 350);
    });
  });
  document.querySelectorAll('[data-pickups-map]').forEach((container) => {
    if (!window.L) return;
    const pins = [...container.parentElement.querySelectorAll('[data-pickup-pin]')];
    if (!pins.length) { container.parentElement.hidden = true; return; }
    const map = L.map(container).setView(defaultCenter, 11);
    L.tileLayer(document.body.dataset.mapTile, {attribution: document.body.dataset.mapAttribution}).addTo(map);
    const bounds = [];
    pins.forEach((pin) => { const point = [Number(pin.dataset.latitude), Number(pin.dataset.longitude)]; L.marker(point).addTo(map).bindPopup(pin.dataset.label); bounds.push(point); });
    map.fitBounds(bounds, {padding: [28, 28], maxZoom: 14});
  });
  const tracking = document.querySelector('[data-global-tracking]') || document.querySelector('[data-volunteer-tracking]');
  if (tracking && navigator.geolocation) {
    const status = tracking.querySelector('[data-tracking-status]');
    let lastSent = null;
    const metresFromLast = (latitude, longitude) => { if (!lastSent) return Infinity; const radians = Math.PI / 180; const deltaLat = (latitude-lastSent.latitude)*radians; const deltaLng = (longitude-lastSent.longitude)*radians; const value = Math.sin(deltaLat/2)**2 + Math.cos(lastSent.latitude*radians)*Math.cos(latitude*radians)*Math.sin(deltaLng/2)**2; return 6371000 * 2 * Math.atan2(Math.sqrt(value), Math.sqrt(1-value)); };
    const send = (position) => { const latitude = position.coords.latitude; const longitude = position.coords.longitude; const now = Date.now(); if (lastSent && now - lastSent.at < 30000 && metresFromLast(latitude, longitude) < 50) return; const data = new URLSearchParams({latitude, longitude}); fetch(tracking.dataset.url, {method: 'POST', headers: {'X-CSRFToken': csrf(), 'Content-Type': 'application/x-www-form-urlencoded'}, body: data}).then(response => { if (response.ok) { lastSent = {latitude, longitude, at: now}; if (status) status.textContent = 'Location sharing is active.'; } }); };
    navigator.geolocation.watchPosition(send, () => { if (status) status.textContent = 'GPS is unavailable. You remain available without live sharing.'; }, {enableHighAccuracy: true, maximumAge: 15000, timeout: 10000});
  }
})();
