try:
    import speech_recognition as sr
    import threading
    import queue as _queue
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class VoiceController:
    """Background voice-recognition thread that pushes recognised commands into a queue."""

    def __init__(self):
        if not AVAILABLE:
            raise RuntimeError("SpeechRecognition / PyAudio not installed")
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.command_queue = _queue.Queue()
        self.is_listening = False

    def start_listening(self):
        self.is_listening = True
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def stop_listening(self):
        self.is_listening = False

    def _listen_loop(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        while self.is_listening:
            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=2)
                command = self.recognizer.recognize_google(audio).lower()
                self.command_queue.put(command)
                print(f"[Voice] {command}")
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except Exception as e:
                print(f"[Voice] error: {e}")

    def get_command(self):
        try:
            return self.command_queue.get_nowait()
        except _queue.Empty:
            return None
