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

// Close modal when clicking outside content
snippetModal.addEventListener('click', (e) => {
    if (e.target === snippetModal) {
        closeModal();
    }
});

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
    libraryGrid.innerHTML = snippets.map(snippet => {
        // Get the first frame from the first segment as thumbnail
        const firstSegment = snippet.segments[0];
        const thumbnailPath = firstSegment ? `/api/frame/${snippet.video_name}/${firstSegment.frame_path}` : '';
        
        return `
            <div class="library-item" onclick="showSnippet('${snippet.id}')">
                <div class="thumbnail">
                    <img src="${thumbnailPath}" alt="${snippet.title}" onerror="this.src='/static/img/placeholder.svg'">
                </div>
                <div class="item-info">
                    <h3>${snippet.title}</h3>
                    <p>${snippet.description || 'No description'}</p>
                    <div class="item-meta">
                        <span>${snippet.segments.length} segments</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Show snippet details
async function showSnippet(id) {
    try {
        const response = await fetch(`/api/library/${id}`);
        const snippet = await response.json();
        
        console.log('Snippet data:', snippet);
        
        // Clear previous metadata if it exists
        const existingMetadata = document.querySelector('.metadata-section');
        if (existingMetadata) {
            existingMetadata.remove();
        }

        snippetTitle.textContent = snippet.title;
        snippetDescription.textContent = snippet.description || 'No description';
        
        // Create metadata HTML
        const metadataHtml = `
            <div class="metadata-section">
                <div class="metadata-item">
                    <strong>Product Type:</strong> ${snippet.product_type || 'Not specified'}
                </div>
                <div class="metadata-item">
                    <strong>Condition:</strong> ${snippet.condition || 'Not specified'}
                </div>
                <div class="metadata-item">
                    <strong>Brand:</strong> ${snippet.brand || 'Not specified'}
                </div>
                <div class="metadata-item">
                    <strong>Compatibility:</strong> ${snippet.compatibility || 'Not specified'}
                </div>
                <div class="metadata-item">
                    <strong>Intended Use:</strong> ${snippet.intended_use || 'Not specified'}
                </div>
                <div class="metadata-item">
                    <strong>Modifications:</strong> ${snippet.modifications?.length ? snippet.modifications.join(', ') : 'None'}
                </div>
                <div class="metadata-item">
                    <strong>Missing Parts:</strong> ${snippet.missing_parts?.length ? snippet.missing_parts.join(', ') : 'None'}
                </div>
            </div>
        `;
        
        // Insert metadata after description
        snippetDescription.insertAdjacentHTML('afterend', metadataHtml);
        
        if (snippet.video_name) {
            // Use the video_url provided by the API
            console.log('Video URL:', snippet.video_url);
            snippetVideo.src = snippet.video_url;
            snippetVideo.style.cursor = 'pointer';
            
            // Add click to play/pause
            snippetVideo.onclick = function() {
                if (snippetVideo.paused) {
                    snippetVideo.play();
                } else {
                    snippetVideo.pause();
                }
            };
            
            // Show play icon on hover when paused
            snippetVideo.onmouseover = function() {
                if (snippetVideo.paused) {
                    snippetVideo.style.opacity = '0.8';
                }
            };
            
            snippetVideo.onmouseout = function() {
                snippetVideo.style.opacity = '1';
            };
        }
        
        // Display segments
        segmentsList.innerHTML = snippet.segments.map(segment => `
            <div class="segment">
                <p>${segment.text}</p>
                <span class="time">${formatTime(segment.start)} - ${formatTime(segment.end)}</span>
            </div>
        `).join('');
        
        snippetModal.classList.add('visible');
        
    } catch (error) {
        console.error('Error showing snippet:', error);
        showError('Failed to load snippet');
    }
}

// Close modal
function closeModal() {
    snippetModal.classList.remove('visible');
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
