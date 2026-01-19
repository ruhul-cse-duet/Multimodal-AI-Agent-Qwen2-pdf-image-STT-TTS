# 🔊 Text-to-Speech (TTS) Setup Guide

## Issue: "TTS failed: 500 - Internal Server Error"

This error occurs because **Piper TTS is not configured**. TTS is an optional feature and the application works perfectly without it.

---

## ✅ Quick Fix: Disable TTS

If you don't need voice output, simply **uncheck "Enable speech output"** in the frontend when asking questions.

The application will work normally and show text responses without audio.

---

## 🔧 Option 1: Setup Piper TTS (Recommended)

### Step 1: Download Piper

**Windows:**
1. Go to: https://github.com/rhasspy/piper/releases
2. Download: `piper_windows_amd64.zip`
3. Extract to: `C:\piper\`
4. Add to PATH or note the location

**Linux:**
```bash
wget https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz
tar -xzf piper_linux_x86_64.tar.gz
sudo mv piper /usr/local/bin/
```

**macOS:**
```bash
brew install piper-tts
```

### Step 2: Download Voice Model

1. Go to: https://github.com/rhasspy/piper/releases/tag/2023.11.14-2
2. Download a voice model (recommended: `en_US-lessac-medium.onnx`)
3. Also download the corresponding `.json` file (e.g., `en_US-lessac-medium.onnx.json`)
4. Save both files to a directory, e.g., `C:\piper\models\`

**Example:**
```
C:\piper\
├── piper.exe
└── models\
    ├── en_US-lessac-medium.onnx
    └── en_US-lessac-medium.onnx.json
```

### Step 3: Update .env Configuration

```env
# Audio Configuration
PIPER_BINARY=C:\piper\piper.exe
PIPER_MODEL_PATH=C:\piper\models\en_US-lessac-medium.onnx
PIPER_CONFIG_PATH=C:\piper\models\en_US-lessac-medium.onnx.json
PIPER_SPEAKER_ID=
```

**For Linux/Mac:**
```env
PIPER_BINARY=piper
PIPER_MODEL_PATH=/usr/local/share/piper/models/en_US-lessac-medium.onnx
PIPER_CONFIG_PATH=/usr/local/share/piper/models/en_US-lessac-medium.onnx.json
```

### Step 4: Restart Backend

```bash
# Stop the backend (Ctrl+C)
# Then restart:
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Step 5: Test TTS

1. Go to http://localhost:8501
2. Ask a question
3. Check "Enable speech output"
4. Submit query
5. You should hear audio!

---

## 🔧 Option 2: Use Edge TTS (Alternative)

If Piper is too complex, you can use Microsoft Edge TTS (cloud-based):

### Install edge-tts:
```bash
pip install edge-tts
```

### Update audio_processor.py:

Add this method to the `AudioProcessor` class:

```python
async def text_to_speech_edge(self, text: str, output_path: Optional[Path] = None) -> Path:
    """Use Edge TTS as alternative"""
    import edge_tts
    
    if output_path is None:
        output_path = config.TEMP_DIR / f"tts_{abs(hash(text))}.wav"
    
    communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
    await communicate.save(str(output_path))
    
    return output_path
```

---

## 🎯 Available Voice Models

### High Quality (Larger files ~50-100MB):
- `en_US-lessac-high.onnx` - Male, clear
- `en_GB-alba-high.onnx` - Female, British
- `en_US-amy-high.onnx` - Female, American

### Medium Quality (Recommended ~20-30MB):
- `en_US-lessac-medium.onnx` - Male, clear ⭐
- `en_GB-alba-medium.onnx` - Female, British
- `en_US-libritts-high.onnx` - Multiple speakers

### Low Quality (Smaller files ~10-15MB):
- `en_US-lessac-low.onnx` - Male, clear
- `en_GB-alba-low.onnx` - Female, British

**Download from:** https://github.com/rhasspy/piper/releases/tag/2023.11.14-2

---

## 🐛 Troubleshooting

### Issue: "piper: command not found"

**Solution:**
```env
# Use absolute path
PIPER_BINARY=C:\piper\piper.exe
```

### Issue: "Model file not found"

**Solution:**
1. Check file exists:
   ```bash
   # Windows
   dir "C:\piper\models\en_US-lessac-medium.onnx"
   
   # Linux/Mac
   ls /usr/local/share/piper/models/en_US-lessac-medium.onnx
   ```
2. Update path in .env with absolute path

### Issue: "Invalid model format"

**Solution:**
- Make sure you downloaded both `.onnx` AND `.onnx.json` files
- They must be in the same directory

### Issue: "TTS very slow"

**Solution:**
- Use a smaller model (low or medium quality)
- Or use Edge TTS (cloud-based, faster)

---

## ✅ Verification

### Test Piper from Command Line:

**Windows:**
```cmd
echo "Hello, this is a test" | C:\piper\piper.exe --model C:\piper\models\en_US-lessac-medium.onnx --output_file test.wav
```

**Linux/Mac:**
```bash
echo "Hello, this is a test" | piper --model /path/to/model.onnx --output_file test.wav
```

If this works, TTS should work in the application!

---

## 📊 Configuration Examples

### Example 1: Simple Setup (Windows)
```env
PIPER_BINARY=piper
PIPER_MODEL_PATH=C:\Users\YourName\piper\en_US-lessac-medium.onnx
```

### Example 2: Complete Setup
```env
PIPER_BINARY=C:\piper\piper.exe
PIPER_MODEL_PATH=C:\piper\models\en_US-lessac-medium.onnx
PIPER_CONFIG_PATH=C:\piper\models\en_US-lessac-medium.onnx.json
PIPER_SPEAKER_ID=0
```

### Example 3: Linux Setup
```env
PIPER_BINARY=piper
PIPER_MODEL_PATH=/usr/local/share/piper/models/en_US-lessac-medium.onnx
PIPER_CONFIG_PATH=/usr/local/share/piper/models/en_US-lessac-medium.onnx.json
```

---

## 🎯 Quick Decision Guide

**Want the easiest setup?**
→ Don't use TTS (uncheck "Enable speech output")

**Want offline TTS?**
→ Use Piper (this guide)

**Want fastest setup?**
→ Use Edge TTS (requires internet)

**Want best quality?**
→ Use Piper with high-quality models

---

## 📝 Summary

1. **TTS is optional** - Application works fine without it
2. **To disable:** Uncheck "Enable speech output" checkbox
3. **To enable:** 
   - Download Piper + Voice model
   - Update .env
   - Restart backend
4. **Alternative:** Use Edge TTS (cloud-based)

---

## 🔗 Resources

- **Piper Releases:** https://github.com/rhasspy/piper/releases
- **Voice Models:** https://github.com/rhasspy/piper/releases/tag/2023.11.14-2
- **Piper Documentation:** https://github.com/rhasspy/piper
- **Edge TTS:** https://github.com/rn0x/edge-tts

---

**Need help?** The application works perfectly without TTS - just don't enable speech output!
