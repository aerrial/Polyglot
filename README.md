# Polyglot: Automated Video Dubbing & Voice Cloning
PolyGlot is an intelligent pipeline designed to automate the process of video translation and dubbing while preserving the original speaker's vocal characteristics. This project was developed as a university thesis to demonstrate the integration of modern AI models in speech processing.

## 🌟 Key Features
  - Speech-to-Text (ASR): High-accuracy transcription using OpenAI Whisper.

  - Neural Translation: Seamless translation of captured text while maintaining context.

  - Voice Cloning (TTS): Generation of natural-sounding speech that mimics a specific voice profile (using XTTS v2 / ElevenLabs).

  - Smart Sync: Automatic time-stretching of audio tracks to perfectly match the original video duration.

  - Automated Video Composition: End-to-end processing from raw video to a fully dubbed output using MoviePy.

## 🛠 Technology Stack
  - Language: Python 3.10+

  - AI Models: * faster-whisper (Speech Recognition)

  - Coqui XTTS or gTTS (Speech Synthesis)

  - Video Processing: MoviePy 2.0, FFmpeg

  - UI: Streamlit or Gradio

## 🚀 Getting Started
1. Clone the repository
```
Bash
git clone https://github.com/yourusername/VoiceSync-AI.git
cd VoiceSync-AI
```
3. Install dependencies
```
Bash
pip install -r requirements.txt
```
5. Run the prototype
```
Bash
python dubbing_test.py
```
## 📈 Roadmap
[x] Basic audio-video extraction and merging

[x] Speech-to-Text integration (Whisper)

[x] Dynamic time-stretching for audio sync

[] Integration of zero-shot voice cloning

[] Development of a web-based GUI

[] Implementation of Wav2Lip for visual synchronization

## 📜 License
This project is licensed under the MIT License - see the LICENSE file for details.
