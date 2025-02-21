document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing upload handlers');
    
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const uploadPrompt = document.querySelector('.upload-prompt');
    const uploadProgress = document.querySelector('.upload-progress');
    const progressBar = document.querySelector('.progress-bar .progress');
    const statusText = document.querySelector('.status');

    // Handle drag and drop events
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    // Handle file input change
    fileInput.addEventListener('change', (e) => {
        const files = e.target.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    async function pollStatus(videoName) {
        try {
            console.log('Polling status for:', videoName);
            const response = await fetch(`/api/status/${videoName}`);
            if (!response.ok) {
                throw new Error('Failed to get status');
            }
            
            const status = await response.json();
            console.log('Status update:', status);
            
            statusText.textContent = status.message;
            
            switch (status.status) {
                case 'uploading':
                    progressBar.style.width = '25%';
                    return false;
                    
                case 'extracting':
                    progressBar.style.width = '50%';
                    return false;
                    
                case 'transcribing':
                    progressBar.style.width = '75%';
                    return false;
                    
                case 'complete':
                    progressBar.style.width = '100%';
                    return true;
                    
                case 'error':
                    throw new Error(status.message);
                    
                default:
                    return false;
            }
        } catch (error) {
            console.error('Status polling error:', error);
            statusText.textContent = `Error: ${error.message}`;
            progressBar.style.backgroundColor = '#ff4444';
            return true;
        }
    }

    async function handleFileUpload(file) {
        console.log('Handling file upload:', file.name);
        
        // Show progress UI
        uploadPrompt.style.display = 'none';
        uploadProgress.style.display = 'block';
        progressBar.style.width = '0%';
        statusText.textContent = 'Starting upload...';
        
        try {
            const formData = new FormData();
            formData.append('video', file);
            
            // Upload file
            statusText.textContent = 'Uploading video...';
            progressBar.style.width = '25%';
            
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('Upload failed');
            }
            
            const result = await response.json();
            console.log('Upload response:', result);
            
            if (result.status === 'success') {
                // Start polling for status
                const videoName = result.video_name;
                console.log('Starting status polling for:', videoName);
                
                const pollInterval = setInterval(async () => {
                    const done = await pollStatus(videoName);
                    if (done) {
                        clearInterval(pollInterval);
                        // Reset UI after 2 seconds
                        setTimeout(() => {
                            uploadPrompt.style.display = 'block';
                            uploadProgress.style.display = 'none';
                            progressBar.style.width = '0%';
                            fileInput.value = '';
                        }, 2000);
                    }
                }, 500);
            } else {
                throw new Error(result.error || 'Processing failed');
            }
            
        } catch (error) {
            console.error('Upload error:', error);
            statusText.textContent = `Error: ${error.message}`;
            progressBar.style.backgroundColor = '#ff4444';
        }
    }
});
