// Helper to retrieve CSRF token
function getCsrfToken() {
    const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!token) {
        console.error('CSRF token not found.');
    }
    return token;
}

// Generic fetch wrapper with error handling
async function fetchWithCSRF(url, method, body = {}) {
    try {
        const response = await fetch(url, {
            method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify(body),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Request failed');
        }

        return data;
    } catch (error) {
        console.error('Fetch error:', error.message);
        alert(`An error occurred: ${error.message}`);
        throw error;
    }
}

// Handle actions with confirmation and status updates
async function handleAction(url, hash, newState) {
    if (!confirmAction('Are you sure you want to perform this action?')) return;

    try {
        const data = await fetchWithCSRF(url, 'POST');
        if (data.message) {
            alert(data.message);

            if (newState === 'Removed') {
                const elementToRemove = document.getElementById(`download-${hash}`);
                if (elementToRemove) elementToRemove.remove();
            } else {
                const statusElement = document.getElementById(`status-${hash}`);
                if (statusElement) statusElement.innerText = newState;
            }
        }
    } catch (error) {
        console.error('Action handling failed:', error);
    }
}

// Confirmation popup
function confirmAction(message) {
    return confirm(message || 'Are you sure?');
}

// Dark mode toggle
function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
}

// TMDB Search with input validation
async function searchTmdb() {
    const title = prompt('Enter the title to search on TMDB:').trim();
    const mediaType = prompt('Enter media type (movie or tv):').trim().toLowerCase();

    if (!title || (mediaType !== 'movie' && mediaType !== 'tv')) {
        alert('Valid title and media type are required.');
        return;
    }

    try {
        const data = await fetchWithCSRF('/media_routes/search-tmdb', 'POST', { 
            title, 
            media_type: mediaType, 
            excluded_ids: excludedIds 
        });

        if (data.id) {
            currentTmdbId = data.id;
            updateModalContent(data);
            openModal();
        } else {
            alert(data.message || 'No results found.');
        }
    } catch (error) {
        console.error('TMDB search failed:', error);
    }
}

// Update modal content with fetched data
function updateModalContent(data) {
    document.getElementById('modal-title').innerText = data.title;
    document.getElementById('modal-overview').innerText = data.overview;
    document.getElementById('modal-release-date').innerText = data.release_date;
}

// Open and close modal
function openModal() {
    const modal = document.getElementById('tmdbModal');
    if (modal) modal.style.display = 'block';
}

function closeModal() {
    const modal = document.getElementById('tmdbModal');
    if (modal) modal.style.display = 'none';
}

// Confirm TMDB selection
async function confirmTmdb() {
    try {
        const data = await fetchWithCSRF('/media_routes/confirm-tmdb', 'POST', { 
            title: document.getElementById('modal-title').innerText, 
            tmdb_id: currentTmdbId 
        });

        alert(data.message);
        closeModal();
    } catch (error) {
        console.error('TMDB confirmation failed:', error);
    }
}

// Reject TMDB selection and retry search
function rejectTmdb() {
    excludedIds.push(currentTmdbId);
    closeModal();
    searchTmdb();
}

// Menu toggle for responsive design
function toggleMenu() {
    const navMenu = document.querySelector('nav ul.collapsed');
    if (navMenu) {
        navMenu.classList.toggle('show'); // Toggle the "show" class
    } else {
        console.error('Navigation menu not found.');
    }
}

// Attach all necessary event listeners after the DOM loads
document.addEventListener('DOMContentLoaded', () => {
    // Menu toggle listener
    const menuToggle = document.querySelector('.menu-toggle');
    if (menuToggle) {
        menuToggle.addEventListener('click', toggleMenu);
    }

    // Modal close listener
    const closeModalButton = document.getElementById('closeModalButton');
    if (closeModalButton) {
        closeModalButton.addEventListener('click', closeModal);
    }

    // Dark mode toggle listener
    const darkModeButton = document.getElementById('darkModeToggle');
    if (darkModeButton) {
        darkModeButton.addEventListener('click', toggleDarkMode);
    }

    // Confirmation button listeners
    document.querySelectorAll('.confirm-btn').forEach(button => {
        button.addEventListener('click', event => {
            if (!confirmAction(button.dataset.message)) {
                event.preventDefault();
            }
        });
    });
});
