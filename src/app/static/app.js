/* ═══════════════════════════════════════════════════════════════
   RAG Agent — Chat UI Client Logic
   ═══════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
    // ── DOM refs ──────────────────────────────────────────────────
    const chatArea = document.getElementById('chatArea');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const clearChat = document.getElementById('clearChat');
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

    let isStreaming = false;
    let defaultPrompt = '';

    // ── Init ──────────────────────────────────────────────────────
    loadSettings();

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

    // ── Clear chat ────────────────────────────────────────────────
    clearChat.addEventListener('click', async () => {
        await fetch('/api/chat/history', { method: 'DELETE' });
        chatArea.innerHTML = '';
        chatArea.appendChild(welcome);
        welcome.style.display = 'flex';
    });

    // ── Sidebar ───────────────────────────────────────────────────
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

    // ── Send message ──────────────────────────────────────────────
    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text || isStreaming) return;

        isStreaming = true;
        sendBtn.disabled = true;
        chatInput.value = '';
        autoResize(chatInput);

        // Hide welcome
        if (welcome) welcome.style.display = 'none';

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

        // Stream response (buffered — user only sees thinking)
        let fullText = '';
        let usageData = null;

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text }),
            });

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
                        } else if (event.type === 'sources') {
                            if (event.data && event.data.length > 0) {
                                renderSources(sourcesContainer, event.data);
                            }
                        } else if (event.type === 'usage') {
                            usageData = event.data;
                        } else if (event.type === 'error') {
                            clearInterval(thinkingTimer);
                            bubble.innerHTML = `<span style="color: var(--error);">${event.data}</span>`;
                        }
                    } catch (e) {
                        // skip malformed
                    }
                }
            }

            // Reveal final markdown with fade-in
            clearInterval(thinkingTimer);
            bubble.classList.add('reveal');
            bubble.innerHTML = renderMarkdown(fullText);

            // Show token usage if available
            if (usageData) {
                const usageEl = document.createElement('div');
                usageEl.className = 'token-usage';
                const total = (usageData.input_tokens || 0) + (usageData.output_tokens || 0);
                const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
                usageEl.textContent = `${total.toLocaleString()} tokens (${usageData.input_tokens.toLocaleString()} in · ${usageData.output_tokens.toLocaleString()} out) · ${elapsed}s`;
                bubble.parentElement.appendChild(usageEl);
            }

        } catch (err) {
            clearInterval(thinkingTimer);
            bubble.innerHTML = `<span style="color: var(--error);">Connection error: ${err.message}</span>`;
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
                <svg class="source-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M9 18l6-6-6-6"/>
                </svg>
                <span class="source-badge">${s.library}</span>
                <span class="source-name">${s.source_file} · p.${s.page_number}</span>
                <span class="source-score">${(s.score * 100).toFixed(0)}%</span>
            `;
            header.style.cursor = 'pointer';

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

    // ── Settings ──────────────────────────────────────────────────
    async function loadSettings() {
        try {
            const res = await fetch('/api/settings');
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
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
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
            return marked.parse(text, { breaks: true });
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
        return `<div class="thinking-status">
            <div class="thinking-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
            <span class="thinking-label">Analyzing sources & forming response…</span>
            <span class="thinking-elapsed">0s</span>
        </div>`;
    }

    function removeTypingIndicator(bubble) {
        const indicator = bubble.querySelector('.typing-indicator');
        if (indicator) indicator.remove();
    }
});
