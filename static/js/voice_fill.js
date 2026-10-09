(() => {
  const root = document.querySelector('[data-voice-fill]');
  if (!root) return;
  const form = root.closest('form');

  const MAX_LENGTH = 2000;
  const MAX_LISTEN_MS = 60000;
  const VOICE_FIELDS = [
    'title', 'description', 'food_type', 'food_condition', 'quantity', 'unit', 'prepared_at',
    'storage_notes', 'allergen_notes', 'is_unpackaged', 'pickup_address', 'pickup_window_start', 'pickup_window_end',
  ];
  const LABELS = {
    title: 'Title', description: 'Description', food_type: 'Food type', food_condition: 'Food condition',
    quantity: 'Quantity', unit: 'Unit', prepared_at: 'Prepared at', storage_notes: 'Storage notes',
    allergen_notes: 'Allergen notes', is_unpackaged: 'Unpackaged food', pickup_address: 'Pickup address',
    pickup_window_start: 'Pickup window start', pickup_window_end: 'Pickup window end',
  };
  const BADGES = {
    filled: ['bi-mic-fill', 'Filled by voice'],
    uncertain: ['bi-question-circle', 'Please confirm'],
    missing: ['bi-pencil', 'Needs your input'],
  };
  const SPEECH_ERRORS = {
    'not-allowed': 'Microphone access is blocked. Allow it in your browser settings, or type your description instead.',
    'service-not-allowed': 'Microphone access is blocked. Allow it in your browser settings, or type your description instead.',
    'no-speech': "We didn't hear anything. Try again, or type your description instead.",
    'audio-capture': 'No microphone was found. Type your description instead.',
    network: 'Voice recognition needs an internet connection. Type your description instead.',
    default: 'Voice input stopped unexpectedly. Try again, or type your description instead.',
  };
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const $ = (selector) => root.querySelector(selector);
  const ui = {
    start: $('[data-voice-start]'),
    startLabel: $('[data-voice-start-label]'),
    typeToggle: $('[data-voice-type-toggle]'),
    transcriptWrap: $('[data-voice-transcript-wrap]'),
    transcript: $('[data-voice-transcript]'),
    count: $('[data-voice-count]'),
    clear: $('[data-voice-clear]'),
    overwrite: $('[data-voice-overwrite]'),
    parse: $('[data-voice-parse]'),
    status: $('[data-voice-status]'),
    summary: $('[data-voice-summary]'),
    summaryText: $('[data-voice-summary-text]'),
    missing: $('[data-voice-missing]'),
    notes: $('[data-voice-notes]'),
    undo: $('[data-voice-undo]'),
  };

  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let speechError = null;
  let listenTimer = null;
  let snapshot = null;
  let applying = false;
  let lastFilledCount = 0;

  const csrfToken = () => form.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '';
  const input = (name) => form.querySelector(`[name="${name}"]`);
  const wrapper = (field) => field?.closest('.donation-field, .location-picker');
  const isEmpty = (field) => (field.type === 'checkbox' ? !field.checked : !String(field.value).trim());
  const setState = (state) => { root.dataset.state = state; };
  const setStatus = (message = '', tone = 'info') => {
    ui.status.textContent = message;
    ui.status.dataset.tone = tone;
    ui.status.hidden = !message;
  };
  const updateCount = () => { ui.count.textContent = `${ui.transcript.value.length} / ${MAX_LENGTH}`; };
  const showTranscript = () => { ui.transcriptWrap.hidden = false; };

  // ---- Field marking -------------------------------------------------------
  const clearWrapperMarks = (wrap) => {
    wrap.classList.remove('is-voice-filled', 'is-voice-missing', 'is-voice-uncertain');
    wrap.querySelectorAll('[data-voice-badge]').forEach((badge) => badge.remove());
  };
  const clearAllMarks = () => {
    form.querySelectorAll('.is-voice-filled, .is-voice-missing, .is-voice-uncertain').forEach(clearWrapperMarks);
  };
  const markField = (name, kind) => {
    const wrap = wrapper(input(name));
    if (!wrap) return;
    clearWrapperMarks(wrap);
    wrap.classList.add(`is-voice-${kind}`);
    const [iconClass, text] = BADGES[kind];
    const badge = document.createElement('span');
    badge.className = `voice-badge voice-badge--${kind}`;
    badge.dataset.voiceBadge = '';
    const icon = document.createElement('i');
    icon.className = `bi ${iconClass}`;
    icon.setAttribute('aria-hidden', 'true');
    badge.append(icon, document.createTextNode(text));
    (wrap.querySelector('.donation-toggle strong') || wrap.querySelector('label') || wrap).append(badge);
  };

  const focusField = (name) => {
    const field = input(name);
    if (!field) return;
    wrapper(field)?.scrollIntoView({behavior: reducedMotion ? 'auto' : 'smooth', block: 'center'});
    field.focus({preventScroll: true});
  };

  const missingFields = () => VOICE_FIELDS.filter((name) => {
    const field = input(name);
    return field && field.required && isEmpty(field);
  });

  const updateSummary = () => {
    const missing = missingFields();
    ui.missing.replaceChildren(...missing.map((name) => {
      const item = document.createElement('li');
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'voice-fill__missing-link';
      button.textContent = LABELS[name];
      button.addEventListener('click', () => focusField(name));
      item.append(button);
      return item;
    }));
    ui.missing.hidden = !missing.length;
    const filledText = lastFilledCount
      ? `Filled ${lastFilledCount} ${lastFilledCount === 1 ? 'field' : 'fields'} from your description.`
      : 'We could not pick out any new details.';
    const missingText = missing.length
      ? `${missing.length} required ${missing.length === 1 ? 'detail needs' : 'details need'} your input:`
      : 'All required details are filled. Please review them before saving.';
    ui.summaryText.textContent = `${filledText} ${missingText}`;
    ui.summary.dataset.complete = String(!missing.length);
    return missing;
  };

  const renderNotes = (notes) => {
    ui.notes.replaceChildren(...notes.map((note) => {
      const item = document.createElement('li');
      item.textContent = note;
      return item;
    }));
    ui.notes.hidden = !notes.length;
  };

  const suggestPlaces = (address) => {
    const search = form.querySelector('[data-location-search]');
    if (!search || !address) return;
    search.value = address.slice(0, 200);
    search.dispatchEvent(new Event('input', {bubbles: true}));
  };

  // ---- Applying parsed values ---------------------------------------------
  const applyResult = (data) => {
    const fields = data.fields || {};
    const uncertain = new Set(data.uncertain || []);
    snapshot = VOICE_FIELDS.map((name) => {
      const field = input(name);
      return field && {field, value: field.value, checked: field.checked};
    }).filter(Boolean);
    clearAllMarks();

    const filled = [];
    const skipped = [];
    applying = true;
    Object.entries(fields).forEach(([name, value]) => {
      const field = input(name);
      if (!VOICE_FIELDS.includes(name) || !field || field.type === 'hidden') return;
      if (field.type === 'checkbox') {
        if (!ui.overwrite.checked && field.checked && !value) return;
        field.checked = Boolean(value);
      } else {
        if (!ui.overwrite.checked && !isEmpty(field)) {
          if (String(field.value) !== String(value)) skipped.push(name);
          return;
        }
        const previous = field.value;
        field.value = String(value);
        if (field.tagName === 'SELECT' && field.value !== String(value)) {
          field.value = previous;
          return;
        }
      }
      field.dispatchEvent(new Event('input', {bubbles: true}));
      field.dispatchEvent(new Event('change', {bubbles: true}));
      filled.push(name);
    });
    applying = false;

    filled.forEach((name) => markField(name, uncertain.has(name) ? 'uncertain' : 'filled'));
    missingFields().forEach((name) => markField(name, 'missing'));
    lastFilledCount = filled.length;
    const missing = updateSummary();

    const notes = [];
    if (skipped.length) {
      notes.push(`Kept what you already entered for ${skipped.map((name) => LABELS[name].toLowerCase()).join(', ')}. Tick "Replace fields I already filled" to overwrite.`);
    }
    if (filled.includes('pickup_address') && !input('pickup_latitude')?.value) {
      notes.push('Choose the matching place in the pickup search results so volunteers get an exact map pin.');
      suggestPlaces(fields.pickup_address);
    }
    notes.push('Photos are never filled by voice. Upload them under "Safety and photos".');
    renderNotes(notes);

    ui.summary.hidden = false;
    setStatus('');
    if (missing.length) focusField(missing[0]);
  };

  const onFieldEdit = (event) => {
    if (applying || !snapshot || !VOICE_FIELDS.includes(event.target.name)) return;
    const wrap = wrapper(event.target);
    if (!wrap || !wrap.matches('.is-voice-filled, .is-voice-uncertain, .is-voice-missing')) return;
    if (wrap.classList.contains('is-voice-missing') && isEmpty(event.target)) return;
    clearWrapperMarks(wrap);
    if (!ui.summary.hidden) updateSummary();
  };
  form.addEventListener('input', onFieldEdit);
  form.addEventListener('change', onFieldEdit);

  ui.undo.addEventListener('click', () => {
    if (!snapshot) return;
    applying = true;
    snapshot.forEach(({field, value, checked}) => {
      field.value = value;
      field.checked = checked;
      field.dispatchEvent(new Event('change', {bubbles: true}));
    });
    applying = false;
    snapshot = null;
    clearAllMarks();
    ui.summary.hidden = true;
    setState('idle');
    setStatus('Voice changes were undone.');
  });

  // ---- Parsing --------------------------------------------------------------
  const setBusy = (busy) => {
    ui.parse.disabled = busy;
    ui.start.disabled = busy;
  };

  const parseTranscript = async () => {
    const text = ui.transcript.value.trim();
    if (!text) {
      setStatus('Say or type something about your donation first.', 'error');
      ui.transcript.focus();
      return;
    }
    setState('parsing');
    setBusy(true);
    setStatus('Reading your description...');
    try {
      const response = await fetch(root.dataset.parseUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken()},
        body: JSON.stringify({transcript: text}),
      });
      let data = {};
      try { data = await response.json(); } catch { data = {}; }
      if (!response.ok || !data.fields) {
        throw new Error(data.detail || 'We could not read that description. Please fill the form manually.');
      }
      applyResult(data);
      setState('review');
    } catch (error) {
      setState('error');
      setStatus(error.message || 'We could not read that description. Please fill the form manually.', 'error');
    } finally {
      setBusy(false);
    }
  };

  // ---- Speech recognition --------------------------------------------------
  const setListeningUi = (listening) => {
    ui.start.setAttribute('aria-pressed', String(listening));
    ui.start.classList.toggle('is-listening', listening);
    ui.startLabel.textContent = listening ? 'Stop listening' : (ui.transcript.value.trim() ? 'Speak again' : 'Start speaking');
    ui.parse.disabled = listening;
  };

  const stopListening = () => recognition?.stop();

  const startListening = () => {
    speechError = null;
    // Append to what is already there so donors can add a missed detail by voice.
    let committed = ui.transcript.value.trim();
    recognition = new Recognition();
    recognition.lang = root.dataset.lang || 'en-IN';
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.onresult = (event) => {
      let interim = '';
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const text = event.results[index][0].transcript.trim();
        if (!text) continue;
        if (event.results[index].isFinal) committed = `${committed} ${text}`.trim();
        else interim = `${interim} ${text}`.trim();
      }
      ui.transcript.value = `${committed} ${interim}`.trim().slice(0, MAX_LENGTH);
      updateCount();
    };
    recognition.onerror = (event) => {
      if (event.error !== 'aborted') speechError = SPEECH_ERRORS[event.error] || SPEECH_ERRORS.default;
    };
    recognition.onend = () => {
      clearTimeout(listenTimer);
      recognition = null;
      setListeningUi(false);
      if (speechError) {
        setState('error');
        setStatus(speechError, 'error');
        return;
      }
      if (ui.transcript.value.trim()) parseTranscript();
      else { setState('idle'); setStatus(''); }
    };
    try {
      recognition.start();
    } catch {
      recognition = null;
      setState('error');
      setStatus(SPEECH_ERRORS.default, 'error');
      return;
    }
    showTranscript();
    setState('listening');
    setListeningUi(true);
    setStatus('Listening... describe the food, quantity, when it was cooked, pickup address and pickup time. Press stop when done.');
    listenTimer = setTimeout(stopListening, MAX_LISTEN_MS);
  };

  // ---- Wiring ---------------------------------------------------------------
  if (Recognition) {
    ui.start.addEventListener('click', () => (recognition ? stopListening() : startListening()));
  } else {
    ui.start.hidden = true;
    ui.typeToggle.hidden = true;
    showTranscript();
    setStatus('Voice input is not supported in this browser. Type a description of your donation and we will fill the form.');
  }
  ui.typeToggle.addEventListener('click', () => {
    showTranscript();
    ui.typeToggle.hidden = true;
    ui.transcript.focus();
  });
  ui.transcript.addEventListener('input', updateCount);
  ui.transcript.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      parseTranscript();
    }
  });
  ui.clear.addEventListener('click', () => {
    ui.transcript.value = '';
    updateCount();
    setListeningUi(Boolean(recognition));
    ui.transcript.focus();
  });
  ui.parse.addEventListener('click', parseTranscript);
  updateCount();
})();
