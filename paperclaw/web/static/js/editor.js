/* ================================================================
   PaperForge Editor - Client-side logic
   ================================================================ */

(function () {
  'use strict';

  // ── State ──────────────────────────────────────────────────────
  const PROJECT = window.PAPERFORGE.projectName;
  let spec = JSON.parse(JSON.stringify(window.PAPERFORGE.spec));
  let currentLang = 'en';
  let previewLang = 'en';
  let currentTab = 'ai-generate';
  let autoSaveTimer = null;
  const AUTO_SAVE_DELAY = 3000; // ms
  let uploadedDataFiles = []; // track data files uploaded for AI generation
  let uploadedExtraDocs = []; // track extra documents for context
  let aiMode = 'experiment'; // 'experiment' or 'manual'

  // ── Initialise ─────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', init);

  function init() {
    buildSectionTabs();
    populateFields();
    refreshPreview();
    bindKeyboard();
    bindResize();
    bindDataUpload();
    loadDiagrams();
  }

  // ── Tab management ─────────────────────────────────────────────

  function buildSectionTabs() {
    const tabBar = document.getElementById('editor-tabs');
    const panels = document.getElementById('editor-panels');
    const refTab = tabBar.querySelector('[data-tab="references"]');

    (spec.sections || []).forEach(function (sec, idx) {
      // Tab button
      var btn = document.createElement('button');
      btn.className = 'tab';
      btn.dataset.tab = 'section-' + idx;
      btn.textContent = sec.heading[currentLang] || sec.heading.en || 'Section ' + (idx + 1);
      btn.onclick = function () { switchTab('section-' + idx); };
      tabBar.insertBefore(btn, refTab);

      // Panel
      var panel = document.createElement('div');
      panel.className = 'panel';
      panel.id = 'panel-section-' + idx;
      panel.innerHTML =
        '<div class="field-group">' +
          '<label>Section Heading</label>' +
          '<input type="text" class="full-width section-heading-input" ' +
                 'id="sec-heading-' + idx + '" ' +
                 'value="" onblur="onFieldBlur()">' +
        '</div>' +
        '<div class="field-group">' +
          '<label>Content (Markdown)</label>' +
          '<textarea id="sec-body-' + idx + '" rows="25" ' +
                    'placeholder="Write section content..." ' +
                    'onblur="onFieldBlur()"></textarea>' +
        '</div>';
      // Insert before references panel
      var refPanel = document.getElementById('panel-references');
      panels.insertBefore(panel, refPanel);
    });
  }

  window.switchTab = function (tabName) {
    currentTab = tabName;

    // Update tab buttons
    document.querySelectorAll('.editor-tabs .tab').forEach(function (t) {
      t.classList.toggle('active', t.dataset.tab === tabName);
    });

    // Update panels
    document.querySelectorAll('.editor-panels .panel').forEach(function (p) {
      p.classList.toggle('active', p.id === 'panel-' + tabName);
    });
  };

  // ── Field population ──────────────────────────────────────────

  function populateFields() {
    var title = spec.title || {};
    document.getElementById('field-title').value = title[currentLang] || title.en || '';

    var authors = spec.authors || [];
    document.getElementById('field-authors').value = authors.join(', ');

    var abstract = spec.abstract || {};
    document.getElementById('field-abstract').value = abstract[currentLang] || abstract.en || '';

    (spec.sections || []).forEach(function (sec, idx) {
      var hInput = document.getElementById('sec-heading-' + idx);
      var bInput = document.getElementById('sec-body-' + idx);
      if (hInput) hInput.value = (sec.heading || {})[currentLang] || (sec.heading || {}).en || '';
      if (bInput) bInput.value = (sec.body || sec.content || {})[currentLang] || (sec.body || sec.content || {}).en || '';
    });

    var refs = spec.references || [];
    document.getElementById('field-references').value = refs.join('\n');

    updateTabLabels();
  }

  function updateTabLabels() {
    (spec.sections || []).forEach(function (sec, idx) {
      var btn = document.querySelector('[data-tab="section-' + idx + '"]');
      if (btn) {
        btn.textContent = (sec.heading || {})[currentLang] || (sec.heading || {}).en || 'Section ' + (idx + 1);
      }
    });
  }

  function collectFields() {
    // Title
    if (!spec.title) spec.title = {};
    spec.title[currentLang] = document.getElementById('field-title').value;

    // Authors
    var authStr = document.getElementById('field-authors').value;
    spec.authors = authStr.split(',').map(function (a) { return a.trim(); }).filter(Boolean);

    // Abstract
    if (!spec.abstract) spec.abstract = {};
    spec.abstract[currentLang] = document.getElementById('field-abstract').value;

    // Sections
    (spec.sections || []).forEach(function (sec, idx) {
      var hInput = document.getElementById('sec-heading-' + idx);
      var bInput = document.getElementById('sec-body-' + idx);
      if (!sec.heading) sec.heading = {};
      if (!sec.body) sec.body = {};
      if (hInput) sec.heading[currentLang] = hInput.value;
      if (bInput) sec.body[currentLang] = bInput.value;
    });

    // References
    var refStr = document.getElementById('field-references').value;
    spec.references = refStr.split('\n').map(function (r) { return r.trim(); }).filter(Boolean);

    updateTabLabels();
  }

  // ── Language switching ────────────────────────────────────────

  window.setLang = function (lang) {
    collectFields(); // save current edits into spec
    currentLang = lang;

    // Update toolbar buttons
    document.querySelectorAll('.editor-toolbar .lang-btn').forEach(function (b) {
      b.classList.toggle('active', b.dataset.lang === lang);
    });

    // Update status bar
    document.getElementById('status-lang').textContent = lang.toUpperCase();

    populateFields();
    scheduleAutoSave();
  };

  window.setPreviewLang = function (lang) {
    previewLang = lang;
    document.querySelectorAll('.preview-toolbar .lang-btn').forEach(function (b) {
      b.classList.toggle('active', b.dataset.lang === lang);
    });
    refreshPreview();
  };

  // ── Save ──────────────────────────────────────────────────────

  window.saveSpec = function () {
    collectFields();
    setStatus('Saving...', 'saving');

    fetch('/api/project/' + PROJECT + '/spec', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(spec),
    })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        if (data.status === 'saved') {
          setStatus('Saved', 'success');
          notify('Saved successfully', 'success');
          refreshPreview();
        } else {
          setStatus('Save failed', 'error');
          notify(data.error || 'Save failed', 'error');
        }
      })
      .catch(function (err) {
        setStatus('Save error', 'error');
        notify('Network error: ' + err.message, 'error');
      });
  };

  // ── Auto-save ─────────────────────────────────────────────────

  window.onFieldBlur = function () {
    scheduleAutoSave();
  };

  function scheduleAutoSave() {
    if (autoSaveTimer) clearTimeout(autoSaveTimer);
    autoSaveTimer = setTimeout(function () {
      saveSpec();
    }, AUTO_SAVE_DELAY);
  }

  // ── Build PDF ─────────────────────────────────────────────────

  window.buildPdf = function () {
    collectFields();
    setStatus('Building PDF...', 'saving');
    notify('Building PDF...', 'info');

    // Save first, then build
    fetch('/api/project/' + PROJECT + '/spec', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(spec),
    })
      .then(function () {
        return fetch('/api/project/' + PROJECT + '/build', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ language: currentLang }),
        });
      })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        if (data.status === 'built' || data.status === 'built_html') {
          setStatus('PDF built', 'success');
          notify('PDF built: ' + (data.message || data.path), 'success');
        } else {
          setStatus('Build failed', 'error');
          notify(data.error || 'Build failed', 'error');
        }
      })
      .catch(function (err) {
        setStatus('Build error', 'error');
        notify('Build error: ' + err.message, 'error');
      });
  };

  // ── Download PDF ──────────────────────────────────────────────

  window.downloadPdf = function () {
    var url = '/api/project/' + PROJECT + '/pdf/' + currentLang;
    var a = document.createElement('a');
    a.href = url;
    a.download = '';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  // ── Preview ───────────────────────────────────────────────────

  window.refreshPreview = function () {
    fetch('/api/project/' + PROJECT + '/preview?lang=' + previewLang)
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        if (data.html) {
          document.getElementById('preview-content').innerHTML = data.html;
        }
      })
      .catch(function () {
        // Silently fail for preview
      });
  };

  // ── Figures ───────────────────────────────────────────────────

  window.uploadFigures = function () {
    var input = document.getElementById('figure-upload');
    if (!input.files.length) return;

    var formData = new FormData();
    for (var i = 0; i < input.files.length; i++) {
      formData.append('file-' + i, input.files[i]);
    }

    setStatus('Uploading figures...', 'saving');

    fetch('/api/project/' + PROJECT + '/figures', {
      method: 'POST',
      body: formData,
    })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        if (data.files && data.files.length) {
          setStatus('Figures uploaded', 'success');
          notify('Uploaded ' + data.files.length + ' figure(s)', 'success');
          renderFigureList(data.files);
        }
      })
      .catch(function (err) {
        setStatus('Upload error', 'error');
        notify('Upload error: ' + err.message, 'error');
      });
  };

  function renderFigureList(files) {
    var container = document.getElementById('figure-list');
    files.forEach(function (f) {
      var div = document.createElement('div');
      div.className = 'figure-item';
      div.innerHTML =
        '<img src="/api/project/' + PROJECT + '/figures/' + f + '" ' +
             'onerror="this.style.display=\'none\'" alt="' + f + '">' +
        '<div>' + f + '</div>';
      container.appendChild(div);
    });
  }

  // ── AI Generate ────────────────────────────────────────────────

  // ── AI mode toggle ───────────────────────────────────────────

  window.setAiMode = function (mode) {
    aiMode = mode;
    document.querySelectorAll('.mode-btn').forEach(function (b) {
      b.classList.toggle('active', b.dataset.mode === mode);
    });
    var expDiv = document.getElementById('ai-mode-experiment');
    var manDiv = document.getElementById('ai-mode-manual');
    if (expDiv) expDiv.style.display = mode === 'experiment' ? '' : 'none';
    if (manDiv) manDiv.style.display = mode === 'manual' ? '' : 'none';
  };

  function bindDataUpload() {
    var input = document.getElementById('ai-data-upload');
    if (input) {
      input.addEventListener('change', function () {
        var list = document.getElementById('ai-data-list');
        list.innerHTML = '';
        uploadedDataFiles = [];
        for (var i = 0; i < input.files.length; i++) {
          var f = input.files[i];
          uploadedDataFiles.push(f);
          var span = document.createElement('span');
          span.className = 'data-item';
          span.textContent = f.name;
          list.appendChild(span);
        }
      });
    }

    // Extra docs upload
    var docsInput = document.getElementById('ai-extra-docs');
    if (docsInput) {
      docsInput.addEventListener('change', function () {
        var list = document.getElementById('ai-extra-docs-list');
        list.innerHTML = '';
        uploadedExtraDocs = [];
        for (var i = 0; i < docsInput.files.length; i++) {
          var f = docsInput.files[i];
          uploadedExtraDocs.push(f);
          var span = document.createElement('span');
          span.className = 'data-item';
          span.textContent = f.name + ' (' + (f.size / 1024).toFixed(0) + 'KB)';
          list.appendChild(span);
        }
      });
    }
  }

  window.aiGenerate = function () {
    var overview = document.getElementById('ai-overview').value.trim();
    var experimentDir = '';
    var expInput = document.getElementById('ai-experiment-dir');
    if (expInput) experimentDir = expInput.value.trim();

    // Validate
    if (aiMode === 'experiment' && !experimentDir) {
      notify('Please enter an experiment directory path.', 'error');
      return;
    }
    if (aiMode === 'manual' && !overview) {
      notify('Please enter a research overview.', 'error');
      return;
    }

    var titleEn = document.getElementById('ai-title-en').value.trim();
    var titleJa = document.getElementById('ai-title-ja').value.trim();
    var template = document.getElementById('ai-template').value;

    var btn = document.getElementById('ai-generate-btn');
    var statusEl = document.getElementById('ai-status');
    btn.disabled = true;
    btn.innerHTML = '<span class="ai-spinner"></span> Generating...';
    statusEl.className = 'ai-status generating';
    statusEl.textContent = 'AI is scanning data and drafting your paper... This may take 30-90 seconds.';
    setStatus('AI generating...', 'saving');

    // Upload extra docs first (if any)
    var docsPromise;
    if (uploadedExtraDocs.length > 0) {
      var docsForm = new FormData();
      for (var i = 0; i < uploadedExtraDocs.length; i++) {
        docsForm.append('file-' + i, uploadedExtraDocs[i]);
      }
      docsPromise = fetch('/api/project/' + PROJECT + '/extra_docs', {
        method: 'POST',
        body: docsForm,
      }).then(function (r) { return r.json(); });
    } else {
      docsPromise = Promise.resolve({ files: [] });
    }

    // Upload data files (manual mode)
    var dataPromise;
    if (aiMode === 'manual' && uploadedDataFiles.length > 0) {
      var formData = new FormData();
      for (var i = 0; i < uploadedDataFiles.length; i++) {
        formData.append('file-' + i, uploadedDataFiles[i]);
      }
      dataPromise = fetch('/api/project/' + PROJECT + '/data', {
        method: 'POST',
        body: formData,
      }).then(function (r) { return r.json(); });
    } else {
      dataPromise = Promise.resolve({ files: [] });
    }

    Promise.all([docsPromise, dataPromise])
      .then(function (results) {
        var dataFiles = (results[1].files || []).map(function (f) { return 'data/' + f; });

        var payload = {
          overview: overview,
          title_en: titleEn || 'Untitled Paper',
          title_ja: titleJa || '無題の論文',
          template: template,
        };

        if (aiMode === 'experiment') {
          payload.experiment_dir = experimentDir;
        } else {
          payload.data_files = dataFiles;
        }

        return fetch('/api/project/' + PROJECT + '/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        btn.disabled = false;
        btn.innerHTML =
          '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
          'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
          '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg> ' +
          'Generate Paper with AI';

        if (data.status === 'generated') {
          statusEl.className = 'ai-status done';
          statusEl.textContent = 'Paper generated! Sections are now populated.';
          setStatus('Paper generated', 'success');
          notify('Paper generated successfully! Check the section tabs.', 'success');
          window.location.reload();
        } else {
          statusEl.className = 'ai-status error';
          statusEl.textContent = data.error || 'Generation failed.';
          setStatus('Generation failed', 'error');
          notify(data.error || 'Generation failed', 'error');
        }
      })
      .catch(function (err) {
        btn.disabled = false;
        btn.innerHTML =
          '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
          'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
          '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg> ' +
          'Generate Paper with AI';
        statusEl.className = 'ai-status error';
        statusEl.textContent = 'Error: ' + err.message;
        setStatus('Generation error', 'error');
        notify('Error: ' + err.message, 'error');
      });
  };

  // ── Diagrams (draw.io / Mermaid) ────────────────────────────────

  function loadDiagrams() {
    fetch('/api/project/' + PROJECT + '/diagrams')
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        var container = document.getElementById('diagram-list');
        if (!container) return;
        container.innerHTML = '';

        var diagrams = data.diagrams || [];
        if (diagrams.length === 0) {
          container.innerHTML = '<p style="color:var(--text-secondary);font-size:0.85rem;">No diagrams yet. Use AI Generate to create diagrams automatically.</p>';
          return;
        }

        diagrams.forEach(function (d) {
          var card = document.createElement('div');
          card.className = 'diagram-card';

          var imgHtml = d.png
            ? '<img src="' + d.png + '" alt="' + d.id + '" class="diagram-preview">'
            : '<div class="diagram-no-img">No preview</div>';

          card.innerHTML =
            imgHtml +
            '<div class="diagram-info">' +
              '<strong>' + d.id + '</strong>' +
              '<div class="diagram-actions">' +
                '<button class="btn btn-sm" onclick="viewMermaidSource(\'' + d.id + '\')">View Source</button>' +
                '<button class="btn btn-sm btn-primary" onclick="openInDrawio(\'' + d.id + '\')">Open in draw.io</button>' +
              '</div>' +
            '</div>';
          container.appendChild(card);
        });
      })
      .catch(function () {});
  }

  // Store mermaid sources for the viewer
  var mermaidSources = {};

  window.viewMermaidSource = function (figId) {
    fetch('/api/project/' + PROJECT + '/diagrams')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var diag = (data.diagrams || []).find(function (d) { return d.id === figId; });
        if (diag) {
          alert('Mermaid source for ' + figId + ':\n\n' + diag.mermaid);
        }
      });
  };

  window.openInDrawio = function (figId) {
    fetch('/api/project/' + PROJECT + '/diagrams')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var diag = (data.diagrams || []).find(function (d) { return d.id === figId; });
        if (diag && diag.mermaid) {
          // Open draw.io with mermaid content via URL
          var encoded = encodeURIComponent(diag.mermaid);
          var url = 'https://www.draw.io/#Uhttps://mermaid.ink/svg/' + btoa(diag.mermaid);
          // Fallback: open draw.io directly
          window.open('https://app.diagrams.net/', '_blank');
          notify('draw.io opened. Paste your Mermaid code to edit.', 'info');
        }
      });
  };

  // ── Keyboard shortcuts ────────────────────────────────────────

  function bindKeyboard() {
    document.addEventListener('keydown', function (e) {
      // Ctrl+S / Cmd+S = Save
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveSpec();
      }
      // Ctrl+B / Cmd+B = Build
      if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
        e.preventDefault();
        buildPdf();
      }
    });
  }

  // ── Resizable split pane ──────────────────────────────────────

  function bindResize() {
    var handle = document.getElementById('resize-handle');
    var editorPane = document.getElementById('editor-pane');
    var layout = document.getElementById('editor-layout');
    var dragging = false;

    handle.addEventListener('mousedown', function (e) {
      e.preventDefault();
      dragging = true;
      handle.classList.add('active');
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    });

    document.addEventListener('mousemove', function (e) {
      if (!dragging) return;
      var rect = layout.getBoundingClientRect();
      var x = e.clientX - rect.left;
      var pct = (x / rect.width) * 100;
      if (pct < 20) pct = 20;
      if (pct > 80) pct = 80;
      editorPane.style.width = pct + '%';
    });

    document.addEventListener('mouseup', function () {
      if (dragging) {
        dragging = false;
        handle.classList.remove('active');
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    });
  }

  // ── Status bar ────────────────────────────────────────────────

  function setStatus(text, type) {
    var el = document.getElementById('status-text');
    el.textContent = text;
    el.className = type ? 'status-' + type : '';

    // Auto-clear after 4s
    if (type === 'success' || type === 'error') {
      setTimeout(function () {
        el.textContent = 'Ready';
        el.className = '';
      }, 4000);
    }
  }

  // ── Notifications ─────────────────────────────────────────────

  function notify(message, type) {
    type = type || 'info';
    var div = document.createElement('div');
    div.className = 'notification ' + type;
    div.textContent = message;
    document.body.appendChild(div);

    setTimeout(function () {
      div.style.opacity = '0';
      div.style.transition = 'opacity 0.3s';
      setTimeout(function () { div.remove(); }, 300);
    }, 3000);
  }

  // Expose for inline handlers
  window.notify = notify;

})();
