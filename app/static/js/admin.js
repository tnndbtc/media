// Admin Dashboard JavaScript

const API_BASE = '/admin/api';

// State
let currentPage = 1;
let pageSize = 20;
let deleteTargetId = null;

// DOM Elements
const promptsBody = document.getElementById('prompts-body');
const pagination = document.getElementById('pagination');
const modal = document.getElementById('modal');
const viewModal = document.getElementById('view-modal');
const deleteModal = document.getElementById('delete-modal');
const promptForm = document.getElementById('prompt-form');
const toast = document.getElementById('toast');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadPrompts();
    setupEventListeners();
});

function setupEventListeners() {
    // Filter buttons
    document.getElementById('btn-filter').addEventListener('click', () => {
        currentPage = 1;
        loadPrompts();
    });

    document.getElementById('btn-clear-filter').addEventListener('click', () => {
        document.getElementById('filter-name').value = '';
        document.getElementById('filter-level').value = '';
        document.getElementById('filter-active').value = '';
        currentPage = 1;
        loadPrompts();
    });

    // Create button
    document.getElementById('btn-create').addEventListener('click', () => {
        openCreateModal();
    });

    // Seed button
    document.getElementById('btn-seed').addEventListener('click', seedPrompts);

    // Form submit
    promptForm.addEventListener('submit', handleFormSubmit);

    // Delete confirm button
    document.getElementById('btn-confirm-delete').addEventListener('click', confirmDelete);

    // Close modals on backdrop click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    viewModal.addEventListener('click', (e) => {
        if (e.target === viewModal) closeViewModal();
    });

    deleteModal.addEventListener('click', (e) => {
        if (e.target === deleteModal) closeDeleteModal();
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
            closeViewModal();
            closeDeleteModal();
        }
    });
}

// API Functions
async function loadPrompts() {
    let name = document.getElementById('filter-name').value;
    const roleFilter = document.getElementById('filter-level').value;
    const isActive = document.getElementById('filter-active').value;

    const params = new URLSearchParams({
        page: currentPage,
        page_size: pageSize,
    });

    // Filter by OpenAI role using name pattern
    if (roleFilter === 'system') {
        // Append SYSTEM to name filter to find system role prompts
        name = name ? name + ' SYSTEM' : 'SYSTEM';
    } else if (roleFilter === 'user') {
        // For user role, we'll filter client-side after fetching
        name = name ? name + ' USER_TEMPLATE' : 'USER_TEMPLATE';
    }

    if (name) params.append('name', name);
    if (isActive) params.append('is_active', isActive);

    try {
        promptsBody.innerHTML = '<tr><td colspan="8" class="loading">Loading...</td></tr>';

        const response = await fetch(`${API_BASE}/prompts?${params}`);
        if (!response.ok) throw new Error('Failed to load prompts');

        const data = await response.json();
        renderPrompts(data.items);
        renderPagination(data.total, data.page, data.total_pages);
    } catch (error) {
        console.error('Error loading prompts:', error);
        promptsBody.innerHTML = '<tr><td colspan="8" class="empty-state"><h3>Error loading prompts</h3><p>Please try again later.</p></td></tr>';
        showToast('Failed to load prompts', true);
    }
}

async function createPrompt(data) {
    const response = await fetch(`${API_BASE}/prompts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create prompt');
    }

    return response.json();
}

async function updatePrompt(id, data) {
    const response = await fetch(`${API_BASE}/prompts/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update prompt');
    }

    return response.json();
}

async function deletePrompt(id) {
    const response = await fetch(`${API_BASE}/prompts/${id}`, {
        method: 'DELETE',
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to delete prompt');
    }
}

async function togglePrompt(id) {
    const response = await fetch(`${API_BASE}/prompts/${id}/toggle`, {
        method: 'POST',
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to toggle prompt');
    }

    return response.json();
}

async function seedPrompts() {
    try {
        const response = await fetch(`${API_BASE}/prompts/seed`, {
            method: 'POST',
        });

        if (!response.ok) throw new Error('Failed to seed prompts');

        const data = await response.json();
        showToast(data.message);
        loadPrompts();
    } catch (error) {
        console.error('Error seeding prompts:', error);
        showToast('Failed to seed prompts', true);
    }
}

// Render Functions
function renderPrompts(prompts) {
    if (prompts.length === 0) {
        promptsBody.innerHTML = `
            <tr>
                <td colspan="8" class="empty-state">
                    <h3>No prompts found</h3>
                    <p>Create a new prompt or adjust your filters.</p>
                </td>
            </tr>
        `;
        return;
    }

    promptsBody.innerHTML = prompts.map(prompt => {
        const openaiRole = getOpenAIRole(prompt.name);
        return `
        <tr>
            <td>${prompt.id}</td>
            <td>
                <a href="#" onclick="viewPrompt(${prompt.id}); return false;" class="prompt-link">
                    ${escapeHtml(prompt.name)}
                </a>
            </td>
            <td><span class="badge badge-${openaiRole}">${openaiRole}</span></td>
            <td class="truncate">${escapeHtml(prompt.description || '-')}</td>
            <td>v${prompt.version}</td>
            <td>
                <span class="badge badge-${prompt.is_active ? 'active' : 'inactive'}">
                    ${prompt.is_active ? 'Active' : 'Inactive'}
                </span>
            </td>
            <td>${formatDate(prompt.updated_at)}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-sm btn-ghost" onclick="viewPrompt(${prompt.id})" title="View">
                        View
                    </button>
                    <button class="btn btn-sm btn-secondary" onclick="editPrompt(${prompt.id})" title="Edit">
                        Edit
                    </button>
                    <button class="btn btn-sm btn-ghost" onclick="togglePromptActive(${prompt.id})" title="Toggle">
                        ${prompt.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button class="btn btn-sm btn-ghost" onclick="openDeleteModal(${prompt.id})" title="Delete" style="color: var(--danger);">
                        Delete
                    </button>
                </div>
            </td>
        </tr>
    `}).join('');
}

function renderPagination(total, page, totalPages) {
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let html = '';

    // Previous button
    html += `<button class="btn btn-sm btn-ghost" ${page === 1 ? 'disabled' : ''} onclick="goToPage(${page - 1})">Prev</button>`;

    // Page numbers
    const startPage = Math.max(1, page - 2);
    const endPage = Math.min(totalPages, page + 2);

    if (startPage > 1) {
        html += `<button class="btn btn-sm btn-ghost" onclick="goToPage(1)">1</button>`;
        if (startPage > 2) html += `<span class="pagination-dots">...</span>`;
    }

    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="btn btn-sm ${i === page ? 'btn-primary active' : 'btn-ghost'}" onclick="goToPage(${i})">${i}</button>`;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) html += `<span class="pagination-dots">...</span>`;
        html += `<button class="btn btn-sm btn-ghost" onclick="goToPage(${totalPages})">${totalPages}</button>`;
    }

    // Next button
    html += `<button class="btn btn-sm btn-ghost" ${page === totalPages ? 'disabled' : ''} onclick="goToPage(${page + 1})">Next</button>`;

    pagination.innerHTML = html;
}

// Modal Functions
function openCreateModal() {
    document.getElementById('modal-title').textContent = 'Create Prompt';
    document.getElementById('prompt-id').value = '';
    document.getElementById('prompt-name').value = '';
    document.getElementById('prompt-level').value = 'developer';
    document.getElementById('prompt-description').value = '';
    document.getElementById('prompt-content').value = '';
    document.getElementById('prompt-active').checked = true;
    modal.classList.remove('hidden');
}

async function editPrompt(id) {
    try {
        const response = await fetch(`${API_BASE}/prompts/${id}`);
        if (!response.ok) throw new Error('Failed to load prompt');

        const prompt = await response.json();

        document.getElementById('modal-title').textContent = 'Edit Prompt';
        document.getElementById('prompt-id').value = prompt.id;
        document.getElementById('prompt-name').value = prompt.name;
        document.getElementById('prompt-level').value = prompt.level;
        document.getElementById('prompt-description').value = prompt.description || '';
        document.getElementById('prompt-content').value = prompt.content;
        document.getElementById('prompt-active').checked = prompt.is_active;

        modal.classList.remove('hidden');
    } catch (error) {
        console.error('Error loading prompt:', error);
        showToast('Failed to load prompt', true);
    }
}

async function viewPrompt(id) {
    try {
        const response = await fetch(`${API_BASE}/prompts/${id}`);
        if (!response.ok) throw new Error('Failed to load prompt');

        const prompt = await response.json();

        const openaiRole = getOpenAIRole(prompt.name);
        document.getElementById('view-modal-title').textContent = prompt.name;
        document.getElementById('view-role').textContent = openaiRole;
        document.getElementById('view-version').textContent = `v${prompt.version}`;

        const statusEl = document.getElementById('view-status');
        statusEl.textContent = prompt.is_active ? 'Active' : 'Inactive';
        statusEl.className = `view-status ${prompt.is_active ? 'active' : 'inactive'}`;

        document.getElementById('view-description').textContent = prompt.description || 'No description';
        document.getElementById('view-content').textContent = prompt.content;
        document.getElementById('view-created').textContent = formatDate(prompt.created_at, true);
        document.getElementById('view-updated').textContent = formatDate(prompt.updated_at, true);

        viewModal.classList.remove('hidden');
    } catch (error) {
        console.error('Error loading prompt:', error);
        showToast('Failed to load prompt', true);
    }
}

function closeModal() {
    modal.classList.add('hidden');
}

function closeViewModal() {
    viewModal.classList.add('hidden');
}

function openDeleteModal(id) {
    deleteTargetId = id;
    deleteModal.classList.remove('hidden');
}

function closeDeleteModal() {
    deleteTargetId = null;
    deleteModal.classList.add('hidden');
}

// Form Handler
async function handleFormSubmit(e) {
    e.preventDefault();

    const id = document.getElementById('prompt-id').value;
    const data = {
        name: document.getElementById('prompt-name').value,
        level: document.getElementById('prompt-level').value,
        description: document.getElementById('prompt-description').value || null,
        content: document.getElementById('prompt-content').value,
        is_active: document.getElementById('prompt-active').checked,
    };

    try {
        if (id) {
            await updatePrompt(id, data);
            showToast('Prompt updated successfully');
        } else {
            await createPrompt(data);
            showToast('Prompt created successfully');
        }

        closeModal();
        loadPrompts();
    } catch (error) {
        console.error('Error saving prompt:', error);
        showToast(error.message, true);
    }
}

// Actions
async function togglePromptActive(id) {
    try {
        await togglePrompt(id);
        showToast('Prompt status updated');
        loadPrompts();
    } catch (error) {
        console.error('Error toggling prompt:', error);
        showToast(error.message, true);
    }
}

async function confirmDelete() {
    if (!deleteTargetId) return;

    try {
        await deletePrompt(deleteTargetId);
        showToast('Prompt deleted successfully');
        closeDeleteModal();
        loadPrompts();
    } catch (error) {
        console.error('Error deleting prompt:', error);
        showToast(error.message, true);
    }
}

function goToPage(page) {
    currentPage = page;
    loadPrompts();
}

// Utility Functions
function getOpenAIRole(promptName) {
    // Determine OpenAI role based on prompt name
    // Names containing "SYSTEM" are sent as system role, others as user role
    return promptName.includes('SYSTEM') ? 'system' : 'user';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr, full = false) {
    const date = new Date(dateStr);
    if (full) {
        return date.toLocaleString();
    }
    return date.toLocaleDateString();
}

function showToast(message, isError = false) {
    toast.textContent = message;
    toast.className = `toast ${isError ? 'error' : ''}`;
    toast.classList.remove('hidden');

    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}
