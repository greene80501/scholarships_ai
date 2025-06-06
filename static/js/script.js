// --- START OF FILE static/js/script.js ---

// Enhanced script.js with consolidated logic and AI recommendation functionality

// Global state management
let currentPage = 1;
let currentFilters = {};
let currentSort = 'relevance';
let viewMode = 'grid';
let isLoading = false;
let isAIResponding = false;
let conversationHistory = []; // Global for AI chat

// DOM content loaded event
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// Initialize the application
function initializeApp() {
    setupEventListeners();
    initializeCurrentYear(); // Set current year in footers

    const path = window.location.pathname;
    const search = window.location.search;

    // Redirect from home if search params exist
    if ((path === '/' || path.endsWith('index.html') || path.endsWith('/')) && search && !path.includes('search.html')) {
        let basePath = window.location.origin;
        if (path.includes('index.html')) {
           basePath += path.substring(0, path.lastIndexOf('/') + 1);
        } else if (path !== '/') {
            basePath += path;
        } else {
             basePath += '/';
        }
        if (basePath !== window.location.origin && !basePath.endsWith('/')) {
            basePath += '/';
        }
        window.location.href = basePath + 'search.html' + search;
        return;
    }
    
    initializeTheme();
    initializeScrollAnimations();
    
    if (path.includes('search.html')) {
        initializeSearchPage();
    } else if (path.includes('ai-recommend.html')) {
        initializeAIChatPage();
    } else if (path.includes('bookmarks.html')) {
        initializeBookmarksPage();
    } else if (path === '/' || path.endsWith('index.html') || path.endsWith('/')) {
        initializeHomePage();
    }
}

// Setup event listeners (consolidated)
function setupEventListeners() {
    // Theme toggle
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) themeToggle.addEventListener('click', toggleTheme);
    
    // Search form submissions
    const quickSearchForm = document.getElementById('quickSearchForm'); // New quick search on index.html
    if (quickSearchForm) quickSearchForm.addEventListener('submit', handleQuickSearchSubmit);

    const searchPageForm = document.getElementById('searchForm'); // Form on search.html
    if (searchPageForm) searchPageForm.addEventListener('submit', handleSearchSubmit);
    
    // Filters toggle (search.html)
    const filtersToggle = document.getElementById('filtersToggle');
    if (filtersToggle) filtersToggle.addEventListener('click', toggleFilters);
    
    // Sort change (search.html)
    const sortSelect = document.getElementById('sortBy');
    if (sortSelect) sortSelect.addEventListener('change', handleSortChange);
    
    // View toggle (search.html)
    const viewButtons = document.querySelectorAll('.view-btn');
    viewButtons.forEach(btn => btn.addEventListener('click', handleViewToggle));
    
    // Mobile navigation (all pages)
    const mobileMenuToggle = document.getElementById('mobileMenuToggle'); // From header.html
    const mainNavLinks = document.getElementById('mainNavLinks'); // Common ID for nav links container
    
    if (mobileMenuToggle && mainNavLinks) { // For all pages using header.html
        mobileMenuToggle.addEventListener('click', () => toggleMobileNav(mainNavLinks, mobileMenuToggle));
    }
    
    // AI Chat specific listeners (ai-recommend.html)
    const sendChatBtn = document.getElementById('sendBtn'); // ID from ai-recommend.html
    const chatInput = document.getElementById('chatInput');
    if (sendChatBtn && chatInput) {
        sendChatBtn.addEventListener('click', sendChatMessage);
        chatInput.addEventListener('input', function() { // Auto-resize and button enable/disable
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 100) + 'px'; // Max height 100px
            sendChatBtn.disabled = !this.value.trim();
        });
        chatInput.addEventListener('keypress', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendChatMessage();
            }
        });
    }
    
    // Click outside to close modals/panels
    document.addEventListener('click', handleOutsideClick);
    // Escape key to close modals/panels
    document.addEventListener('keydown', handleEscapeKey);
}

function initializeCurrentYear() {
    const yearElements = document.querySelectorAll('#currentYear, #currentYearSearch, #currentYearBookmarks'); // Targets all footer year spans
    yearElements.forEach(el => {
        if(el) el.textContent = new Date().getFullYear();
    });
}

// Initialize home page
function initializeHomePage() {
    loadHomePageStats();
}

// Initialize search page
function initializeSearchPage() {
    const urlParams = new URLSearchParams(window.location.search);
    currentFilters = Object.fromEntries(urlParams.entries());
    
    const formFilters = { ...currentFilters };
    delete formFilters.page;
    delete formFilters.sort;
    
    populateSearchForm(formFilters);
    
    currentPage = parseInt(urlParams.get('page')) || 1;
    currentSort = urlParams.get('sort') || 'relevance';
    const sortSelect = document.getElementById('sortBy');
    if (sortSelect) sortSelect.value = currentSort;

    performSearch();
    
    const searchDeadlineInput = document.getElementById('searchDeadline');
    if (searchDeadlineInput) {
        const today = new Date().toISOString().split('T')[0];
        searchDeadlineInput.min = today;
    }
}

// Initialize AI Chat Page
function initializeAIChatPage() {
    const chatMessagesContainer = document.getElementById('chatMessages');
    const chatInput = document.getElementById('chatInput');
    
    if (chatMessagesContainer && chatInput && conversationHistory.length === 0 && !chatMessagesContainer.querySelector('.message:not(.welcome-state)')) {
        // Static welcome HTML is already there.
    }
    if(chatInput) chatInput.focus(); 
}

// --- Bookmarks Page Functionality ---
async function initializeBookmarksPage() {
    const container = document.getElementById('bookmarkedScholarshipsContainer');
    const loadingPlaceholder = document.getElementById('bookmarksLoadingPlaceholder');
    const noBookmarksMessage = document.getElementById('noBookmarksMessage');

    if (!container || !loadingPlaceholder || !noBookmarksMessage) return;

    // Show loading initially
    loadingPlaceholder.style.display = 'flex';
    noBookmarksMessage.style.display = 'none';
    container.innerHTML = ''; // Clear previous content if any, except for placeholders
    container.appendChild(loadingPlaceholder); // Re-add loading placeholder
    container.appendChild(noBookmarksMessage); // And no bookmarks message, hidden

    const bookmarkedIds = JSON.parse(localStorage.getItem('bookmarkedScholarships')) || [];

    if (bookmarkedIds.length === 0) {
        loadingPlaceholder.style.display = 'none';
        noBookmarksMessage.style.display = 'flex';
        return;
    }

    try {
        const scholarshipPromises = bookmarkedIds.map(id =>
            fetch(`/api/scholarship/${id}`).then(response => {
                if (!response.ok) {
                    console.error(`Failed to fetch scholarship ID ${id}: ${response.status}`);
                    return null; // Return null for failed fetches to handle them later
                }
                return response.json();
            })
        );

        const results = await Promise.all(scholarshipPromises);
        const validScholarships = [];
        results.forEach(result => {
            if (result && result.success && result.scholarship) {
                validScholarships.push(result.scholarship);
            }
        });
        
        loadingPlaceholder.style.display = 'none';

        if (validScholarships.length === 0) {
            noBookmarksMessage.style.display = 'flex';
            if (bookmarkedIds.length > 0) { // If there were IDs but no valid scholarships fetched
                 noBookmarksMessage.querySelector('p').textContent = 'Could not load your bookmarked scholarships. They might have been removed or there was an error.';
            }
        } else {
            noBookmarksMessage.style.display = 'none';
            // Determine view mode (default to grid, or could be stored/passed)
            container.className = 'scholarships-grid'; // Or 'scholarships-list'
            validScholarships.forEach(scholarship => {
                const card = createScholarshipCard(scholarship); // Reuse existing card creation
                container.appendChild(card);
            });
            initializeCardInteractions(); // Re-initialize interactions for new cards
        }
    } catch (error) {
        console.error('Error loading bookmarked scholarships:', error);
        loadingPlaceholder.style.display = 'none';
        noBookmarksMessage.style.display = 'flex';
        noBookmarksMessage.querySelector('p').textContent = 'An error occurred while loading your bookmarks. Please try again later.';
    }
}


// --- AI Chat Functionality ---
function clearWelcomeState() {
    const welcomeState = document.querySelector('.welcome-state');
    if (welcomeState) {
        welcomeState.remove();
    }
}

async function sendChatMessage() {
    if (isAIResponding) return;

    const chatInput = document.getElementById('chatInput');
    const sendChatBtn = document.getElementById('sendBtn'); 
    
    if (!chatInput || !sendChatBtn) return;

    const message = chatInput.value.trim();
    if (!message) return;

    clearWelcomeState(); 
    chatInput.value = '';
    chatInput.style.height = 'auto'; 
    sendChatBtn.disabled = true;
    
    displayUserMessage(message);
    conversationHistory.push({ role: 'user', content: message });
    
    showEnhancedTypingIndicator();
    isAIResponding = true;
    showLoading("AI is thinking..."); 

    try {
        const response = await fetch('/api/ai/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                message: message,
                conversation_history: conversationHistory.slice(-12) // Increased history
            }),
        });

        hideLoading(); 

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ 
                ai_response: "I'm experiencing some technical difficulties. Please try again in a moment." 
            }));
            throw new Error(errorData.ai_response || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        hideEnhancedTypingIndicator();
        displayAIMessage(data.ai_response, true); 
        
        if (data.conversation_history && Array.isArray(data.conversation_history)) {
            conversationHistory = data.conversation_history;
        } else {
            conversationHistory.push({ role: 'assistant', content: data.ai_response });
        }

        if (data.scholarships && data.scholarships.length > 0) {
            setTimeout(() => displayEnhancedScholarshipRecommendations(data.scholarships), 600);
        } else {
            const recommendationsContainer = document.getElementById('aiScholarshipRecommendations');
            if (recommendationsContainer) recommendationsContainer.innerHTML = ''; 
        }

    } catch (error) {
        console.error('Error sending chat message:', error);
        hideLoading();
        hideEnhancedTypingIndicator();
        displayAIMessage("🔧 I'm having some technical difficulties. Please try rephrasing or try again later.", false); 
        conversationHistory.push({ role: 'assistant', content: "🔧 I'm having some technical difficulties. Please try rephrasing or try again later." });
    } finally {
        isAIResponding = false;
        if (sendChatBtn && chatInput) sendChatBtn.disabled = chatInput.value.trim() === ''; 
        if (chatInput) chatInput.focus();
    }
}

function displayUserMessage(message) {
    const chatMessagesContainer = document.getElementById('chatMessages');
    if (!chatMessagesContainer) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', 'user');
    const timestamp = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    
    messageDiv.innerHTML = `
        <div class="message-content">
            ${escapeHtml(message)}
            <div class="message-time">${timestamp}</div>
        </div>
        <div class="message-avatar">👤</div>
    `;
    chatMessagesContainer.appendChild(messageDiv);
    scrollToBottom(chatMessagesContainer);
}

function displayAIMessage(message, isHTML = false) {
    const chatMessagesContainer = document.getElementById('chatMessages');
    if (!chatMessagesContainer) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', 'ai');
    const timestamp = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    let formattedMessage = isHTML ? formatAIMessage(message) : escapeHtml(message);
    
    messageDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            ${formattedMessage}
            <div class="message-time">${timestamp}</div>
        </div>
    `;
    chatMessagesContainer.appendChild(messageDiv);
    if (!message.toLowerCase().includes('recommendation_mode_activated') && !message.toLowerCase().includes('found') && !message.toLowerCase().includes('scholarships for you')) {
        setTimeout(() => addContextualSuggestions(messageDiv, message), 1000);
    }
    scrollToBottom(chatMessagesContainer);
}

function formatAIMessage(message) { 
    return message
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') 
        .replace(/\*(.*?)\*/g, '<em>$1</em>')        
        .replace(/•/g, '<span style="color: var(--accent-primary); font-weight: bold;">•</span>') 
        .replace(/\n/g, '<br>')                       
        .replace(/🎯|🔍|💡|⚡|🎓|💬|📋|✨|🚀|💰|🏆/g, '<span style="font-size: 1.1em;">$&</span>'); 
}

function addContextualSuggestions(messageElement, aiMessage) {
    const suggestions = [];
    const lowerMessage = aiMessage.toLowerCase();
    
    if (lowerMessage.includes('field of study') || lowerMessage.includes('what do you study')) {
        suggestions.push("Engineering", "Business", "Arts & Humanities", "Medicine/Health");
    } 
    else if (lowerMessage.includes('education level') || lowerMessage.includes('what level are you')) {
        suggestions.push("High School", "Undergraduate", "Graduate");
    }
    else if (lowerMessage.includes('anything else') || lowerMessage.includes('next steps') || (lowerMessage.includes("what would you like to do") && messageElement.parentElement.querySelector('.enhanced-ai-card'))) {
        suggestions.push("Show high-value scholarships", "No essay scholarships", "International student options");
    }
    else if (conversationHistory.length < 5 && (lowerMessage.includes('welcome') || lowerMessage.includes('quick start') || lowerMessage.includes('let\'s get started'))) {
         suggestions.push("I study computer science with 3.2 GPA", "High school senior, STEM focus", "Graduate student in business looking for funding");
    }
    
    if (suggestions.length > 0) {
        const suggestionsContainer = document.createElement('div');
        suggestionsContainer.className = 'suggestions-container'; 
        suggestions.forEach(suggestionText => {
            const chip = document.createElement('button');
            chip.className = 'suggestion-chip';
            chip.textContent = suggestionText;
            chip.onclick = () => sendSuggestion(suggestionText); 
            suggestionsContainer.appendChild(chip);
        });
        messageElement.querySelector('.message-content').appendChild(suggestionsContainer);
    }
}

function showEnhancedTypingIndicator() {
    const chatMessagesContainer = document.getElementById('chatMessages');
    if (!chatMessagesContainer || document.getElementById('typingIndicator')) return; 
    
    const typingDiv = document.createElement('div');
    typingDiv.classList.add('message', 'ai', 'typing-indicator');
    typingDiv.id = 'typingIndicator'; 
    typingDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
            <span>AI is analyzing your request...</span>
        </div>
    `;
    chatMessagesContainer.appendChild(typingDiv);
    scrollToBottom(chatMessagesContainer);
}

function hideEnhancedTypingIndicator() {
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) typingIndicator.remove();
}

function displayEnhancedScholarshipRecommendations(scholarships) {
    const recommendationsContainer = document.getElementById('aiScholarshipRecommendations');
    if (!recommendationsContainer) return;

    recommendationsContainer.innerHTML = ''; 
    
    const containerDiv = document.createElement('div');
    containerDiv.className = 'ai-container'; 

    const headerDiv = document.createElement('div');
    headerDiv.innerHTML = ` 
        <h2>🎯 AI-Matched Scholarships</h2>
        <p>Found ${scholarships.length} scholarship${scholarships.length === 1 ? '' : 's'} tailored to your profile</p>
    `;
    containerDiv.appendChild(headerDiv);

    const grid = document.createElement('div');
    grid.className = 'scholarships-grid'; 

    scholarships.forEach((scholarship, index) => {
        const card = createEnhancedScholarshipCard(scholarship, index);
        grid.appendChild(card);
    });
    containerDiv.appendChild(grid);
    
    const actionsDiv = document.createElement('div');
    actionsDiv.innerHTML = `
        <h3>What would you like to do next?</h3>
        <div>
            <button onclick="askForMoreRecommendations()" class="btn-primary">🔍 Find More</button>
            <button onclick="askForApplicationTips()" class="btn-secondary">💡 Application Tips</button>
            <button onclick="askForHighValueScholarships()" class="btn-secondary">💰 High-Value Only</button>
        </div>
    `;
    containerDiv.appendChild(actionsDiv);
    recommendationsContainer.appendChild(containerDiv);
    
    recommendationsContainer.classList.add('show'); 
    setTimeout(() => recommendationsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' }), 300);
    initializeCardInteractions(); 
}

function createEnhancedScholarshipCard(scholarship, index) {
    const card = document.createElement('div');
    card.className = 'scholarship-card enhanced-ai-card'; 
    card.dataset.scholarshipId = scholarship.id;
    
    const matchScore = calculateAIMatchScore(scholarship); 
    const deadline = scholarship.due_date ? formatDate(scholarship.due_date) : 'Varies';
    const keywords = Array.isArray(scholarship.keywords) ? scholarship.keywords : [];
    const keywordTags = keywords.slice(0, 2).map(keyword => `<span class="tag">${keyword}</span>`).join('');
    
    card.innerHTML = `
        <div class="card-header">
            <div class="card-badge">${scholarship.amount_display || 'Amount Varies'}</div>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                 <div class="ai-match-badge">🤖 ${matchScore}% Match</div>
                 <button class="bookmark-btn" onclick="toggleBookmark(event, ${scholarship.id})" aria-label="Bookmark scholarship" aria-pressed="false">
                    <svg width="18" height="18" viewBox="0 0 24 24"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
                </button>
            </div>
        </div>
        <div class="card-content">
            <h3 class="card-title">${scholarship.title || 'Untitled Scholarship'}</h3>
            <div class="card-organization">${scholarship.organization_name || 'Unknown Organization'}</div>
            <div class="ai-insights">
                <div>🎯 Why this matches you:</div>
                <div>${generateAIInsight(scholarship)}</div>
            </div>
            <div class="card-description">${truncateText(scholarship.eligibility_summary_text || scholarship.description_summary || 'No detailed description available.', 100)}</div>
            ${keywordTags ? `<div class="card-tags">${keywordTags}</div>` : ''}
            <div class="card-meta">
                <div class="meta-item"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>Due: ${deadline}</div>
                <div class="meta-item"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>${scholarship.education_level || 'All Levels'}</div>
                ${scholarship.gpa_requirement ? `<div class="meta-item"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>GPA: ${scholarship.gpa_requirement}${scholarship.gpa_requirement.toString().includes('+') ? '' : '+'}</div>` : ''}
            </div>
        </div>
        <div class="card-actions">
            <button class="btn-primary" onclick="viewScholarshipDetails(${scholarship.id})">📋 View Details</button>
            <button class="btn-secondary" onclick="askAboutScholarship('${scholarship.title.replace(/'/g, "\\'")}')">🤖 Ask AI</button>
        </div>
    `;
    
    const bookmarkedScholarships = JSON.parse(localStorage.getItem('bookmarkedScholarships')) || [];
    const bookmarkBtn = card.querySelector('.bookmark-btn');
    if (bookmarkedScholarships.includes(scholarship.id)) {
        if (bookmarkBtn) {
            bookmarkBtn.classList.add('active');
            bookmarkBtn.setAttribute('aria-pressed', 'true');
        }
    }

    card.style.opacity = '0';
    card.style.transform = 'translateY(20px)';
    setTimeout(() => {
        card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        card.style.opacity = '1';
        card.style.transform = 'translateY(0)';
    }, index * 100); 
    
    return card;
}

function calculateAIMatchScore(scholarship) {
    let score = 70; 
    if (scholarship.amount_numeric_max && scholarship.amount_numeric_max > 5000) score += 8;
    if (scholarship.amount_numeric_max && scholarship.amount_numeric_max > 15000) score += 7; 
    if (scholarship.due_date) {
        const daysDiff = (new Date(scholarship.due_date) - new Date()) / (1000 * 60 * 60 * 24);
        if (daysDiff > 90) score += 5; 
        else if (daysDiff > 30) score += 3;
    }
    if (scholarship.gpa_requirement && parseFloat(scholarship.gpa_requirement) <= 3.2) score += 5; 
    if (scholarship.field_of_study && scholarship.field_of_study !== 'All Fields') score += 3;
    score += Math.floor(Math.random() * 10) - 2; 
    return Math.min(99, Math.max(70, Math.floor(score))); 
}

function generateAIInsight(scholarship) {
    const insights = [];
    if (scholarship.field_of_study && scholarship.field_of_study !== 'All Fields') insights.push(`Strong match for ${scholarship.field_of_study.toLowerCase()}`);
    if (scholarship.education_level && scholarship.education_level !== 'All Levels') insights.push(`Suitable for ${scholarship.education_level.toLowerCase()} students`);
    if (scholarship.demographic_requirements && scholarship.demographic_requirements !== 'All Students') insights.push(`Targets ${scholarship.demographic_requirements.toLowerCase()}`);
    
    if (insights.length === 0) insights.push('Good general opportunity based on your profile.');
    
    return insights.slice(0, 1).join(' • '); 
}

// --- End AI Chat Functionality ---


// --- General Search & UI Functions ---
async function loadHomePageStats() {
    try {
        const response = await fetch('/api/stats');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        if (data.success && data.stats) {
            animateCountUp('totalScholarships', data.stats.total_scholarships);
            animateCountUp('totalAmount', data.stats.total_amount);
            animateCountUp('studentsHelped', data.stats.students_helped);
        } else console.error('Failed to load stats:', data.error || 'Unknown error');
    } catch (error) { console.error('Error loading stats:', error); }
}

function animateCountUp(elementId, finalValue) {
    const element = document.getElementById(elementId);
    if (!element) return;
    let targetNumericValue, prefix = '', suffix = '', isCurrency = false;
    if (elementId === 'totalAmount') {
        isCurrency = true; prefix = '$'; targetNumericValue = Number(finalValue);
        if (targetNumericValue >= 1000000) { targetNumericValue /= 1000000; suffix = 'M'; }
        else if (targetNumericValue >= 1000) { targetNumericValue /= 1000; suffix = 'K'; }
    } else targetNumericValue = Number(String(finalValue).replace(/,/g, ''));
    if (isNaN(targetNumericValue) || !isFinite(targetNumericValue)) { element.textContent = prefix + "0" + suffix; return; }
    let current = 0; const duration = 1500, frameRate = 60, totalFrames = Math.round((duration / 1000) * frameRate);
    const increment = targetNumericValue / totalFrames; let frame = 0;
    const timer = setInterval(() => {
        frame++; current += increment;
        if (frame >= totalFrames) { current = targetNumericValue; clearInterval(timer); }
        let displayNum = (isCurrency && suffix && current < 10 && !Number.isInteger(current)) ? current.toFixed(1) : Math.floor(current).toLocaleString();
        element.textContent = prefix + displayNum + suffix;
    }, 1000 / frameRate);
}

function handleQuickSearchSubmit(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const query = formData.get('q');
    if (query && query.trim()) {
        window.location.href = `search.html?q=${encodeURIComponent(query.trim())}`;
    }
}

function handleSearchSubmit(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const params = {};
    for (let [key, value] of formData.entries()) {
        if (String(value).trim()) params[key] = String(value).trim();
    }
    currentFilters = params; currentPage = 1;
    updateURL(); performSearch();
    const filtersPanel = document.getElementById('filtersPanel');
    if (filtersPanel && filtersPanel.classList.contains('active')) toggleFilters();
}

async function performSearch() {
    if (isLoading) return;
    showLoading("Searching scholarships...");
    try {
        const params = { ...currentFilters, sort: currentSort, page: currentPage, per_page: 20 };
        const activeParams = Object.fromEntries(Object.entries(params).filter(([_, v]) => v != null && v !== '' && v !== undefined));
        const queryString = new URLSearchParams(activeParams).toString();
        const response = await fetch(`/api/search?${queryString}`);
        const data = await response.json();
        if (data.success) {
            displaySearchResults(data.scholarships, data.pagination);
            updateActiveFilters(data.filters);
            updateResultsCount(data.pagination.total_results);
        } else {
            showError('Failed to load scholarships: ' + (data.message || data.error));
            displayNoResults(document.getElementById('scholarshipsGrid'));
        }
    } catch (error) {
        console.error('Search error:', error);
        showError('An error occurred while searching.');
        displayNoResults(document.getElementById('scholarshipsGrid'));
    } finally { hideLoading(); }
}

function displaySearchResults(scholarships, pagination) {
    const container = document.getElementById('scholarshipsGrid');
    if (!container) return;
    container.innerHTML = '';
    if (!scholarships || scholarships.length === 0) {
        displayNoResults(container); updatePagination(pagination); return;
    }
    container.className = viewMode === 'list' ? 'scholarships-list' : 'scholarships-grid';
    scholarships.forEach(scholarship => container.appendChild(createScholarshipCard(scholarship))); 
    updatePagination(pagination);
    initializeCardInteractions();
}

function createScholarshipCard(scholarship) { 
    const card = document.createElement('div');
    card.className = 'scholarship-card';
    card.dataset.scholarshipId = scholarship.id;
    const deadline = scholarship.due_date ? formatDate(scholarship.due_date) : 'Varies';
    const keywords = Array.isArray(scholarship.keywords) ? scholarship.keywords : [];
    const keywordTags = keywords.slice(0, 3).map(keyword => `<span class="tag">${keyword}</span>`).join('');
    const metaItems = [
        { icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`, text: `Due: ${deadline}`},
        { icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>`, text: scholarship.education_level || 'All Levels'}
    ];
    if (scholarship.gpa_requirement) metaItems.push({ icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`, text: `GPA: ${scholarship.gpa_requirement}${scholarship.gpa_requirement.toString().includes('+') ? '' : '+'}`});
    const metaHtml = metaItems.map(item => `<div class="meta-item">${item.icon} ${item.text}</div>`).join('');
    const description = scholarship.eligibility_summary_text || scholarship.description_summary || 'No detailed description available.';
    card.innerHTML = `
        <div class="card-header">
            <div class="card-badge">${scholarship.amount_display || 'Amount Varies'}</div>
            <button class="bookmark-btn" onclick="toggleBookmark(event, ${scholarship.id})" aria-label="Bookmark scholarship" aria-pressed="false">
                <svg width="18" height="18" viewBox="0 0 24 24"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
            </button>
        </div>
        <div class="card-content">
            <h3 class="card-title">${scholarship.title || 'Untitled Scholarship'}</h3>
            <div class="card-organization">${scholarship.organization_name || 'Unknown Organization'}</div>
            <div class="card-description">${truncateText(description, 120)}</div>
            ${keywordTags ? `<div class="card-tags">${keywordTags}</div>` : ''}
            <div class="card-meta">${metaHtml}</div>
        </div>
        <div class="card-actions">
            <button class="btn-primary" onclick="viewScholarshipDetails(${scholarship.id})">View Details</button>
            <a href="${scholarship.application_url || scholarship.source_link || '#'}" target="_blank" rel="noopener noreferrer" class="btn-secondary" ${!(scholarship.application_url || scholarship.source_link) ? 'disabled aria-disabled="true"' : ''}>Apply Now</a>
        </div>
    `;
    const bookmarkedScholarships = JSON.parse(localStorage.getItem('bookmarkedScholarships')) || [];
    const bookmarkBtn = card.querySelector('.bookmark-btn');
    if (bookmarkedScholarships.includes(scholarship.id)) {
        if (bookmarkBtn) {
            bookmarkBtn.classList.add('active');
            bookmarkBtn.setAttribute('aria-pressed', 'true');
        }
    }
    return card;
}

function displayNoResults(container) {
    if (!container) return;
    container.innerHTML = `
        <div class="no-results">
            <div class="no-results-content">
                <svg viewBox="0 0 24 24" stroke-width="1" fill="none" stroke="currentColor"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                <h3>No scholarships found</h3>
                <p>Try adjusting your search criteria or removing some filters.</p>
                <button class="btn-primary" onclick="clearAllFilters()">Clear All Filters</button>
            </div>
        </div>
    `;
    container.className = 'scholarships-grid'; 
}

function updatePagination(pagination) {
    const paginationContainer = document.querySelector('.pagination');
    if (!paginationContainer) return;
    if (!pagination || pagination.total_pages <= 1) { paginationContainer.style.display = 'none'; paginationContainer.innerHTML = ''; return; }
    paginationContainer.style.display = 'flex'; paginationContainer.innerHTML = '';
    const prevBtn = document.createElement('button'); prevBtn.className = 'pagination-btn';
    prevBtn.disabled = pagination.current_page === 1;
    prevBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg> Previous`;
    prevBtn.onclick = () => changePage(pagination.current_page - 1); paginationContainer.appendChild(prevBtn);
    const numbersContainer = document.createElement('div'); numbersContainer.className = 'pagination-numbers';
    const maxVisible = 5; let startPage = Math.max(1, pagination.current_page - Math.floor(maxVisible / 2));
    let endPage = Math.min(pagination.total_pages, startPage + maxVisible - 1);
    if (endPage - startPage + 1 < maxVisible && startPage > 1) startPage = Math.max(1, endPage - maxVisible + 1);
    if (startPage > 1) { numbersContainer.appendChild(createPageButton(1, pagination.current_page));
        if (startPage > 2) { const dots = document.createElement('span'); dots.className = 'pagination-dots'; dots.textContent = '...'; numbersContainer.appendChild(dots); }}
    for (let i = startPage; i <= endPage; i++) numbersContainer.appendChild(createPageButton(i, pagination.current_page));
    if (endPage < pagination.total_pages) { if (endPage < pagination.total_pages - 1) { const dots = document.createElement('span'); dots.className = 'pagination-dots'; dots.textContent = '...'; numbersContainer.appendChild(dots); }
        numbersContainer.appendChild(createPageButton(pagination.total_pages, pagination.current_page)); }
    paginationContainer.appendChild(numbersContainer);
    const nextBtn = document.createElement('button'); nextBtn.className = 'pagination-btn';
    nextBtn.disabled = pagination.current_page === pagination.total_pages;
    nextBtn.innerHTML = `Next <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>`;
    nextBtn.onclick = () => changePage(pagination.current_page + 1); paginationContainer.appendChild(nextBtn);
}

function createPageButton(pageNumber, currentPage) {
    const btn = document.createElement('button');
    btn.className = `pagination-btn ${pageNumber === currentPage ? 'active' : ''}`;
    btn.textContent = pageNumber; btn.onclick = () => changePage(pageNumber); return btn;
}

function changePage(page) {
    if (page === currentPage || isLoading) return;
    currentPage = page; updateURL(); performSearch();
    const resultsSection = document.querySelector('.results-section');
    if (resultsSection) resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function toggleFilters() {
    const filtersPanel = document.getElementById('filtersPanel');
    const filtersToggle = document.getElementById('filtersToggle');
    if (filtersPanel && filtersToggle) {
        const isActive = filtersPanel.classList.toggle('active');
        filtersToggle.classList.toggle('active');
        filtersToggle.setAttribute('aria-expanded', isActive.toString());
    }
}

function handleSortChange(event) {
    currentSort = event.target.value; currentPage = 1;
    updateURL(); performSearch();
}

function handleViewToggle(event) {
    const button = event.target.closest('.view-btn');
    if (!button || button.classList.contains('active')) return;
    viewMode = button.dataset.view;
    document.querySelectorAll('.view-btn').forEach(btn => { btn.classList.remove('active'); btn.setAttribute('aria-pressed', 'false'); });
    button.classList.add('active'); button.setAttribute('aria-pressed', 'true');
    const container = document.getElementById('scholarshipsGrid');
    if (container) container.className = viewMode === 'list' ? 'scholarships-list' : 'scholarships-grid';
}

function clearAllFilters() {
    currentFilters = {}; currentPage = 1;
    const form = document.getElementById('searchForm');
    if (form) form.reset();
    updateURL(); performSearch(); updateActiveFilters({});
}

function clearFilterTag(filterKey) {
    delete currentFilters[filterKey]; currentPage = 1;
    const searchForm = document.getElementById('searchForm');
    if (searchForm && searchForm.elements[filterKey]) {
        const element = searchForm.elements[filterKey];
        if (element.type === 'select-one') element.selectedIndex = 0;
        else element.value = '';
    }
    updateURL(); performSearch(); updateActiveFilters(currentFilters); 
}

function updateActiveFilters(backendFilters) {
    const container = document.getElementById('activeFilters');
    if (!container) return;
    container.innerHTML = '';
    const filterLabels = { q: 'Keywords', min_amount: 'Min Amount', deadline: 'Deadline', level: 'Education Level', field: 'Field of Study', gpa: 'GPA', demographics: 'Demographics', amount_range: 'Amount Range' };
    const filtersToDisplay = backendFilters || currentFilters;
    Object.entries(filtersToDisplay).forEach(([key, value]) => {
        if (value && key !== 'sort' && key !== 'page' && key !== 'per_page' && key !== 'undefined') {
            const label = filterLabels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            let displayValue = value;
            if (key === 'level' || key === 'field' || key === 'demographics' || key === 'amount_range') {
                const selectElement = document.querySelector(`#searchForm select[name="${key}"]`);
                if (selectElement) { const selectedOption = Array.from(selectElement.options).find(opt => opt.value === value); if (selectedOption) displayValue = selectedOption.textContent; }
            } else if (key === 'min_amount') displayValue = `$${parseFloat(value).toLocaleString()}`;
            else if (key === 'gpa') displayValue = `${value}+`;
            const tag = document.createElement('div'); tag.className = 'filter-tag';
            tag.innerHTML = `${label}: ${displayValue} <button onclick="clearFilterTag('${key}')" aria-label="Remove filter ${label}">×</button>`;
            container.appendChild(tag);
        }
    });
}

function updateResultsCount(totalResults) {
    const countElement = document.querySelector('.results-count');
    if (countElement) {
        const plural = totalResults === 1 ? '' : 's';
        countElement.textContent = `${totalResults.toLocaleString()} scholarship${plural} found`;
    }
}

function populateSearchForm(filters) {
    const form = document.getElementById('searchForm');
    if (!form) return;
    Object.entries(filters).forEach(([key, value]) => {
        const input = form.elements[key];
        if (input) {
            if (input.type === 'radio' || input.type === 'checkbox') {
                if (input.length && typeof input.forEach === 'function') input.forEach(i => { if (i.value === value) i.checked = true; });
                else if (input.value === value) input.checked = true;
            } else input.value = value;
        }
    });
}

function updateURL() {
    const params = new URLSearchParams();
    for (const key in currentFilters) {
        if (currentFilters[key] !== '' && currentFilters[key] !== null && currentFilters[key] !== undefined) params.set(key, currentFilters[key]);
    }
    if (currentSort && currentSort !== 'relevance') params.set('sort', currentSort);
    if (currentPage > 1) params.set('page', currentPage);
    const newUrl = `${window.location.pathname}?${params.toString()}`;
    window.history.pushState({ path: newUrl }, '', newUrl);
}

async function viewScholarshipDetails(scholarshipId) {
    showLoading("Loading details...");
    try {
        const response = await fetch(`/api/scholarship/${scholarshipId}`);
        const data = await response.json();
        if (data.success && data.scholarship) showScholarshipModal(data.scholarship);
        else showError('Failed to load scholarship details: ' + (data.message || data.error));
    } catch (error) { console.error('Error loading scholarship details:', error); showError('An error occurred while loading details.');
    } finally { hideLoading(); }
}

function showScholarshipModal(scholarship) {
    let modal = document.getElementById('scholarshipModal');
    if (!modal) { console.error("Scholarship modal structure not found!"); return; }
    populateScholarshipModal(modal, scholarship);
    modal.style.display = 'flex';
    requestAnimationFrame(() => modal.classList.add('show'));
    document.body.style.overflow = 'hidden';
    const firstFocusable = modal.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (firstFocusable) firstFocusable.focus();
}

function populateScholarshipModal(modal, scholarship) {
    const titleEl = modal.querySelector('#modalTitle');
    const bodyEl = modal.querySelector('#modalBody');
    const applyBtnEl = modal.querySelector('#modalApplyBtn');
    if (titleEl) titleEl.textContent = scholarship.title || 'Scholarship Details';
    if (applyBtnEl) {
        const applyUrl = scholarship.application_url || scholarship.source_link || '#';
        applyBtnEl.href = applyUrl;
        if (applyUrl === '#') { applyBtnEl.classList.add('disabled'); applyBtnEl.setAttribute('aria-disabled', 'true'); applyBtnEl.onclick = (e) => e.preventDefault(); }
        else { applyBtnEl.classList.remove('disabled'); applyBtnEl.removeAttribute('aria-disabled'); applyBtnEl.onclick = null; }
    }
    const requirements = scholarship.requirements_structured || {};
    let reqListHtml = Object.keys(requirements).length > 0 ? Object.entries(requirements).map(([key, value]) => {
        if (!value) return ''; const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        return `<div class="requirement-item"><strong>${label}:</strong> ${value}</div>`; }).join('') : '';
    const keywords = Array.isArray(scholarship.keywords) ? scholarship.keywords : [];
    const keywordTags = keywords.map(keyword => `<span class="tag">${keyword}</span>`).join('');
    const description = scholarship.eligibility_summary_text || scholarship.description_summary || 'No detailed description available.';
    if (bodyEl) bodyEl.innerHTML = `
        <div class="scholarship-details">
            ${scholarship.organization_name ? `<div class="detail-section"><h3>Organization</h3><p>${scholarship.organization_name}</p></div>` : ''}
            ${scholarship.amount_display ? `<div class="detail-section"><h3>Award Amount</h3><p>${scholarship.amount_display}</p></div>` : ''}
            ${scholarship.due_date ? `<div class="detail-section"><h3>Deadline</h3><p>${formatDate(scholarship.due_date)}</p></div>` : ''}
            <div class="detail-section"><h3>Description</h3><p>${description.replace(/\n/g, '<br>')}</p></div>
            ${reqListHtml ? `<div class="detail-section"><h3>Specific Requirements</h3><div class="requirements-list">${reqListHtml}</div></div>` : ''}
            ${scholarship.field_of_study && scholarship.field_of_study !== 'All Fields' ? `<div class="detail-section"><h3>Field of Study</h3><p>${scholarship.field_of_study}</p></div>` : ''}
            ${scholarship.education_level && scholarship.education_level !== 'All Levels' ? `<div class="detail-section"><h3>Education Level</h3><p>${scholarship.education_level}</p></div>` : ''}
            ${scholarship.gpa_requirement ? `<div class="detail-section"><h3>GPA Requirement</h3><p>${scholarship.gpa_requirement}${scholarship.gpa_requirement.toString().includes('+') ? '' : '+'}</p></div>` : ''}
            ${scholarship.demographic_requirements && scholarship.demographic_requirements !== 'All Students' ? `<div class="detail-section"><h3>Demographics</h3><p>${scholarship.demographic_requirements}</p></div>` : ''}
            ${keywordTags ? `<div class="detail-section"><h3>Keywords</h3><div class="card-tags">${keywordTags}</div></div>` : ''}
            ${scholarship.source_website ? `<div class="detail-section"><h3>Source</h3><p><a href="${scholarship.source_link || '#'}" target="_blank" rel="noopener noreferrer">${scholarship.source_website}</a></p></div>` : ''}
        </div>`;
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        modal.addEventListener('transitionend', () => { if (!modal.classList.contains('show')) modal.style.display = 'none'; }, { once: true });
        document.body.style.overflow = '';
    }
}

function toggleBookmark(event, scholarshipId) {
    event.stopPropagation();
    const btn = event.currentTarget;
    if (!btn) return;
    const isActive = btn.classList.toggle('active');
    btn.setAttribute('aria-pressed', isActive.toString());
        
    showNotification(isActive ? 'Scholarship bookmarked!' : 'Bookmark removed.', 'success');
    let bookmarked = JSON.parse(localStorage.getItem('bookmarkedScholarships')) || [];
    if (isActive) { if (!bookmarked.includes(scholarshipId)) bookmarked.push(scholarshipId); }
    else bookmarked = bookmarked.filter(id => id !== scholarshipId);
    localStorage.setItem('bookmarkedScholarships', JSON.stringify(bookmarked));

    // If on bookmarks page and item is unbookmarked, remove it from view
    if (window.location.pathname.includes('bookmarks.html') && !isActive) {
        const cardToRemove = btn.closest('.scholarship-card');
        if (cardToRemove) {
            cardToRemove.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            cardToRemove.style.opacity = '0';
            cardToRemove.style.transform = 'scale(0.95)';
            setTimeout(() => {
                cardToRemove.remove();
                // Check if no bookmarks are left
                const remainingCards = document.querySelectorAll('#bookmarkedScholarshipsContainer .scholarship-card');
                if (remainingCards.length === 0) {
                    const noBookmarksMessage = document.getElementById('noBookmarksMessage');
                    if (noBookmarksMessage) noBookmarksMessage.style.display = 'flex';
                }
            }, 300);
        }
    }
}

function initializeCardInteractions() {
    const cards = document.querySelectorAll('.scholarship-card:not(.enhanced-ai-card)'); 
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries, obs) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.animationDelay = `${Math.random() * 0.2}s`; 
                    entry.target.classList.add('animate-fade-in');
                    obs.unobserve(entry.target);
                }
            });
        }, { threshold: 0.05, rootMargin: '0px 0px -50px 0px' });
        cards.forEach(card => observer.observe(card));
    } else cards.forEach(card => card.classList.add('animate-fade-in'));
}

function initializeTheme() {
    const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    applyTheme(savedTheme);
}
function toggleTheme() {
    const currentTheme = document.body.classList.contains('dark-mode') ? 'dark' : 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    applyTheme(newTheme); localStorage.setItem('theme', newTheme);
}
function applyTheme(theme) {
    const body = document.body;
    const themeIcon = document.querySelector('#themeToggle .theme-icon');
    if (theme === 'dark') { body.classList.add('dark-mode'); if (themeIcon) themeIcon.textContent = '☀️'; }
    else { body.classList.remove('dark-mode'); if (themeIcon) themeIcon.textContent = '🌙'; }
}

function toggleMobileNav(navLinksElement, toggleButtonElement) {
    if (navLinksElement && toggleButtonElement) {
        navLinksElement.classList.toggle('active');
        toggleButtonElement.classList.toggle('active');
        const isExpanded = navLinksElement.classList.contains('active');
        toggleButtonElement.setAttribute('aria-expanded', isExpanded.toString());
    }
}

function initializeScrollAnimations() {
    const animatedElements = document.querySelectorAll('.animate-on-scroll');
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries, obs) => {
            entries.forEach(entry => { if (entry.isIntersecting) { entry.target.classList.add('animated'); obs.unobserve(entry.target); }});
        }, { threshold: 0.15, rootMargin: '0px 0px -50px 0px' });
        animatedElements.forEach(el => observer.observe(el));
    } else animatedElements.forEach(el => el.classList.add('animated'));
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        let date;
        if (dateString.length === 10 && dateString.includes('-')) date = new Date(dateString + 'T00:00:00Z'); 
        else date = new Date(dateString); 
        if (isNaN(date.getTime())) return dateString; 
        return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC' });
    } catch (error) { return dateString; } 
}

function truncateText(text, maxLength) {
    if (!text || typeof text !== 'string') return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength).trim() + '...';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text; return div.innerHTML;
}

function scrollToBottom(element) { if (element) element.scrollTop = element.scrollHeight; }

function showLoading(message = "Loading...") {
    isLoading = true;
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        const p = loadingOverlay.querySelector('p'); if (p) p.textContent = message;
        loadingOverlay.classList.add('show');
    }
    const container = document.getElementById('scholarshipsGrid'); 
    if (container && !container.querySelector('.scholarship-card') && !container.querySelector('.no-results') && message.toLowerCase().includes("scholarships")) {
        container.innerHTML = `<div class="loading-placeholder"><div class="loading-spinner"><div class="spinner"></div><p>Searching scholarships...</p></div></div>`;
        container.className = 'scholarships-grid';
    }
}

function hideLoading() {
    isLoading = false;
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.classList.remove('show');
        const p = loadingOverlay.querySelector('p'); if (p) p.textContent = "Loading..."; 
    }
}

function showNotification(message, type = 'info', duration = 3000) {
    let container = document.querySelector('.notification-container');
    if (!container) { container = document.createElement('div'); container.className = 'notification-container'; document.body.appendChild(container); }
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`; notification.setAttribute('role', 'alert');
    notification.innerHTML = `<span>${message}</span><button class="notification-close-btn" onclick="this.parentElement.remove()" aria-label="Close notification">×</button>`;
    container.appendChild(notification);
    requestAnimationFrame(() => notification.classList.add('show'));
    setTimeout(() => { notification.classList.remove('show'); notification.addEventListener('transitionend', () => notification.remove(), { once: true }); }, duration);
}
function showError(message) { showNotification(message, 'error', 5000); }
function showSuccess(message) { showNotification(message, 'success'); }

function handleOutsideClick(event) {
    const openModal = document.querySelector('.modal-overlay.show');
    if (openModal && event.target === openModal) closeModal(openModal.id);
    
    const filtersPanel = document.getElementById('filtersPanel');
    const filtersToggle = document.getElementById('filtersToggle');
    if (filtersPanel && filtersPanel.classList.contains('active') && !filtersPanel.contains(event.target) && filtersToggle && !filtersToggle.contains(event.target)) toggleFilters();
    
    const activeNavMenuToggle = document.querySelector('#mobileMenuToggle.active'); 
    const mainNavLinks = document.getElementById('mainNavLinks');
    if (mainNavLinks && mainNavLinks.classList.contains('active') && !mainNavLinks.contains(event.target) && activeNavMenuToggle && !activeNavMenuToggle.contains(event.target)) {
        toggleMobileNav(mainNavLinks, activeNavMenuToggle);
    }
}

function handleEscapeKey(event) {
    if (event.key === 'Escape') {
        const openModal = document.querySelector('.modal-overlay.show');
        if (openModal) { closeModal(openModal.id); return; }
        
        const filtersPanel = document.getElementById('filtersPanel');
        if (filtersPanel && filtersPanel.classList.contains('active')) { toggleFilters(); return; }
        
        const activeNavMenuToggle = document.querySelector('#mobileMenuToggle.active'); 
        const mainNavLinks = document.getElementById('mainNavLinks'); 
        if (mainNavLinks && mainNavLinks.classList.contains('active') && activeNavMenuToggle) {
            toggleMobileNav(mainNavLinks, activeNavMenuToggle);
        }
    }
}

// Make functions globally available for HTML onclick attributes
window.scrollToSearch = () => { 
    const searchFormContainer = document.querySelector('.search-form') || document.querySelector('.advanced-search-form');
    if(searchFormContainer) searchFormContainer.scrollIntoView({behavior: 'smooth'});
    else window.location.href = 'search.html';
};
window.clearAllFilters = clearAllFilters;
window.clearFilterTag = clearFilterTag;
window.viewScholarshipDetails = viewScholarshipDetails;
window.toggleBookmark = toggleBookmark;
window.closeModal = closeModal;

// AI Chat related functions made global
window.askAboutScholarship = (scholarshipTitle) => {
    const message = `Tell me more about the "${scholarshipTitle}" scholarship. What are the key requirements, application process, and any tips?`;
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.value = message;
        sendChatMessage(); 
        const chatMessagesEl = document.getElementById('chatMessages');
        if (chatMessagesEl) setTimeout(() => chatMessagesEl.scrollIntoView({ behavior: 'smooth', block: 'end' }), 100);
    }
};
window.askForMoreRecommendations = () => {
    const message = "Find more scholarships similar to these recommendations.";
    const chatInput = document.getElementById('chatInput');
    if (chatInput) { chatInput.value = message; sendChatMessage(); }
};
window.askForApplicationTips = () => {
    const message = "Can you give me some general tips for successful scholarship applications and writing essays?";
    const chatInput = document.getElementById('chatInput');
    if (chatInput) { chatInput.value = message; sendChatMessage(); }
};
window.askForHighValueScholarships = () => {
    const message = "Show me high-value scholarships, for example, those over $10,000.";
    const chatInput = document.getElementById('chatInput');
    if (chatInput) { chatInput.value = message; sendChatMessage(); }
};
window.sendSuggestion = (message) => { 
    clearWelcomeState(); 
    const chatInput = document.getElementById('chatInput');
    if (chatInput) { chatInput.value = message; sendChatMessage(); }
};
window.clearChat = () => { 
    const messagesContainer = document.getElementById('chatMessages');
    if(messagesContainer) {
         messagesContainer.innerHTML = `
            <div class="welcome-state">
                <div class="welcome-icon">🎓</div>
                <h3>Welcome to SchoolSmart.ai!</h3>
                <p>I'm here to help you find scholarships that match your profile. Tell me about yourself to get started!</p>
                <div class="welcome-suggestions">
                    <button class="welcome-suggestion" onclick="sendSuggestion('I study computer science with a 3.2 GPA')">Computer Science Student</button>
                    <button class="welcome-suggestion" onclick="sendSuggestion('I need scholarships for engineering majors')">Engineering Major</button>
                    <button class="welcome-suggestion" onclick="sendSuggestion('International student looking for aid')">International Student</button>
                    <button class="welcome-suggestion" onclick="sendSuggestion('First-generation college student')">First-Gen Student</button>
                </div>
            </div>
        `;
    }
    conversationHistory = []; 
    const recommendationsContainer = document.getElementById('aiScholarshipRecommendations');
    if (recommendationsContainer) {
        recommendationsContainer.innerHTML = ''; 
        recommendationsContainer.classList.remove('show'); 
    }
    const chatInput = document.getElementById('chatInput');
    if (chatInput) chatInput.focus();
};

// Listen for browser back/forward navigation
window.addEventListener('popstate', (event) => {
    initializeApp(); 
});
// --- END OF FILE static/js/script.js ---