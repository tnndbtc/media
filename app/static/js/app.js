/**
 * Multilingual Media Search - Frontend Application
 */

// DOM Elements
const searchForm = document.getElementById('search-form');
const searchInput = document.getElementById('search-input');
const searchButton = document.getElementById('search-button');
const queryInfo = document.getElementById('query-info');
const errorSection = document.getElementById('error-section');
const errorText = document.getElementById('error-text');
const resultsSection = document.getElementById('results-section');
const resultsGrid = document.getElementById('results-grid');
const loadingSection = document.getElementById('loading-section');
const modal = document.getElementById('media-modal');

// State
let isSearching = false;

/**
 * Initialize the application
 */
function init() {
    searchForm.addEventListener('submit', handleSearch);

    // Modal event listeners
    modal.querySelector('.modal-overlay').addEventListener('click', closeModal);
    modal.querySelector('.modal-close').addEventListener('click', closeModal);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });

    // Focus search input on load
    searchInput.focus();
}

/**
 * Handle search form submission
 */
async function handleSearch(e) {
    e.preventDefault();

    if (isSearching) return;

    const query = searchInput.value.trim();
    if (!query) return;

    // Get selected media types
    const mediaTypeCheckboxes = document.querySelectorAll('input[name="media_type"]:checked');
    const mediaTypes = Array.from(mediaTypeCheckboxes).map(cb => cb.value);

    if (mediaTypes.length === 0) {
        showError('Please select at least one media type (Images or Videos)');
        return;
    }

    const limit = parseInt(document.getElementById('limit').value, 10);

    // Build request body
    const requestBody = {
        text: query,
        media_type: mediaTypes,
        limit: limit
    };

    await performSearch(requestBody);
}

/**
 * Perform the search API call
 */
async function performSearch(requestBody) {
    setLoading(true);
    hideError();
    hideResults();
    hideQueryInfo();

    try {
        const response = await fetch('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Search failed with status ${response.status}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error('Search was not successful');
        }

        displayQueryInfo(data);
        displayResults(data.results);

    } catch (error) {
        console.error('Search error:', error);
        showError(error.message || 'An error occurred while searching. Please try again.');
    } finally {
        setLoading(false);
    }
}

/**
 * Display query analysis information
 */
function displayQueryInfo(data) {
    const query = data.query;

    // Language badge
    document.getElementById('detected-language').textContent =
        `${query.detected_language} (${query.language_code})`;

    // English translation (show only if original was not English)
    const translationRow = document.getElementById('translation-row');
    if (query.language_code !== 'en' && query.english_query) {
        document.getElementById('english-query').textContent = query.english_query;
        translationRow.hidden = false;
    } else {
        translationRow.hidden = true;
    }

    // Keywords
    const keywordsContainer = document.getElementById('keywords');
    keywordsContainer.innerHTML = '';
    if (query.keywords && query.keywords.length > 0) {
        query.keywords.forEach(keyword => {
            const tag = document.createElement('span');
            tag.className = 'keyword-tag';
            tag.textContent = keyword;
            keywordsContainer.appendChild(tag);
        });
    } else {
        keywordsContainer.textContent = 'N/A';
    }

    // Processing time
    document.getElementById('processing-time').textContent =
        `${data.processing_time_ms.toFixed(0)}ms`;

    // Result count
    document.getElementById('result-count').textContent =
        `${data.total_returned} of ${data.total_found} found`;

    // APIs invoked
    const apisContainer = document.getElementById('apis-invoked');
    apisContainer.innerHTML = '';
    if (data.apis_invoked && data.apis_invoked.length > 0) {
        data.apis_invoked.forEach(api => {
            const tag = document.createElement('span');
            tag.className = 'api-tag' + (api.cached ? ' cached' : '');
            tag.textContent = `${api.service}: ${api.method}`;
            apisContainer.appendChild(tag);
        });
    } else {
        apisContainer.textContent = 'N/A';
    }

    queryInfo.hidden = false;
}

/**
 * Display search results
 */
function displayResults(results) {
    resultsGrid.innerHTML = '';

    if (!results || results.length === 0) {
        resultsGrid.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--color-text-muted);">
                <p>No results found. Try a different search query.</p>
            </div>
        `;
        resultsSection.hidden = false;
        return;
    }

    results.forEach(item => {
        const card = createMediaCard(item);
        resultsGrid.appendChild(card);
    });

    resultsSection.hidden = false;
}

/**
 * Create a media card element
 */
function createMediaCard(item) {
    const card = document.createElement('div');
    card.className = 'media-card';
    card.addEventListener('click', () => openModal(item));

    const thumbnailUrl = item.urls.medium || item.urls.small || item.urls.thumbnail || item.urls.original;
    const isVideo = item.media_type === 'video';
    const sourceClass = item.source.toLowerCase();
    const title = item.title || 'Untitled';
    const photographer = item.photographer || 'Unknown';
    const score = Math.round(item.final_score * 100);

    card.innerHTML = `
        <div class="media-thumbnail">
            ${isVideo ? `
                <video src="${thumbnailUrl}" muted preload="metadata"></video>
                <div class="video-overlay"></div>
            ` : `
                <img src="${thumbnailUrl}" alt="${escapeHtml(title)}" loading="lazy">
            `}
            <span class="media-type-badge">${item.media_type}</span>
            <span class="source-badge ${sourceClass}">${capitalizeFirst(item.source)}</span>
        </div>
        <div class="media-info">
            <div class="media-title" title="${escapeHtml(title)}">${escapeHtml(title)}</div>
            <div class="media-meta">
                <span class="media-photographer" title="${escapeHtml(photographer)}">by ${escapeHtml(photographer)}</span>
                <span class="media-score">
                    <span class="score-bar">
                        <span class="score-fill" style="width: ${score}%"></span>
                    </span>
                    ${score}%
                </span>
            </div>
        </div>
    `;

    // Add hover preview for videos
    if (isVideo) {
        const video = card.querySelector('video');
        card.addEventListener('mouseenter', () => {
            video.play().catch(() => {});
        });
        card.addEventListener('mouseleave', () => {
            video.pause();
            video.currentTime = 0;
        });
    }

    return card;
}

/**
 * Open modal with media details
 */
function openModal(item) {
    const modalMedia = document.getElementById('modal-media');
    const isVideo = item.media_type === 'video';
    const fullUrl = item.urls.large || item.urls.original;

    if (isVideo) {
        modalMedia.innerHTML = `
            <video src="${fullUrl}" controls autoplay style="max-width: 100%; max-height: 70vh;">
                Your browser does not support video playback.
            </video>
        `;
    } else {
        modalMedia.innerHTML = `
            <img src="${fullUrl}" alt="${escapeHtml(item.title || 'Image')}" style="max-width: 100%; max-height: 70vh;">
        `;
    }

    document.getElementById('modal-title').textContent = item.title || 'Untitled';
    document.getElementById('modal-description').textContent = item.description || '';
    document.getElementById('modal-photographer').textContent = item.photographer ? `By ${item.photographer}` : '';

    const sourceLink = document.getElementById('modal-source-link');
    sourceLink.href = item.source_url;
    sourceLink.textContent = `View on ${capitalizeFirst(item.source)}`;

    modal.hidden = false;
    document.body.style.overflow = 'hidden';
}

/**
 * Close the modal
 */
function closeModal() {
    modal.hidden = true;
    document.body.style.overflow = '';

    // Stop video playback
    const video = modal.querySelector('video');
    if (video) {
        video.pause();
    }
}

/**
 * Set loading state
 */
function setLoading(loading) {
    isSearching = loading;
    searchButton.disabled = loading;
    searchButton.querySelector('.button-text').hidden = loading;
    searchButton.querySelector('.button-loading').hidden = !loading;
    loadingSection.hidden = !loading;
}

/**
 * Show error message
 */
function showError(message) {
    errorText.textContent = message;
    errorSection.hidden = false;
}

/**
 * Hide error message
 */
function hideError() {
    errorSection.hidden = true;
}

/**
 * Hide results section
 */
function hideResults() {
    resultsSection.hidden = true;
}

/**
 * Hide query info section
 */
function hideQueryInfo() {
    queryInfo.hidden = true;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Capitalize first letter
 */
function capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', init);
