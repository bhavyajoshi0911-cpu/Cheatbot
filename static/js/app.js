document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('searchInput');
    const suggestionsBox = document.getElementById('searchSuggestions');
    const resultsGrid = document.getElementById('resourceResults');
    const assistantResponse = document.getElementById('assistantResponse');
    const searchSubmitBtn = document.getElementById('searchSubmitBtn');
    const voiceInputBtn = document.getElementById('voiceInputBtn');
    const quickLaunchBtn = document.getElementById('quickLaunchBtn');
    const micPermissionNotice = document.getElementById('micPermissionNotice');
    const micPermissionClose = document.querySelector('.permission-notice__close');
    const themeToggle = document.querySelector('.mode-toggle');

    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach((item) => {
        const href = item.getAttribute('href');
        if (!href || href === '#') return;

        const targetPath = new URL(href, window.location.origin).pathname;
        if (window.location.pathname === targetPath) {
            item.classList.add('active');
        }

        item.addEventListener('click', () => {
            navItems.forEach((navItem) => navItem.classList.remove('active'));
            item.classList.add('active');
        });
    });

    const chatConversation = document.getElementById('chatConversation');

    const appendFormattedText = (container, text) => {
        const fragment = document.createDocumentFragment();
        const lines = String(text || '').split(/\r?\n/);

        lines.forEach((line) => {
            if (!line.trim()) return;
            const paragraph = document.createElement(/^\s*[-*]\s+/.test(line) ? 'li' : 'p');
            if (paragraph.tagName === 'LI') {
                paragraph.className = 'assistant-list-item';
                line = line.replace(/^\s*[-*]\s+/, '');
            }

            const parts = line.split(/(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`)/g);
            parts.forEach((part) => {
                if (/^\*\*[^*]+\*\*$/.test(part) || /^__[^_]+__$/.test(part)) {
                    const strong = document.createElement('strong');
                    strong.textContent = part.slice(2, -2);
                    paragraph.appendChild(strong);
                } else if (/^`[^`]+`$/.test(part)) {
                    const code = document.createElement('code');
                    code.textContent = part.slice(1, -1);
                    paragraph.appendChild(code);
                } else {
                    paragraph.appendChild(document.createTextNode(part));
                }
            });
            fragment.appendChild(paragraph);
        });

        container.appendChild(fragment);
    };

    const addChatMessage = (sender, text) => {
        if (!chatConversation) return;

        const lastUserMessage = chatConversation.querySelector('.chat-message.user:last-child .chat-bubble')?.textContent?.trim();
        if (sender === 'user' && lastUserMessage && lastUserMessage === text.trim()) {
            return;
        }

        const row = document.createElement('div');
        row.className = `chat-message ${sender}`;
        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble';
        if (sender === 'assistant') {
            appendFormattedText(bubble, text);
        } else {
            bubble.textContent = text;
        }
        row.appendChild(bubble);
        chatConversation.appendChild(row);
        chatConversation.classList.add('visible');
        chatConversation.scrollTop = chatConversation.scrollHeight;
    };

    const showAssistantResponse = (text, tone = 'info') => {
        if (!assistantResponse) return;
        if (chatConversation && chatConversation.classList.contains('visible')) {
            assistantResponse.classList.remove('visible');
            assistantResponse.classList.add('hidden');
            assistantResponse.textContent = '';
            return;
        }
        assistantResponse.classList.remove('hidden', 'success', 'error', 'info');
        assistantResponse.classList.add(tone === 'error' ? 'error' : tone === 'success' ? 'success' : 'info');
        assistantResponse.classList.add('visible');
        assistantResponse.textContent = text;
    };

    const showMicPermissionNotice = (visible = true) => {
        if (!micPermissionNotice) return;
        micPermissionNotice.classList.toggle('hidden', !visible);
    };

    const isLikelyAssistantQuery = (query) => {
        if (!query) return false;

        const trimmed = query.trim();
        if (!trimmed) return false;

        const lower = trimmed.toLowerCase();
        const explicitCommandPattern = /^(open|launch|start|run|visit|go to|goto|search|find|lookup|look up)\b/i;
        const directSitePattern = /^(google|youtube|canva|github|gitlab|notion|gmail|slack|teams|stackoverflow|w3schools|coursera|udemy|chatgpt|openai|vscode|vs code)$/i;
        const questionPattern = /\?|\b(what|who|why|how|when|where|which|explain|tell me|define|compare|create|show me|list|best|difference|can you|please|what's|who's)\b/i;

        if (explicitCommandPattern.test(lower)) {
            return false;
        }

        if (directSitePattern.test(lower)) {
            return false;
        }

        if (questionPattern.test(lower)) {
            return true;
        }

        const hasWhitespace = /\s/.test(trimmed);
        if (hasWhitespace) {
            return true;
        }

        return false;
    };

    const callAssistant = async (query) => {
        if (searchInput.dataset.busy === 'true') return;
        searchInput.dataset.busy = 'true';
        if (searchSubmitBtn) {
            searchSubmitBtn.disabled = true;
            searchSubmitBtn.classList.add('is-loading');
            searchSubmitBtn.setAttribute('aria-busy', 'true');
        }

        try {
            const response = await fetch('/api/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ question: query })
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                showAssistantResponse(data.error || data.answer || 'Unable to process your request.', 'error');
                return;
            }

            if (chatConversation) {
                addChatMessage('user', query);
                addChatMessage('assistant', data.answer || 'Here is what I found.');
                showAssistantResponse('', 'info');
            } else {
                showAssistantResponse(data.answer || 'Here is what I found.', data.intent === 'OPEN_APPLICATION' ? 'success' : 'info');
            }

            if (data.action && data.action.type === 'open_website') {
                window.open(data.action.url, '_blank', 'noopener,noreferrer');
            }
            if (data.action && data.action.type === 'web_search') {
                window.open(data.action.url, '_blank', 'noopener,noreferrer');
            }
            if (data.action && data.action.type === 'youtube_search') {
                window.open(data.action.url, '_blank', 'noopener,noreferrer');
            }
        } catch (error) {
            showAssistantResponse('The assistant is temporarily unavailable. Please try again.', 'error');
        } finally {
            searchInput.dataset.busy = 'false';
            if (searchSubmitBtn) {
                searchSubmitBtn.disabled = false;
                searchSubmitBtn.classList.remove('is-loading');
                searchSubmitBtn.removeAttribute('aria-busy');
            }
        }
    };

    const openSpokenTarget = (spokenText) => {
        const text = (spokenText || '').trim();
        if (!text) return;

        const normalized = text.toLowerCase();
        const directTargets = {
            youtube: 'https://www.youtube.com',
            whatsapp: 'https://web.whatsapp.com',
            google: 'https://www.google.com/search?q=' + encodeURIComponent(text),
            github: 'https://github.com',
            email: 'https://mail.google.com/mail/u/0/'
        };

        if (normalized.includes('youtube')) {
            window.open(directTargets.youtube, '_blank', 'noopener,noreferrer');
            return;
        }
        if (normalized.includes('whatsapp')) {
            window.open(directTargets.whatsapp, '_blank', 'noopener,noreferrer');
            return;
        }
        if (normalized.includes('github')) {
            window.open(directTargets.github, '_blank', 'noopener,noreferrer');
            return;
        }
        if (normalized.includes('email')) {
            window.open(directTargets.email, '_blank', 'noopener,noreferrer');
            return;
        }

        const query = text.replace(/^(open|launch|go to|visit|start|search for|find)/i, '').trim();
        const url = 'https://www.google.com/search?q=' + encodeURIComponent(query || text);
        window.open(url, '_blank', 'noopener,noreferrer');
    };

    const requestMicrophonePermission = async () => {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error('microphone-not-supported');
        }

        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach((track) => track.stop());
    };

    const setupVoiceInput = () => {
        if (!voiceInputBtn || !searchInput) return;

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            voiceInputBtn.disabled = true;
            voiceInputBtn.title = 'Voice input is not supported in this browser';
            voiceInputBtn.setAttribute('aria-label', 'Voice input is not supported in this browser');
            if (quickLaunchBtn) {
                quickLaunchBtn.disabled = true;
                quickLaunchBtn.title = 'Quick launch voice input is not supported in this browser';
                quickLaunchBtn.setAttribute('aria-label', 'Quick launch voice input is not supported in this browser');
            }
            return;
        }

        const getSpeechTranscript = (event) => {
            if (!event || !event.results || event.results.length === 0) return '';
            const result = event.results[event.resultIndex >= 0 ? event.resultIndex : 0] || event.results[0];
            if (!result) return '';
            return Array.from(result)
                .map((item) => item?.transcript || '')
                .join(' ')
                .trim();
        };

        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'en-IN';
        let originalText = '';

        recognition.addEventListener('start', () => {
            originalText = searchInput.value.trim();
            voiceInputBtn.classList.add('is-listening');
            voiceInputBtn.setAttribute('aria-label', 'Stop voice input');
            voiceInputBtn.title = 'Listening... click to stop';
            searchInput.placeholder = 'Listening...';
        });

        recognition.addEventListener('result', (event) => {
            const transcript = Array.from(event.results)
                .map((result) => result[0].transcript)
                .join(' ')
                .trim();
            searchInput.value = [originalText, transcript].filter(Boolean).join(' ');
            searchInput.dispatchEvent(new Event('input', { bubbles: true }));
        });

        recognition.addEventListener('end', () => {
            voiceInputBtn.classList.remove('is-listening');
            voiceInputBtn.setAttribute('aria-label', 'Speak your question');
            voiceInputBtn.title = 'Speak your question';
            searchInput.placeholder = 'Ask me anything...';
            searchInput.focus();
        });

        recognition.addEventListener('error', (event) => {
            if (event.error !== 'aborted') {
                const messageMap = {
                    'not-allowed': 'Microphone access is blocked. Please click the browser lock icon, allow Microphone, then refresh and try again.',
                    'audio-capture': 'No microphone was found. Please check your microphone and try again.',
                    'network': 'Speech service is offline. Please try again in a moment.',
                };
                showMicPermissionNotice(event?.error === 'not-allowed');
                showAssistantResponse(messageMap[event?.error] || 'Voice input could not start. Please allow microphone access and try again.', 'error');
            }
        });

        voiceInputBtn.addEventListener('click', async () => {
            if (voiceInputBtn.classList.contains('is-listening')) {
                recognition.stop();
                return;
            }

            try {
                await requestMicrophonePermission();
                showMicPermissionNotice(false);
                recognition.start();
            } catch (error) {
                recognition.stop();
                showMicPermissionNotice(true);
                showAssistantResponse('Microphone access is blocked. Please click the browser lock icon, allow Microphone, then refresh and try again.', 'error');
            }
        });

        if (quickLaunchBtn) {
            quickLaunchBtn.addEventListener('click', async () => {
                if (!SpeechRecognition) {
                    quickLaunchBtn.disabled = true;
                    quickLaunchBtn.title = 'Quick launch voice input is not supported in this browser';
                    quickLaunchBtn.setAttribute('aria-label', 'Quick launch voice input is not supported in this browser');
                    showAssistantResponse('Quick launch voice input is not supported in this browser.', 'error');
                    return;
                }

                try {
                    await requestMicrophonePermission();
                    showMicPermissionNotice(false);
                } catch (error) {
                    showMicPermissionNotice(true);
                    showAssistantResponse('Microphone access is blocked. Please click the browser lock icon, allow Microphone, then refresh and try again.', 'error');
                    return;
                }

                const launchRecognition = new SpeechRecognition();
                launchRecognition.continuous = false;
                launchRecognition.interimResults = false;
                launchRecognition.lang = 'en-IN';
                quickLaunchBtn.classList.add('is-listening');
                quickLaunchBtn.setAttribute('aria-label', 'Listening for quick launch');

                launchRecognition.onresult = (event) => {
                    const spoken = getSpeechTranscript(event);
                    if (!spoken) {
                        return;
                    }
                    openSpokenTarget(spoken);
                    quickLaunchBtn.classList.remove('is-listening');
                    quickLaunchBtn.setAttribute('aria-label', 'Quick launch');
                };

                launchRecognition.onerror = (event) => {
                    quickLaunchBtn.classList.remove('is-listening');
                    quickLaunchBtn.setAttribute('aria-label', 'Quick launch');

                    if (event && event.error === 'aborted') {
                        return;
                    }

                    const messageMap = {
                        'no-speech': 'Quick launch did not hear a clear request. Please try again.',
                        'not-allowed': 'Microphone access is blocked. Please click the browser lock icon, allow Microphone, then refresh and try again.',
                        'audio-capture': 'No microphone was found. Please check your microphone and try again.',
                        'network': 'Quick launch is temporarily unavailable because the speech service is offline. Please try again in a moment.',
                    };

                    showAssistantResponse(messageMap[event?.error] || 'Quick launch could not hear your request. Please try again.', 'error');
                };

                launchRecognition.onend = () => {
                    quickLaunchBtn.classList.remove('is-listening');
                    quickLaunchBtn.setAttribute('aria-label', 'Quick launch');
                };

                try {
                    launchRecognition.start();
                } catch (error) {
                    quickLaunchBtn.classList.remove('is-listening');
                    quickLaunchBtn.setAttribute('aria-label', 'Quick launch');
                    showAssistantResponse('Quick launch could not start. Please allow microphone access and try again.', 'error');
                }
            });
        }
    };

    if (micPermissionClose) {
        micPermissionClose.addEventListener('click', () => showMicPermissionNotice(false));
    }

    const applyTheme = (theme) => {
        const selectedTheme = theme === 'dark' ? 'dark' : 'light';
        document.body.setAttribute('data-theme', selectedTheme);
        localStorage.setItem('cheatbot-theme', selectedTheme);

        if (themeToggle) {
            const icon = themeToggle.querySelector('i');
            if (icon) {
                icon.className = selectedTheme === 'dark' ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
            }
            themeToggle.setAttribute('aria-label', selectedTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
        }

        document.querySelectorAll('.theme-switcher .btn').forEach((button) => {
            const isActive = button.dataset.theme === selectedTheme;
            button.classList.toggle('active', isActive);
            button.setAttribute('aria-pressed', String(isActive));
        });
    };

    const savedTheme = localStorage.getItem('cheatbot-theme') || 'light';
    applyTheme(savedTheme);

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const nextTheme = document.body.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            applyTheme(nextTheme);
        });
    }

    document.querySelectorAll('.theme-switcher .btn').forEach((button) => {
        button.addEventListener('click', () => {
            applyTheme(button.dataset.theme || 'light');
        });
    });

    const handleOpen = (event, url, openType) => {
        if (openType === 'website' && url) {
            event.preventDefault();
            window.open(url, '_blank', 'noopener,noreferrer');
            return true;
        }
        return false;
    };

    const bindFavoriteButton = (button) => {
        button.addEventListener('click', async () => {
            const resourceId = button.dataset.id;
            const response = await fetch(`/resource/${resourceId}/favorite`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });

            const data = await response.json();
            if (response.ok && data.success) {
                const isFavorited = Boolean(data.favorited);
                button.textContent = isFavorited ? '★ Favorited' : '★ Favorite';
                button.classList.toggle('active', isFavorited);
                button.setAttribute('aria-pressed', String(isFavorited));
            } else if (response.status === 401) {
                window.location.href = '/login';
            }
        });
    };

    const bindLaunchForm = (form) => {
        form.addEventListener('submit', (event) => {
            const button = form.querySelector('button[type="submit"]');
            const openType = form.dataset.openType;
            const url = form.dataset.url;

            if (button) {
                button.disabled = true;
                button.textContent = 'Launching...';
                button.classList.add('is-launching');
            }

            handleOpen(event, url, openType);
        });
    };

    const normalizeText = (value = '') => value.toLowerCase().replace(/[^a-z0-9]/g, '');

    const filterVisibleResults = (query) => {
        if (!resultsGrid) return;

        const cards = [...resultsGrid.querySelectorAll('.resource-card')];
        const cleanQuery = (query || '').trim();

        if (!cleanQuery) {
            cards.forEach((card) => { card.style.display = 'block'; });
            return;
        }

        const aliasMap = {
            cheatgpt: 'chatgpt',
            gogle: 'google',
            googl: 'google',
            chatgptai: 'chatgpt',
            chagpt: 'chatgpt',
            canvaa: 'canva',
        };

        const normalizedQuery = normalizeText(cleanQuery);
        const directQuery = aliasMap[normalizedQuery] || normalizedQuery;

        cards.forEach((card) => {
            const name = (card.querySelector('h4')?.textContent || '').toLowerCase();
            const category = (card.querySelector('.resource-category')?.textContent || '').toLowerCase();
            const description = (card.querySelector('p')?.textContent || '').toLowerCase();
            const haystack = `${name} ${category} ${description}`;

            const textMatch = haystack.includes(normalizedQuery) || haystack.includes(directQuery);
            const tokenMatch = cleanQuery.toLowerCase().split(/\s+/).filter(Boolean).every((token) => {
                const tokenNorm = normalizeText(token);
                const tokenAlias = aliasMap[tokenNorm] || tokenNorm;
                return haystack.includes(tokenNorm) || haystack.includes(tokenAlias);
            });

            card.style.display = textMatch || tokenMatch ? 'block' : 'none';
        });
    };

    const renderResults = (items) => {
        if (!resultsGrid) return;
        resultsGrid.innerHTML = '';

        if (!items.length) {
            const empty = document.createElement('div');
            empty.className = 'empty-state';
            empty.textContent = 'No matching results found.';
            resultsGrid.appendChild(empty);
            return;
        }

        items.forEach((item) => {
            const article = document.createElement('article');
            article.className = 'resource-card';
            article.innerHTML = `
                <div class="resource-header">
                    <div class="resource-icon">${item.icon || '🔗'}</div>
                    <div>
                        <h4>${item.name}</h4>
                        <span class="resource-category">${item.category_name || 'General'}</span>
                    </div>
                </div>
                <p>${item.description || 'Useful developer resource.'}</p>
                <div class="resource-footer">
                    <button class="btn favorite-btn" type="button" data-id="${item.id}">★ Favorite</button>
                    <form class="launch-form" method="post" action="/resource/${item.id}/launch" data-open-type="${item.open_type || 'website'}" data-url="${item.url || ''}">
                        <button class="btn btn-primary" type="submit">Open →</button>
                    </form>
                </div>
            `;

            const favoriteButton = article.querySelector('.favorite-btn');
            if (favoriteButton) bindFavoriteButton(favoriteButton);

            const launchForm = article.querySelector('.launch-form');
            if (launchForm) bindLaunchForm(launchForm);

            resultsGrid.appendChild(article);
        });
    };

    if (!searchInput) return;

    setupVoiceInput();

    const buildSuggestions = (items) => {
        if (!suggestionsBox) return;
        suggestionsBox.innerHTML = '';
        if (!items.length) {
            suggestionsBox.classList.remove('visible');
            return;
        }

        items.forEach((item) => {
            const suggestion = document.createElement('div');
            suggestion.className = 'suggestion-item';
            suggestion.innerHTML = `
                <span>${item.icon || '🔗'} ${item.name}</span>
                <small>${item.category_name || 'General'}</small>
            `;
            suggestion.addEventListener('click', () => {
                searchInput.value = item.name;
                suggestionsBox.classList.remove('visible');
                renderResults([item]);
                if (item.open_type === 'website' && item.url) {
                    window.open(item.url, '_blank', 'noopener,noreferrer');
                    return;
                }
                const openForm = document.createElement('form');
                openForm.method = 'post';
                openForm.action = `/resource/${item.id}/launch`;
                document.body.appendChild(openForm);
                openForm.submit();
            });
            suggestionsBox.appendChild(suggestion);
        });
        suggestionsBox.classList.add('visible');
    };

    const fetchSearch = async (query) => {
        const cleanQuery = (query || '').trim();

        if (!cleanQuery) {
            suggestionsBox?.classList.remove('visible');
            if (resultsGrid) {
                const response = await fetch('/api/search?q=');
                const items = await response.json();
                renderResults(items.slice(0, 12));
                filterVisibleResults('');
            }
            return;
        }

        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(cleanQuery)}`);
            const items = await response.json();
            buildSuggestions(items.slice(0, 6));
            renderResults(items.slice(0, 12));
            filterVisibleResults(cleanQuery);
        } catch (error) {
            if (resultsGrid) {
                const cards = [...resultsGrid.querySelectorAll('.resource-card')];
                cards.forEach((card) => { card.style.display = 'block'; });
                filterVisibleResults(cleanQuery);
            }
        }
    };

    const submitSearch = async () => {
        const query = searchInput.value.trim();
        if (!query) {
            suggestionsBox?.classList.remove('visible');
            return;
        }

        if (isLikelyAssistantQuery(query)) {
            await callAssistant(query);
        } else {
            await fetchSearch(query);
        }
        suggestionsBox?.classList.remove('visible');
    };

    searchInput.addEventListener('input', (event) => {
        const query = event.target.value.trim();
        if (query && isLikelyAssistantQuery(query)) {
            suggestionsBox?.classList.remove('visible');
            return;
        }
        fetchSearch(query);
    });

    searchInput.addEventListener('keydown', async (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            await submitSearch();
        }
    });

    if (searchSubmitBtn) {
        searchSubmitBtn.addEventListener('click', async () => {
            await submitSearch();
        });
    }

    document.querySelectorAll('.prompt-chip').forEach((chip) => {
        chip.addEventListener('click', () => {
            const value = chip.textContent.trim();
            searchInput.value = value;
            searchInput.focus();
            callAssistant(value);
        });
    });

    document.addEventListener('keydown', (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
            event.preventDefault();
            searchInput.focus();
            searchInput.select();
        }

        if (event.key === 'Escape' && suggestionsBox) {
            suggestionsBox.classList.remove('visible');
        }
    });

    document.querySelectorAll('.launch-form').forEach((form) => {
        form.addEventListener('submit', (event) => {
            const button = form.querySelector('button[type="submit"]');
            const openType = form.dataset.openType;
            const url = form.dataset.url;

            if (button) {
                button.disabled = true;
                const originalText = button.textContent;
                button.dataset.originalText = originalText;
                button.textContent = 'Launching...';
                button.classList.add('is-launching');
            }

            handleOpen(event, url, openType);
        });
    });

    document.querySelectorAll('.btn-primary').forEach((button) => {
        if (button.closest('.launch-form')) return;
        if (button.closest('form') && button.closest('form').classList.contains('launch-form')) return;
    });

    document.querySelectorAll('.favorite-btn').forEach((button) => {
        button.addEventListener('click', async () => {
            const resourceId = button.dataset.id;
            const response = await fetch(`/resource/${resourceId}/favorite`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });

            const data = await response.json();
            if (response.ok && data.success) {
                const isFavorited = Boolean(data.favorited);
                button.textContent = isFavorited ? '★ Favorited' : '★ Favorite';
                button.classList.toggle('active', isFavorited);
                button.setAttribute('aria-pressed', String(isFavorited));
            } else if (response.status === 401) {
                window.location.href = '/login';
            }
        });
    });

    if (resultsGrid) {
        const cards = [...resultsGrid.querySelectorAll('.resource-card')];
        cards.forEach((card) => {
            const name = card.querySelector('h4')?.textContent || '';
            card.style.border = '1px solid transparent';
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-2px)';
            });
            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0)';
            });
        });
    }
});
