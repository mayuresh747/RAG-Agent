/* ═══════════════════════════════════════════════════════════════
   RAG Agent — Chat UI Client Logic
   ═══════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
    // ── DOM refs ──────────────────────────────────────────────────
    const chatArea = document.getElementById('chatArea');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const clearChat = document.getElementById('clearChat');
    const shareBtn = document.getElementById('shareBtn');
    const openSettings = document.getElementById('openSettings');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const sidebarClose = document.getElementById('sidebarClose');
    const systemPrompt = document.getElementById('systemPrompt');
    const savePrompt = document.getElementById('savePrompt');
    const resetPrompt = document.getElementById('resetPrompt');
    const saveStatus = document.getElementById('saveStatus');
    const welcome = document.getElementById('welcome');
    const tempSlider = document.getElementById('tempSlider');
    const tempValue = document.getElementById('tempValue');

    // Auth Elements
    const authModal = document.getElementById('authModal');
    const apiKeyInput = document.getElementById('apiKeyInput');
    const authBtn = document.getElementById('authBtn');
    const authError = document.getElementById('authError');

    let isStreaming = false;
    let defaultPrompt = '';
    
    // Auth State
    let apiKey = localStorage.getItem('rag_api_key') || '';
    let sessionId = localStorage.getItem('rag_session_id');

    // Generate Session ID if missing
    if (!sessionId) {
        sessionId = crypto.randomUUID();
        localStorage.setItem('rag_session_id', sessionId);
    }

    // ── Init ──────────────────────────────────────────────────────
    checkAuth();
    
    function checkAuth() {
        if (!apiKey) {
            authModal.style.display = 'flex';
        } else {
            authModal.style.display = 'none';
            // Sync backend history state with empty UI state
            clearBackendHistory();
            // Only load settings if we have a key (or attempt to)
            // loadSettings(); // Hidden for now
        }
    }

    async function clearBackendHistory() {
        try {
            await fetch(`/api/chat/history?session_id=${sessionId}`, { 
                method: 'DELETE',
                headers: getHeaders()
            });
        } catch (e) {
            console.error("Failed to clear backend history on load", e);
        }
    }

    // Auth Event Listeners
    authBtn.addEventListener('click', submitAuth);
    apiKeyInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') submitAuth();
    });

    function submitAuth() {
        const key = apiKeyInput.value.trim();
        if (key) {
            apiKey = key;
            localStorage.setItem('rag_api_key', key);
            checkAuth();
        } else {
            authError.textContent = "Please enter a key";
        }
    }

    // Headers Helper
    function getHeaders() {
        return { 
            'Content-Type': 'application/json',
            'x-api-key': apiKey
        };
    }

    // ── Input handling ────────────────────────────────────────────
    chatInput.addEventListener('input', () => {
        sendBtn.disabled = !chatInput.value.trim() || isStreaming;
        autoResize(chatInput);
    });

    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled) sendMessage();
        }
    });

    sendBtn.addEventListener('click', sendMessage);

    // ── Example queries ───────────────────────────────────────────
    const QUESTION_POOL = [
        // Standard Legal Queries (Grounded in available docs)
        "What are the requirements for ADUs in Seattle under SMC?",
        "RCW definition of 'family' for zoning purposes",
        "WAC rules for childcare center licensing",
        "Washington Supreme Court ruling on 'public duty doctrine'",
        "Governor's emergency orders on eviction moratorium",
        "Seattle Director's Rule on tree protection",
        "SPU design standards for drainage in right-of-way",
        "IBC seismic design category for Western Washington",
        "Landlord-tenant act notice requirements RCW 59.18",
        "Seattle noise ordinance construction hours",

        // Conflict & Friction Queries (Seattle vs State vs Code)
        "Does Seattle SMC 25.09 (critical areas) conflict with WAC 365-190?",
        "Conflict between IBC egress requirements and Seattle Building Code amendments?",
        "Differences in 'affordable housing' definitions: RCW vs SMC",
        "State vs Seattle rules on short-term rentals (RCW 64.37 vs SMC)",
        "Does Seattle's minimum wage ordinance conflict with state RCW?",
        "SPU drainage rules vs Ecology stormwater manual (WAC)",
        "Washington State energy code vs Seattle energy code amendments",
        "Conflict between Governor's emergency proclamations and existing RCWs",
        "SMC zoning density limits vs State 'Missing Middle' housing bill (HB 1110)",
        "Court rulings interpreting 'vested rights' vs current SMC land use codes"
    ];

    function renderRandomExamples() {
        const container = document.querySelector('.example-queries');
        if (!container) return;

        // Shuffle and pick 4
        const shuffled = [...QUESTION_POOL].sort(() => 0.5 - Math.random());
        const selected = shuffled.slice(0, 4);

        container.innerHTML = '';
        selected.forEach(q => {
            const btn = document.createElement('button');
            btn.className = 'example-query';
            btn.textContent = q;
            btn.addEventListener('click', () => {
                chatInput.value = q;
                sendBtn.disabled = false;
                autoResize(chatInput);
                sendMessage();
            });
            container.appendChild(btn);
        });
    }

    renderRandomExamples();

    // ── Share conversation ────────────────────────────────────────
    shareBtn.addEventListener('click', async () => {
        shareBtn.disabled = true;
        shareBtn.textContent = 'Sharing…';
        try {
            const res = await fetch('/api/share', {
                method: 'POST',
                headers: getHeaders(),
                body: JSON.stringify({ session_id: sessionId }),
            });
            if (!res.ok) throw new Error('Failed to create share');
            const data = await res.json();
            showShareModal(window.location.origin + data.share_url);
        } catch (e) {
            console.error('Share failed', e);
            alert('Could not create share link. Please try again.');
        } finally {
            shareBtn.disabled = false;
            shareBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg> Share`;
        }
    });

    function showShareModal(url) {
        const overlay = document.createElement('div');
        overlay.className = 'share-modal-overlay';
        overlay.innerHTML = `
            <div class="share-modal">
                <h3>Conversation shared</h3>
                <p class="share-modal-sub">Anyone with this link can view this conversation.</p>
                <div class="share-url-row">
                    <a class="share-url-link" href="${url}" target="_blank" rel="noopener">${url}</a>
                    <button class="btn btn-primary share-copy-btn" id="copyShareBtn">Copy</button>
                </div>
                <button class="btn btn-secondary share-close-btn" id="closeShareBtn">Close</button>
            </div>
        `;
        document.body.appendChild(overlay);

        document.getElementById('copyShareBtn').addEventListener('click', () => {
            navigator.clipboard.writeText(url).then(() => {
                document.getElementById('copyShareBtn').textContent = 'Copied!';
                setTimeout(() => { document.getElementById('copyShareBtn').textContent = 'Copy'; }, 2000);
            });
        });

        document.getElementById('closeShareBtn').addEventListener('click', () => overlay.remove());
        overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
    }

    // ── Clear chat ────────────────────────────────────────────────
    clearChat.addEventListener('click', async () => {
        try {
            await fetch(`/api/chat/history?session_id=${sessionId}`, { 
                method: 'DELETE',
                headers: getHeaders()
            });
            chatArea.innerHTML = '';
            chatArea.appendChild(welcome);
            welcome.style.display = 'flex';
            shareBtn.style.display = 'none';
        } catch (e) {
            console.error("Clear chat failed", e);
        }
    });

    // ── Sidebar ───────────────────────────────────────────────────
    /* Settings UI hidden
    openSettings.addEventListener('click', () => toggleSidebar(true));
    sidebarClose.addEventListener('click', () => toggleSidebar(false));
    sidebarOverlay.addEventListener('click', () => toggleSidebar(false));

    savePrompt.addEventListener('click', saveSettings);
    resetPrompt.addEventListener('click', () => {
        systemPrompt.value = defaultPrompt;
        tempSlider.value = 0.1;
        tempValue.textContent = '0.10';
        showSaveStatus('Reset to default — click Save to apply', '');
    });

    tempSlider.addEventListener('input', () => {
        tempValue.textContent = parseFloat(tempSlider.value).toFixed(2);
    });
    */

    // ── Send message ──────────────────────────────────────────────
    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text || isStreaming) return;

        isStreaming = true;
        sendBtn.disabled = true;
        chatInput.value = '';
        autoResize(chatInput);

        // Hide welcome, reveal share button
        if (welcome) welcome.style.display = 'none';
        shareBtn.style.display = 'inline-flex';

        // Add user message
        addMessage('user', text);

        // Add assistant placeholder with thinking
        const assistantMsg = addMessage('assistant', '', true);
        const bubble = assistantMsg.querySelector('.message-bubble');
        const sourcesContainer = assistantMsg.querySelector('.sources-container');

        // Show thinking indicator
        const startTime = Date.now();
        bubble.innerHTML = thinkingHTML();
        const thinkingTimer = setInterval(() => {
            const el = bubble.querySelector('.thinking-elapsed');
            if (el) {
                const secs = Math.floor((Date.now() - startTime) / 1000);
                el.textContent = `${secs}s`;
            }
        }, 1000);

        // Streaming preview toggle
        const streamingPreview = bubble.querySelector('.streaming-preview');
        const expandBtn = bubble.querySelector('.thinking-expand-btn');
        let isPreviewOpen = false;
        if (expandBtn) {
            expandBtn.addEventListener('click', () => {
                isPreviewOpen = !isPreviewOpen;
                streamingPreview.classList.toggle('open', isPreviewOpen);
                expandBtn.classList.toggle('rotated', isPreviewOpen);
                if (isPreviewOpen && fullText) {
                    streamingPreview.textContent = fullText;
                    streamingPreview.scrollTop = streamingPreview.scrollHeight;
                }
            });
        }

        // Stream response (buffered — user only sees thinking)
        let fullText = '';
        let usageData = null;
        let streamError = null;

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: getHeaders(),
                body: JSON.stringify({
                    message: text,
                    session_id: sessionId
                }),
            });

            if (response.status === 401 || response.status === 403) {
                clearInterval(thinkingTimer);
                localStorage.removeItem('rag_api_key');
                bubble.innerHTML = `<span style="color:var(--error)">Access denied — please reload and enter your access key.</span>`;
                authModal.style.display = 'flex';
                isStreaming = false;
                sendBtn.disabled = !chatInput.value.trim();
                return;
            }

            if (response.status === 429) {
                clearInterval(thinkingTimer);
                bubble.innerHTML = `<span style="color:var(--error)">Too many requests — please wait a moment before trying again.</span>`;
                isStreaming = false;
                sendBtn.disabled = !chatInput.value.trim();
                return;
            }

            if (!response.ok) {
                clearInterval(thinkingTimer);
                bubble.innerHTML = `<span style="color:var(--error)">Server error (${response.status}). Please try again.</span>`;
                isStreaming = false;
                sendBtn.disabled = !chatInput.value.trim();
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    try {
                        const event = JSON.parse(line.slice(6));
                        if (event.type === 'token') {
                            fullText += event.data;
                            // Live-update streaming preview if open
                            if (isPreviewOpen && streamingPreview) {
                                streamingPreview.textContent = fullText;
                                streamingPreview.scrollTop = streamingPreview.scrollHeight;
                            }
                        } else if (event.type === 'sources') {
                            if (event.data && event.data.length > 0) {
                                renderSources(sourcesContainer, event.data);
                            }
                        } else if (event.type === 'usage') {
                            usageData = event.data;
                        } else if (event.type === 'error') {
                            streamError = event.data;
                        }
                    } catch (e) {
                        // skip malformed
                    }
                }
            }

            // Reveal final answer (or error)
            clearInterval(thinkingTimer);
            if (streamError) {
                bubble.innerHTML = `<span style="color:var(--error)">${escapeHtml(streamError)}</span>`;
            } else {
                bubble.innerHTML = renderMarkdown(fullText) || '<em style="color:var(--text-muted)">No response received.</em>';
            }
            // Add reveal AFTER innerHTML so the animation plays on the actual content
            void bubble.offsetWidth; // force reflow so animation triggers cleanly
            bubble.classList.add('reveal');

            // Show token usage if available
            if (usageData) {
                const usageEl = document.createElement('div');
                usageEl.className = 'token-usage';
                const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
                usageEl.textContent = `Time: ${elapsed}s`;
                bubble.parentElement.appendChild(usageEl);
            }

        } catch (err) {
            clearInterval(thinkingTimer);
            if (err.message && err.message.includes("403")) {
                bubble.innerHTML = `<span style="color: var(--error);">Access Denied: Invalid Key. Please reload to try again.</span>`;
                // Optionally trigger auth modal again
                localStorage.removeItem('rag_api_key');
            } else {
                bubble.innerHTML = `<span style="color: var(--error);">Connection error: ${err.message || 'Unknown error'}</span>`;
            }
        }

        isStreaming = false;
        sendBtn.disabled = !chatInput.value.trim();
        scrollToBottom();
    }

    // (Stream events are handled inline in sendMessage)

    // ── Add message to chat ───────────────────────────────────────
    function addMessage(role, content, showTyping = false) {
        const msg = document.createElement('div');
        msg.className = `message message-${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = role === 'user' ? 'U' : 'AI';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';

        if (showTyping) {
            bubble.innerHTML = typingHTML();
        } else {
            bubble.innerHTML = role === 'user' ? escapeHtml(content) : renderMarkdown(content);
        }

        contentDiv.appendChild(bubble);

        // Sources container for assistant messages
        if (role === 'assistant') {
            const sourcesContainer = document.createElement('div');
            sourcesContainer.className = 'sources-container';
            contentDiv.appendChild(sourcesContainer);
        }

        msg.appendChild(avatar);
        msg.appendChild(contentDiv);
        chatArea.appendChild(msg);
        scrollToBottom();

        return msg;
    }

    // ── Render sources ────────────────────────────────────────────
    function renderSources(container, sources) {
        if (!sources.length) return;

        const toggle = document.createElement('button');
        toggle.className = 'sources-toggle';
        toggle.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M6 9l6 6 6-6"/>
            </svg>
            ${sources.length} source${sources.length > 1 ? 's' : ''} found
        `;

        const list = document.createElement('div');
        list.className = 'sources-list';

        sources.forEach((s, i) => {
            const item = document.createElement('div');
            item.className = 'source-item';

            const header = document.createElement('div');
            header.className = 'source-header';
            header.innerHTML = `
                <span class="source-num">${i + 1}</span>
                <svg class="source-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M9 18l6-6-6-6"/>
                </svg>
                <span class="source-badge">${s.library}</span>
                <span class="source-name">${s.source_file} · p.${s.page_number}</span>
                <span class="source-score">${(s.score * 100).toFixed(0)}%</span>
            `;
            header.style.cursor = 'pointer';

            // "View" button — opens the full PDF in the document viewer
            const viewBtn = document.createElement('button');
            viewBtn.className = 'view-doc-btn';
            viewBtn.textContent = 'View';
            viewBtn.title = 'View full document';
            viewBtn.addEventListener('click', (e) => {
                e.stopPropagation(); // don't toggle the source expand
                openDocumentViewer(s.library, s.source_file, s.page_number);
            });
            header.appendChild(viewBtn);

            const textBlock = document.createElement('div');
            textBlock.className = 'source-text';
            textBlock.textContent = s.text || '(no text available)';

            header.addEventListener('click', () => {
                item.classList.toggle('expanded');
            });

            item.appendChild(header);
            item.appendChild(textBlock);
            list.appendChild(item);
        });

        toggle.addEventListener('click', () => {
            toggle.classList.toggle('open');
            list.classList.toggle('open');
        });

        container.appendChild(toggle);
        container.appendChild(list);
    }

    // ── Document Viewer ────────────────────────────────────────────
    const docViewer      = document.getElementById('docViewer');
    const docViewerFrame = document.getElementById('docViewerFrame');
    const docViewerTitle = document.getElementById('docViewerTitle');
    const docViewerClose = document.getElementById('docViewerClose');

    function openDocumentViewer(library, filename, page) {
        const url = `/api/documents/${encodeURIComponent(library)}/${encodeURIComponent(filename)}#page=${page}&toolbar=0`;
        // Force reload even if same URL — clear first, then set on next frame
        docViewerFrame.src = 'about:blank';
        requestAnimationFrame(() => { docViewerFrame.src = url; });
        docViewerTitle.textContent = `${filename} — p.${page}`;
        document.body.classList.add('doc-viewer-open');
    }

    function closeDocumentViewer() {
        document.body.classList.remove('doc-viewer-open');
        docViewerFrame.src = '';  // release PDF from browser memory
    }

    docViewerClose.addEventListener('click', closeDocumentViewer);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && document.body.classList.contains('doc-viewer-open')) {
            closeDocumentViewer();
        }
    });

    // ── Settings ──────────────────────────────────────────────────
    async function loadSettings() {
        try {
            const res = await fetch(`/api/settings?session_id=${sessionId}`, {
                headers: getHeaders()
            });
            const data = await res.json();
            systemPrompt.value = data.system_prompt;
            defaultPrompt = data.system_prompt;
            if (data.temperature !== undefined) {
                tempSlider.value = data.temperature;
                tempValue.textContent = parseFloat(data.temperature).toFixed(2);
            }
        } catch (e) {
            console.error('Failed to load settings:', e);
        }
    }

    async function saveSettings() {
        try {
            const res = await fetch('/api/settings', {
                method: 'PUT',
                headers: getHeaders(),
                body: JSON.stringify({
                    session_id: sessionId,
                    system_prompt: systemPrompt.value,
                    temperature: parseFloat(tempSlider.value),
                }),
            });
            if (res.ok) {
                showSaveStatus('✓ Saved successfully', 'success');
            } else {
                showSaveStatus('Failed to save', 'error');
            }
        } catch (e) {
            showSaveStatus('Connection error', 'error');
        }
    }

    function showSaveStatus(text, className) {
        saveStatus.textContent = text;
        saveStatus.className = `save-status ${className}`;
        setTimeout(() => {
            saveStatus.textContent = '';
            saveStatus.className = 'save-status';
        }, 3000);
    }

    function toggleSidebar(open) {
        sidebar.classList.toggle('open', open);
        sidebarOverlay.classList.toggle('open', open);
    }

    // ── Utilities ─────────────────────────────────────────────────
    function autoResize(el) {
        el.style.height = 'auto';
        el.style.height = Math.min(el.scrollHeight, 150) + 'px';
    }

    function scrollToBottom() {
        chatArea.scrollTop = chatArea.scrollHeight;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function renderMarkdown(text) {
        if (!text) return '';
        try {
            const rawHtml = marked.parse(text, { breaks: true });
            let clean = DOMPurify.sanitize(rawHtml);
            // Wrap "Source N" / "source N" mentions into a citation badge
            // $2 is guaranteed digits-only by \d+, so this is XSS-safe
            clean = clean.replace(/\b([Ss]ource)\s+(\d+)\b/g,
                '<span class="citation-ref">Source&nbsp;$2</span>');
            return clean;
        } catch (e) {
            return escapeHtml(text);
        }
    }

    function typingHTML() {
        return `<div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>`;
    }

    function thinkingHTML() {
        return `<div class="thinking-wrapper">
            <div class="thinking-status">
                <div class="thinking-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
                <span class="thinking-label">Searching corpus</span>
                <span class="thinking-elapsed">0s</span>
                <button class="thinking-expand-btn" title="Preview response as it streams">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                        <path d="M6 9l6 6 6-6"/>
                    </svg>
                    Live
                </button>
            </div>
            <div class="streaming-preview"></div>
        </div>`;
    }

    function removeTypingIndicator(bubble) {
        const indicator = bubble.querySelector('.typing-indicator');
        if (indicator) indicator.remove();
    }
});
