/* ═══════════════════════════════════════════════════════════════════════════
   BOUYGUES TELECOM — GenUI Engine v5 (Streaming Progressive)
   Chat-driven UI mutation: Claude generates HTML, injected PROGRESSIVELY
   into DOM as sections complete during streaming.
   ═══════════════════════════════════════════════════════════════════════════ */

// ── State ──
const state = {
    chatOpen: false,
    messages: [],
    isStreaming: false,
    originalHTML: {},
};

// ── DOM refs ──
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const chatToggle = $('#chatbot-toggle');
const chatPanel = $('#chatbot-panel');
const chatClose = $('#chatbot-close');
const chatMessages = $('#chatbot-messages');
const chatForm = $('#chatbot-form');
const chatInput = $('#chatbot-input');
const chatBadge = $('.chatbot-badge');
const genuiOverlay = $('#genui-overlay');

// ── GenUI section IDs that can be replaced ──
const GENUI_SECTIONS = [
    'genui-hero',
    'genui-about',
    'genui-stats',
    'genui-business',
    'genui-rejoindre',
    'genui-metiers',
    'genui-engagements'
];
const GENUI_SEPARATOR = '|||GENUI_HTML|||';

// ═══════════════════════════════════════════════════════════════════════════
// CHATBOT UI
// ═══════════════════════════════════════════════════════════════════════════

function toggleChat() {
    state.chatOpen = !state.chatOpen;
    chatPanel.classList.toggle('hidden', !state.chatOpen);
    if (state.chatOpen) {
        chatBadge.style.display = 'none';
        chatInput.focus();
    }
}

chatToggle.addEventListener('click', toggleChat);
chatClose.addEventListener('click', toggleChat);

function addChatMessage(role, text, isProcessing = false) {
    const msg = document.createElement('div');
    msg.className = `chat-message ${role === 'user' ? 'user' : 'bot'}`;
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    if (isProcessing) bubble.classList.add('processing');
    bubble.textContent = text;
    msg.appendChild(bubble);
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msg;
}

function addTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.id = 'typing-indicator';
    indicator.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
    chatMessages.appendChild(indicator);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return indicator;
}

function removeTypingIndicator() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
}

// ═══════════════════════════════════════════════════════════════════════════
// CHAT FORM SUBMIT → PROGRESSIVE STREAMING
// ═══════════════════════════════════════════════════════════════════════════

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text || state.isStreaming) return;

    chatInput.value = '';
    addChatMessage('user', text);
    state.messages.push({ role: 'user', content: text });

    state.isStreaming = true;
    addTypingIndicator();

    try {
        const fullResponse = await streamWithProgressiveInjection(state.messages);
        state.messages.push({ role: 'assistant', content: fullResponse });
    } catch (err) {
        removeTypingIndicator();
        addChatMessage('bot', 'Une erreur est survenue. Veuillez reessayer.');
        console.error('Chat error:', err);
    }

    state.isStreaming = false;
});

// ═══════════════════════════════════════════════════════════════════════════
// PROGRESSIVE STREAMING — inject sections as they complete
// ═══════════════════════════════════════════════════════════════════════════

async function streamWithProgressiveInjection(messages) {
    const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages }),
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';
    let sseBuffer = '';

    // Chat streaming bubble
    removeTypingIndicator();
    const streamMsg = document.createElement('div');
    streamMsg.className = 'chat-message bot';
    streamMsg.innerHTML = '<div class="chat-bubble"></div>';
    chatMessages.appendChild(streamMsg);
    const streamBubble = streamMsg.querySelector('.chat-bubble');

    // Progressive injection state
    let inHTML = false;
    let htmlBuffer = '';
    let injectedSections = new Set();
    let imagePromises = [];
    let separatorJustDetected = false;
    let processingMsg = null;
    let sectionsFadedOut = false;

    // Backup original sections for potential restore
    for (const id of GENUI_SECTIONS) {
        if (!state.originalHTML[id]) {
            const el = document.getElementById(id);
            if (el) state.originalHTML[id] = el.outerHTML;
        }
    }

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        sseBuffer += decoder.decode(value, { stream: true });
        const lines = sseBuffer.split('\n');
        sseBuffer = lines.pop();

        for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const data = line.slice(6).trim();
            if (data === '[DONE]') continue;

            try {
                const event = JSON.parse(data);
                if (event.type === 'text') {
                    fullText += event.content;

                    if (!inHTML && fullText.includes(GENUI_SEPARATOR)) {
                        inHTML = true;
                        separatorJustDetected = true;

                        const chatPart = fullText.split(GENUI_SEPARATOR)[0].trim();
                        streamBubble.textContent = chatPart;

                        processingMsg = addChatMessage('bot', 'Personnalisation de la page en cours...', true);
                        genuiOverlay.classList.remove('hidden');
                        fadeOutAllSections();
                        sectionsFadedOut = true;

                        htmlBuffer = fullText.split(GENUI_SEPARATOR).slice(1).join(GENUI_SEPARATOR);

                    } else if (inHTML) {
                        htmlBuffer += event.content;

                        const newlyInjected = tryInjectCompletedSections(htmlBuffer, injectedSections);
                        for (const { id, promise } of newlyInjected) {
                            injectedSections.add(id);
                            if (promise) imagePromises.push(promise);
                        }

                    } else {
                        streamBubble.textContent = fullText;
                    }

                    chatMessages.scrollTop = chatMessages.scrollHeight;

                } else if (event.type === 'error') {
                    throw new Error(event.content);
                }
            } catch (parseErr) {
                if (parseErr.message && !parseErr.message.includes('JSON')) {
                    throw parseErr;
                }
            }
        }
    }

    // Stream ended — inject the last section
    if (inHTML && htmlBuffer.trim()) {
        const finalInjected = tryInjectFinalSection(htmlBuffer, injectedSections);
        for (const { id, promise } of finalInjected) {
            injectedSections.add(id);
            if (promise) imagePromises.push(promise);
        }

        if (injectedSections.size === 0 && htmlBuffer.trim().length > 50) {
            const mainEl = document.getElementById('genui-main');
            if (mainEl) {
                mainEl.innerHTML = htmlBuffer;
                mainEl.classList.remove('genui-fade-out');
                mainEl.classList.add('genui-fade-in');
                const p = generateAllImages(mainEl);
                imagePromises.push(p);
            }
        }
    }

    if (imagePromises.length > 0) {
        await Promise.allSettled(imagePromises);
    }

    genuiOverlay.classList.add('hidden');
    if (processingMsg) {
        const bubble = processingMsg.querySelector('.chat-bubble');
        bubble.textContent = 'La page a ete personnalisee.';
        bubble.classList.remove('processing');
    }

    if (injectedSections.size > 0 || (inHTML && htmlBuffer.trim().length > 50)) {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    return fullText;
}

// ═══════════════════════════════════════════════════════════════════════════
// SECTION DETECTION AND PROGRESSIVE INJECTION
// ═══════════════════════════════════════════════════════════════════════════

function fadeOutAllSections() {
    for (const id of GENUI_SECTIONS) {
        const el = document.getElementById(id);
        if (el) {
            el.classList.add('genui-fade-out');
        }
    }
}

function findSectionBoundaries(html) {
    const regex = /<(?:div|section)[^>]*\bid="(genui-[^"]*)"[^>]*>/gi;
    const boundaries = [];
    let match;
    while ((match = regex.exec(html)) !== null) {
        boundaries.push({ index: match.index, id: match[1] });
    }
    return boundaries;
}

function tryInjectCompletedSections(htmlBuffer, alreadyInjected) {
    const boundaries = findSectionBoundaries(htmlBuffer);
    const results = [];

    for (let i = 0; i < boundaries.length - 1; i++) {
        const { id } = boundaries[i];
        if (alreadyInjected.has(id)) continue;

        const start = boundaries[i].index;
        const end = boundaries[i + 1].index;
        const sectionHTML = htmlBuffer.slice(start, end).trim();

        const promise = injectSingleSection(id, sectionHTML);
        results.push({ id, promise });
    }

    return results;
}

function tryInjectFinalSection(htmlBuffer, alreadyInjected) {
    const boundaries = findSectionBoundaries(htmlBuffer);
    const results = [];

    if (boundaries.length === 0) return results;

    for (let i = 0; i < boundaries.length; i++) {
        const { id } = boundaries[i];
        if (alreadyInjected.has(id)) continue;

        const start = boundaries[i].index;
        const end = i < boundaries.length - 1 ? boundaries[i + 1].index : htmlBuffer.length;
        const sectionHTML = htmlBuffer.slice(start, end).trim();

        const promise = injectSingleSection(id, sectionHTML);
        results.push({ id, promise });
    }

    return results;
}

async function injectSingleSection(id, sectionHTML) {
    const existing = document.getElementById(id);
    if (!existing) {
        console.warn(`GenUI: section #${id} not found in DOM`);
        return;
    }

    const temp = document.createElement('div');
    temp.innerHTML = sectionHTML;
    const newSection = temp.firstElementChild;
    if (!newSection) {
        console.warn(`GenUI: could not parse HTML for #${id}`);
        return;
    }

    newSection.id = id;

    existing.classList.add('genui-fade-out');
    await delay(300);

    existing.replaceWith(newSection);

    newSection.classList.add('genui-fade-out');
    requestAnimationFrame(() => {
        newSection.classList.remove('genui-fade-out');
        newSection.classList.add('genui-fade-in');
    });

    console.log(`GenUI: section #${id} injected`);

    return generateAllImages(newSection);
}

// ═══════════════════════════════════════════════════════════════════════════
// IMAGE GENERATION VIA FLUX (with retry)
// ═══════════════════════════════════════════════════════════════════════════

async function generateAllImages(container) {
    const images = container.querySelectorAll('img[data-generate]');
    if (images.length === 0) return;

    const queue = Array.from(images);
    const concurrency = 3;
    const executing = [];

    for (const img of queue) {
        const prompt = img.getAttribute('data-generate');
        if (!prompt) continue;

        img.classList.add('loading');
        img.src = 'data:image/svg+xml,' + encodeURIComponent(
            '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250" fill="#E8F4FD"><rect width="400" height="250"/></svg>'
        );

        const task = generateSingleImage(img, prompt);
        executing.push(task);

        if (executing.length >= concurrency) {
            await Promise.race(executing);
        }
    }

    await Promise.allSettled(executing);
}

async function generateSingleImage(imgEl, prompt, retries = 2) {
    for (let attempt = 0; attempt <= retries; attempt++) {
        try {
            const resp = await fetch('/api/generate-image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt }),
            });

            if (!resp.ok) {
                if (attempt < retries) {
                    console.warn(`Image gen attempt ${attempt + 1} failed (HTTP ${resp.status}), retrying...`);
                    await delay(1000 * (attempt + 1));
                    continue;
                }
                throw new Error(`HTTP ${resp.status}`);
            }

            const data = await resp.json();
            if (data.url) {
                if (data.url.startsWith('data:') || data.url.startsWith('http')) {
                    imgEl.src = data.url;
                } else {
                    imgEl.src = `data:image/png;base64,${data.url}`;
                }
                imgEl.classList.remove('loading');
                imgEl.removeAttribute('data-generate');
                return;
            } else if (attempt < retries) {
                console.warn(`Image gen attempt ${attempt + 1}: no URL in response, retrying...`);
                await delay(1000 * (attempt + 1));
                continue;
            }
        } catch (err) {
            if (attempt < retries) {
                console.warn(`Image gen attempt ${attempt + 1} error:`, err.message, '— retrying...');
                await delay(1000 * (attempt + 1));
                continue;
            }
            console.error('Image gen failed after retries:', err);
        }
    }
    imgEl.classList.remove('loading');
}

// ═══════════════════════════════════════════════════════════════════════════
// UTILITY
// ═══════════════════════════════════════════════════════════════════════════

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ── Mobile menu toggle ──
document.addEventListener('DOMContentLoaded', () => {
    console.log('Bouygues Telecom — GenUI Engine v5 (Streaming Progressive) loaded');

    const burger = document.querySelector('.bytel-burger');
    const nav = document.querySelector('.bytel-nav');
    if (burger && nav) {
        burger.addEventListener('click', () => {
            nav.classList.toggle('active');
            const expanded = burger.getAttribute('aria-expanded') === 'true';
            burger.setAttribute('aria-expanded', !expanded);
        });
    }

    setTimeout(() => {
        if (!state.chatOpen && chatBadge) {
            chatBadge.style.display = 'none';
        }
    }, 8000);
});
