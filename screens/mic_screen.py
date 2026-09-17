import flet as ft
import flet_audio_recorder as far
import speech_recognition as sr
import asyncio
import threading
import time


# ============================================================
# SETTINGS
# ============================================================

SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2

# Itni der tak audio na aaye to recording stop
SILENCE_SECONDS = 1.2

# Maximum recording duration
MAX_RECORD_SECONDS = 30


class MicScreen:

    def __init__(
        self,
        page: ft.Page,
        on_status=None,
        on_result=None,
        on_recording_change=None,
    ):

        self.page = page

        # ----------------------------------------------------
        # Callbacks
        # ----------------------------------------------------

        self.on_status = (
            on_status
            if on_status
            else lambda text, color="white": None
        )

        self.on_result = (
            on_result
            if on_result
            else lambda text: None
        )

        self.on_recording_change = (
            on_recording_change
            if on_recording_change
            else lambda is_recording: None
        )

        # ----------------------------------------------------
        # Speech Recognition
        # ----------------------------------------------------

        self.recognizer = sr.Recognizer()

        # ====================================================
        # IMPORTANT:
        # on_state_change intentionally NOT used.
        #
        # This prevents:
        # 'MicScreen' object has no attribute '_on_state_change'
        # ====================================================

        self.recorder = far.AudioRecorder(
            on_stream=self._on_audio_stream,
        )

        # ----------------------------------------------------
        # Recording state
        # ----------------------------------------------------

        self.is_recording = False
        self.stop_in_progress = False

        self.record_start_time = 0
        self.last_audio_time = 0

        # ----------------------------------------------------
        # Audio data
        # ----------------------------------------------------

        self.frames = []

        self.lock = threading.Lock()

        # ----------------------------------------------------
        # Background task
        # ----------------------------------------------------

        self.silence_task = None


    # ========================================================
    # MIC BUTTON
    # ========================================================

    def toggle_mic(self, e):

        try:

            self.page.run_task(
                self._toggle_mic
            )

        except Exception as ex:

            print(
                "Toggle microphone error:",
                ex
            )

            self.on_status(
                f"Microphone error: {ex}",
                "red"
            )


    async def _toggle_mic(self):

        if self.is_recording:

            await self.stop_recording()

        else:

            await self.start_recording()


    # ========================================================
    # START RECORDING
    # ========================================================

    async def start_recording(self):

        # Already recording
        if self.is_recording:
            return

        # Previous stop still running
        if self.stop_in_progress:
            return

        try:

            # ------------------------------------------------
            # Microphone permission
            # ------------------------------------------------

            permission = await self.recorder.has_permission()

            if not permission:

                self.on_status(
                    "Microphone permission denied.",
                    "red"
                )

                return

            # ------------------------------------------------
            # Reset old recording
            # ------------------------------------------------

            with self.lock:

                self.frames.clear()

            self.record_start_time = time.time()

            self.last_audio_time = time.time()

            self.stop_in_progress = False

            # ------------------------------------------------
            # Recording ON
            # ------------------------------------------------

            self.is_recording = True

            self.on_recording_change(True)

            self.on_status(
                "Listening...",
                "blue"
            )

            # ------------------------------------------------
            # Start AudioRecorder
            # ------------------------------------------------

            await self.recorder.start_recording(
                configuration=far.AudioRecorderConfiguration(
                    encoder=far.AudioEncoder.PCM16BITS,
                    sample_rate=SAMPLE_RATE,
                    channels=CHANNELS,
                )
            )

            # ------------------------------------------------
            # Start silence watcher
            # ------------------------------------------------

            self.silence_task = asyncio.create_task(
                self._watch_silence()
            )

        except Exception as ex:

            self.is_recording = False

            self.on_recording_change(False)

            self.on_status(
                f"Microphone error: {ex}",
                "red"
            )

            print(
                "Start recording error:",
                ex
            )


    # ========================================================
    # AUDIO STREAM
    # ========================================================

    def _on_audio_stream(self, e):

        if not self.is_recording:
            return

        try:

            # Flet AudioRecorder stream event
            chunk = getattr(
                e,
                "chunk",
                None
            )

            if not chunk:
                return

            # ------------------------------------------------
            # Save audio
            # ------------------------------------------------

            with self.lock:

                if self.is_recording:

                    self.frames.append(
                        bytes(chunk)
                    )

            # ------------------------------------------------
            # Audio received
            # ------------------------------------------------

            self.last_audio_time = time.time()

        except Exception as ex:

            print(
                "Audio stream error:",
                ex
            )


    # ========================================================
    # SILENCE DETECTION
    # ========================================================

    async def _watch_silence(self):

        while self.is_recording:

            await asyncio.sleep(
                0.1
            )

            if not self.is_recording:
                return

            now = time.time()

            # ------------------------------------------------
            # User stopped speaking
            # ------------------------------------------------

            if (
                now - self.last_audio_time
                >= SILENCE_SECONDS
            ):

                await self.stop_recording()

                return

            # ------------------------------------------------
            # Maximum recording time
            # ------------------------------------------------

            if (
                now - self.record_start_time
                >= MAX_RECORD_SECONDS
            ):

                await self.stop_recording()

                return


    # ========================================================
    # STOP RECORDING
    # ========================================================

    async def stop_recording(self):

        if not self.is_recording:
            return

        if self.stop_in_progress:
            return

        self.stop_in_progress = True

        # ----------------------------------------------------
        # Immediately turn OFF UI
        # ----------------------------------------------------

        self.is_recording = False

        self.on_recording_change(False)

        try:

            # ------------------------------------------------
            # Stop recorder
            # ------------------------------------------------

            try:

                await self.recorder.stop_recording()

            except Exception as ex:

                print(
                    "Recorder stop error:",
                    ex
                )

            # ------------------------------------------------
            # Copy frames safely
            # ------------------------------------------------

            with self.lock:

                frames = list(
                    self.frames
                )

                self.frames.clear()

            # ------------------------------------------------
            # No audio
            # ------------------------------------------------

            if not frames:

                self.on_status(
                    "Kuch record nahi hua.",
                    "red"
                )

                return

            # ------------------------------------------------
            # Join all PCM chunks
            # ------------------------------------------------

            audio_bytes = b"".join(
                frames
            )

            self.on_status(
                "Transcribing...",
                "blue"
            )

            # ------------------------------------------------
            # Transcription in background
            # ------------------------------------------------

            threading.Thread(
                target=self._transcribe,
                args=(audio_bytes,),
                daemon=True
            ).start()

        except Exception as ex:

            print(
                "Stop recording error:",
                ex
            )

            self.on_status(
                f"Error: {ex}",
                "red"
            )

        finally:

            self.stop_in_progress = False


    # ========================================================
    # TRANSCRIBE
    # ========================================================

    def _transcribe(
        self,
        audio_bytes
    ):

        try:

            if not audio_bytes:

                self._status(
                    "Kuch bola nahi gaya.",
                    "red"
                )

                return

            # ------------------------------------------------
            # Convert PCM to SpeechRecognition AudioData
            # ------------------------------------------------

            audio_data = sr.AudioData(
                audio_bytes,
                SAMPLE_RATE,
                SAMPLE_WIDTH
            )

            # ------------------------------------------------
            # Google Speech Recognition
            # ------------------------------------------------

            text = self.recognizer.recognize_google(
                audio_data,
                language="en-IN"
            )

            text = text.strip()

            if text:

                # Put recognized text into TextField
                self._result(text)

                self._status(
                    "",
                    "white"
                )

            else:

                self._status(
                    "Samajh nahi aaya.",
                    "red"
                )

        except sr.UnknownValueError:

            self._status(
                "Samajh nahi aaya, dobara boliye.",
                "red"
            )

        except sr.RequestError as ex:

            self._status(
                f"Speech service error: {ex}",
                "red"
            )

        except Exception as ex:

            print(
                "Transcription error:",
                ex
            )

            self._status(
                f"Transcription error: {ex}",
                "red"
            )


    # ========================================================
    # SAFE CALLBACKS
    # ========================================================

    def _status(
        self,
        text,
        color="white"
    ):

        try:

            self.on_status(
                text,
                color
            )

        except Exception as ex:

            print(
                "Status callback error:",
                ex
            )


    def _result(
        self,
        text
    ):

        try:

            self.on_result(
                text
            )

        except Exception as ex:

            print(
                "Result callback error:",
                ex
            )
