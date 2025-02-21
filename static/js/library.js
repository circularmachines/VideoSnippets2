// DOM Elements
const searchInput = document.getElementById('searchInput');
const libraryGrid = document.getElementById('libraryGrid');
const snippetModal = document.getElementById('snippetModal');
const snippetVideo = document.getElementById('snippetVideo');
const snippetTitle = document.getElementById('snippetTitle');
const snippetDescription = document.getElementById('snippetDescription');
const segmentsList = document.getElementById('segmentsList');

// Event Listeners
searchInput.addEventListener('input', debounce(handleSearch, 300));

// Load library data
async function loadLibrary() {
    try {
        const response = await fetch('/api/library');
        const snippets = await response.json();
        displayLibrary(snippets);
    } catch (error) {
        console.error('Error loading library:', error);
        showError('Failed to load library');
    }
}

// Display library items
function displayLibrary(snippets) {
    libraryGrid.innerHTML = snippets.map(snippet => `
        <div class="library-item" onclick="showSnippet('${snippet.id}')">
            <div class="item-info">
                <h3>${snippet.title}</h3>
                <p>${snippet.description || 'No description'}</p>
                <div class="item-meta">
                    <span>${snippet.segments.length} segments</span>
                </div>
            </div>
        </div>
    `).join('');
}

// Show snippet details
async function showSnippet(id) {
    try {
        const response = await fetch(`/api/library/${id}`);
        const snippet = await response.json();
        
        console.log('Snippet data:', snippet);
        
        snippetTitle.textContent = snippet.title;
        snippetDescription.textContent = snippet.description || 'No description';
        
        if (snippet.video_name) {
            // Convert title to filename format and make it match the actual files
            const filename = snippet.title
                .toLowerCase()
                .replace(/[^a-z0-9]+/g, '_')  // Replace any non-alphanumeric chars with underscore
                .replace(/^_+|_+$/g, '')      // Remove leading/trailing underscores
                + '.mp4';
            const videoPath = `${snippet.video_name}/videos/${filename}`;
            console.log('Video path:', videoPath);
            snippetVideo.src = `/api/video/${videoPath}`;
            snippetVideo.parentElement.style.display = 'block';
        } else {
            console.log('No video_name in snippet data');
            snippetVideo.parentElement.style.display = 'none';
        }
        
        // Display segments
        segmentsList.innerHTML = snippet.segments.map(segment => `
            <div class="segment">
                <p>${segment.text}</p>
                <span class="timestamp">${formatTime(segment.start)} - ${formatTime(segment.end)}</span>
            </div>
        `).join('');
        
        snippetModal.style.display = 'block';
    } catch (error) {
        console.error('Error loading snippet:', error);
        showError('Failed to load snippet');
    }
}

// Close modal
function closeModal() {
    snippetModal.style.display = 'none';
    snippetVideo.pause();
    snippetVideo.src = '';
}

// Handle search
async function handleSearch(event) {
    const query = event.target.value.trim();
    try {
        const response = await fetch(`/api/library/search?q=${encodeURIComponent(query)}`);
        const snippets = await response.json();
        displayLibrary(snippets);
    } catch (error) {
        console.error('Error searching:', error);
        showError('Search failed');
    }
}

// Format time (seconds to MM:SS)
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Show error message
function showError(message) {
    // TODO: Implement error display
    console.error(message);
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Load library on page load
loadLibrary();
