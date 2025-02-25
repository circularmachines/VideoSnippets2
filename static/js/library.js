// DOM Elements
const searchInput = document.getElementById('searchInput');
const libraryContent = document.getElementById('libraryContent');
const snippetModal = document.getElementById('snippetModal');
const snippetVideo = document.getElementById('snippetVideo');
const snippetTitle = document.getElementById('snippetTitle');
const snippetDescription = document.getElementById('snippetDescription');

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
    libraryContent.innerHTML = snippets.map(snippet => {
        // Get the first frame from the first segment as thumbnail
        const firstSegment = snippet.segments[0];
        const thumbnailPath = firstSegment ? `/api/frame/${snippet.video_name}/${firstSegment.frame_path}` : '';
        
        return `
            <div class="library-item" onclick="showSnippet('${snippet.video_path}')">
                <div class="thumbnail">
                    <img src="${thumbnailPath}" alt="${snippet.title}" onerror="this.src='/static/img/placeholder.svg'">
                </div>
                <div class="item-info">
                    <h3>${snippet.title}</h3>
                    <p>${snippet.description || 'No description'}</p>
                    <div class="segments-count">
                        ${snippet.segments.length} segments
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Show snippet details
async function showSnippet(snippetId) {
    try {
        console.log('Opening snippet:', snippetId);
        const response = await fetch(`/api/library/${encodeURIComponent(snippetId)}`);
        const snippet = await response.json();
        
        console.log('Snippet data:', snippet);

        // Update modal content
        snippetTitle.textContent = snippet.title;
        snippetDescription.textContent = snippet.description || '';
        
        // Update metadata fields
        document.getElementById('productType').textContent = snippet.product_type || '';
        document.getElementById('condition').textContent = snippet.condition || '';
        document.getElementById('brand').textContent = snippet.brand || '';
        document.getElementById('compatibility').textContent = snippet.compatibility || '';
        document.getElementById('intendedUse').textContent = snippet.intended_use || '';
        document.getElementById('modifications').textContent = (snippet.modifications || []).join(', ');
        document.getElementById('missingParts').textContent = (snippet.missing_parts || []).join(', ');
        
        // Update video source
        snippetVideo.src = snippet.video_url;
        snippetVideo.load();

        // Debug: Log video dimensions when loaded
        snippetVideo.onloadedmetadata = function() {
            console.log('Video dimensions:', {
                width: snippetVideo.videoWidth,
                height: snippetVideo.videoHeight,
                naturalWidth: snippetVideo.naturalWidth,
                naturalHeight: snippetVideo.naturalHeight
            });
        };

        // Add click to play/pause
        const videoContainer = document.querySelector('.video-container');
        videoContainer.onclick = function() {
            if (snippetVideo.paused) {
                snippetVideo.play();
            } else {
                snippetVideo.pause();
            }
        };
        
        // Show modal
        snippetModal.classList.add('visible');
    } catch (error) {
        console.error('Error showing snippet:', error);
        showError('Failed to load snippet details');
    }
}

// Close modal
function closeModal() {
    snippetModal.classList.remove('visible');
    snippetVideo.pause();
    snippetVideo.src = '';
}

// Handle search
function handleSearch(event) {
    const searchTerm = event.target.value.toLowerCase();
    const items = document.querySelectorAll('.library-item');
    
    items.forEach(item => {
        const title = item.querySelector('h3').textContent.toLowerCase();
        const description = item.querySelector('p').textContent.toLowerCase();
        
        if (title.includes(searchTerm) || description.includes(searchTerm)) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });
}

// Format time (seconds to MM:SS)
function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

// Show error message
function showError(message) {
    // You can implement this to show errors in a nice way
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
