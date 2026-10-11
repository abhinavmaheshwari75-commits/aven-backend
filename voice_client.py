import os
import sys
import time
import wave
import tempfile
import threading
import warnings
import numpy as np
import sounddevice as sd
import websocket
import pyttsx3
from openwakeword.model import Model
from faster_whisper import WhisperModel

# Suppress Hugging Face Hub & System Warnings
os.environ["HF_HUB_DISABLE_SYMLINK_WARNING"] = "1"
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", module="huggingface_hub")

# -------------------------------------------------------------------------
# Audio & Voice Configuration
# -------------------------------------------------------------------------
WS_URL = "ws://127.0.0.1:8000/ws"
SAMPLE_RATE = 16000
CHUNK_SIZE = 1280

# Load Faster-Whisper Model (STT)
print("[INIT] Loading Faster-Whisper model...")
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")

# Load OpenWakeWord Engine
print("[INIT] Loading ONNX wake-word engine...")
wakeword_model = Model(wakeword_models=["hey_jarvis", "alexa"], inference_framework="onnx")

# -------------------------------------------------------------------------
# Thread-Safe Text-To-Speech (TTS) Engine
# -------------------------------------------------------------------------
tts_lock = threading.Lock()

def speak(text: str):
    """Speaks text response out loud in a non-blocking background thread."""
    if not text or not text.strip():
        return

    def _run_tts():
        with tts_lock:
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", 175)  # Speech pace speed
                voices = engine.getProperty("voices")
                if voices:
                    engine.setProperty("voice", voices[0].id)
                engine.say(text)
                engine.runAndWait()
                engine.stop()
            except Exception as e:
                print(f"[TTS Error] Could not synthesize speech: {e}")

    threading.Thread(target=_run_tts, daemon=True).start()

# -------------------------------------------------------------------------
# WebSocket Communication Handler
# -------------------------------------------------------------------------
def send_and_receive(prompt: str) -> str:
    """Sends user voice command over WebSocket to main.py and receives output."""
    try:
        ws = websocket.create_connection(WS_URL, timeout=30)
        ws.send(prompt)
        
        response_text = ""
        while True:
            try:
                chunk = ws.recv()
                if chunk:
                    response_text += chunk
            except websocket.WebSocketTimeoutException:
                break
            except Exception:
                break
        ws.close()
        return response_text.strip()
    except Exception as e:
        return f"Error connecting to backend: {str(e)}"

# -------------------------------------------------------------------------
# Audio Recording & STT Helper
# -------------------------------------------------------------------------
def record_command(duration: int = 5) -> str:
    """Records user voice for a set duration and transcribes it using Faster-Whisper."""
    print("[Aven Active] Listening for your command...")
    audio_data = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='int16')
    sd.wait()

    # Save audio temporarily for Whisper transcription
    temp_wav = os.path.join(tempfile.gettempdir(), "aven_input.wav")
    with wave.open(temp_wav, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_data.tobytes())

    print("[Aven Active] Transcribing audio...")
    segments, _ = whisper_model.transcribe(temp_wav, beam_size=5)
    transcription = " ".join([seg.text for seg in segments]).strip()
    
    # Clean up temporary WAV file
    if os.path.exists(temp_wav):
        try:
            os.remove(temp_wav)
        except Exception:
            pass

    return transcription

# -------------------------------------------------------------------------
# Hands-Free Listener Main Loop
# -------------------------------------------------------------------------
def main():
    print("Initializing Aven Hands-Free Voice Channel...")
    print("[CONNECTED] Hands-Free Voice Channel Active.")
    print("\n[Aven Standby] Listening for wake-word... (Say 'Hey Jarvis' or 'Alexa' to awaken Aven)\n")

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16', blocksize=CHUNK_SIZE) as stream:
        while True:
            audio_frame, _ = stream.read(CHUNK_SIZE)
            audio_data = np.frombuffer(audio_frame, dtype=np.int16)

            # Pass audio chunk to wake-word engine
            prediction = wakeword_model.predict(audio_data)

            triggered = False
            for model_name, score in wakeword_model.prediction_buffer.items():
                if score[-1] >= 0.5:  # Sensitivity threshold
                    print(f"\n[WAKE WORD DETECTED] Triggered by model: {model_name} (Score: {score[-1]:.2f})")
                    triggered = True
                    break

            if triggered:
                wakeword_model.reset()
                
                # Capture and transcribe voice command
                user_text = record_command(duration=5)
                
                if user_text:
                    print(f"You (Voice): {user_text}")
                    
                    # Send prompt to main.py server over WebSockets
                    response = send_and_receive(user_text)
                    
                    if response:
                        print(f"\nAven: {response}\n")
                        # Speak the response aloud using non-blocking TTS
                        speak(response)
                else:
                    print("[Aven] No spoken input detected.")

                print("\n[Aven Standby] Listening for wake-word...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting Aven Voice Client.")
        sys.exit(0)