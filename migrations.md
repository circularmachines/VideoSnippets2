# Migration Plan

## Files to Migrate

### Core Processing
- [ ] extract_audio.py → processing/audio.py
- [ ] extract_frames.py → processing/video.py
- [ ] process_segments.py → processing/analysis.py
- [ ] transcribe_with_timestamps.py → processing/audio.py
- [ ] cut_video_segments.py → processing/video.py

### Dependencies
- [x] ai_docs/ (symlinked)
- [x] .env (symlinked)

### Frontend
- [ ] static/styles.css → static/css/styles.css (done)
- [ ] static/verify.html → static/verify.html (in progress)
- [ ] static/index.html → static/index.html (new version)

## Migration Steps

1. **Phase 1: Basic Structure** ✓
   - Set up new directory structure
   - Create placeholder modules
   - Set up frontend templates

2. **Phase 2: Core Processing**
   - Migrate video processing
   - Migrate audio processing
   - Migrate analysis
   - Update imports and dependencies

3. **Phase 3: Frontend**
   - Migrate and update CSS
   - Create new upload interface
   - Update verification interface
   - Add library view

4. **Phase 4: Testing**
   - Test video upload flow
   - Test processing pipeline
   - Test verification interface
   - Test library management

## Notes

- Keep both repos functional during migration
- Test each component after migration
- Update documentation as components are moved
