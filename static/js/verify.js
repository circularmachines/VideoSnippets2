document.addEventListener('DOMContentLoaded', () => {
    // Get item ID from URL
    const params = new URLSearchParams(window.location.search);
    const itemId = params.get('item');
    const videoName = params.get('video');
    
    if (!itemId) {
        showError('No item ID provided');
        return;
    }
    
    if (!videoName) {
        showError('No video name provided');
        return;
    }
    
    // Load item data
    fetch(`/api/library/${itemId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load item');
            }
            return response.json();
        })
        .then(data => {
            displayAudioInfo(data);
        })
        .catch(error => {
            showError(error.message);
        });
    
    // Load transcription
    fetch(`/api/transcription/${videoName}`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to load transcription');
            return response.json();
        })
        .then(data => {
            displayTranscription(data);
        })
        .catch(error => {
            showError(error.message);
        });
});

function displayAudioInfo(data) {
    const content = document.getElementById('verificationContent');
    
    const audioPath = data.audio_path || 'Not available';
    const videoPath = data.video_path || 'Not available';
    
    content.innerHTML = `
        <div class="audio-info">
            <div class="metadata">
                <h3>File Information</h3>
                <p><strong>Video File:</strong> ${videoPath.split('/').pop()}</p>
                <p><strong>Audio File:</strong> ${audioPath.split('/').pop()}</p>
                <p><strong>Status:</strong> ${data.status}</p>
            </div>
            <div class="actions">
                <button onclick="window.location.href='/'">Process Another Video</button>
            </div>
        </div>
    `;
}

function displayTranscription(data) {
    const content = document.getElementById('transcriptionContent');
    
    const segments = data.segments.map(segment => `
        <div class="segment">
            <div class="segment-text">${segment.text}</div>
            <div class="segment-time">${formatTime(segment.start)} - ${formatTime(segment.end)}</div>
        </div>
    `).join('');
    
    content.innerHTML = `
        <div class="transcription">
            <h2>Transcription</h2>
            ${segments}
        </div>
    `;
}

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

function showError(message) {
    const content = document.getElementById('verificationContent');
    content.innerHTML = `
        <div class="error">
            <h2>Error</h2>
            <p>${message}</p>
            <button onclick="window.location.href='/'">Try Again</button>
        </div>
    `;
}
