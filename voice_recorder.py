import pyaudio
import wave
import streamlit as st
import threading
import time
import numpy as np

class VoiceRecorder:
    def __init__(self, sample_rate=16000, channels=1, chunk=1024, format=pyaudio.paInt16, input_device_index=None):
        self.sample_rate = sample_rate           # target/default rate for model (16k)
        self.channels = channels
        self.chunk = chunk
        self.format = format
        self.audio = pyaudio.PyAudio()
        self.recording = False
        self.frames = []
        self.input_device_index = input_device_index
        self.device_rate = None                  # actual device default rate (e.g., 44100/48000)
        self._last_used_channels = self.channels

    def list_input_devices(self):
        """List available input devices with at least 1 input channel."""
        devices = []
        try:
            for i in range(self.audio.get_device_count()):
                info = self.audio.get_device_info_by_index(i)
                if int(info.get("maxInputChannels", 0)) > 0:
                    devices.append({
                        "index": i,
                        "name": info.get("name", f"Device {i}"),
                        "rate": int(info.get("defaultSampleRate", self.sample_rate)),
                    })
        except Exception as e:
            st.warning(f"Gagal membaca daftar perangkat audio: {e}")
        return devices

    def set_input_device(self, index: int):
        """Set selected input device index and cache its default sample rate."""
        self.input_device_index = index
        try:
            info = self.audio.get_device_info_by_index(index)
            rate = int(info.get("defaultSampleRate", self.sample_rate))
            if rate > 0:
                self.device_rate = rate
        except Exception:
            self.device_rate = None

    def get_effective_rate(self) -> int:
        """Return actual capture sample rate (device default if available)."""
        if self.device_rate and isinstance(self.device_rate, (int, float)):
            return int(self.device_rate)
        return int(self.sample_rate)

    def _choose_supported_rate(self) -> int:
        """Pick a device-supported input rate to avoid instant-finish/corrupted audio on some mics."""
        # For external mics (especially USB), often need to test actual recording capability
        if self.input_device_index is not None:
            # Test specific rates with actual stream opening for external devices
            test_rates = [48000, 44100, 16000, 32000, 22050]
            if self.device_rate and self.device_rate not in test_rates:
                test_rates.insert(0, int(self.device_rate))
            
            for rate in test_rates:
                if self._test_stream_capability(rate):
                    return int(rate)
        
        # Fallback to original logic for built-in mics
        candidates = []
        if self.device_rate:
            candidates.append(int(self.device_rate))
        candidates += [48000, 44100, 32000, 16000]
        for r in candidates:
            try:
                ok = self.audio.is_format_supported(
                    r,
                    input_device=self.input_device_index if self.input_device_index is not None else None,
                    input_channels=self.channels,
                    input_format=self.format,
                )
                if ok:
                    return int(r)
            except Exception:
                continue
        return int(self.sample_rate)

    def _test_stream_capability(self, rate: int) -> bool:
        """Test if we can actually open and read from a stream at given rate."""
        try:
            kwargs = dict(
                format=self.format,
                channels=self.channels,
                rate=rate,
                input=True,
                frames_per_buffer=self.chunk,
                input_device_index=self.input_device_index
            )
            
            test_stream = self.audio.open(**kwargs)
            
            # Try to read a small amount of data to verify it works
            try:
                test_stream.read(self.chunk, exception_on_overflow=False)
                test_stream.stop_stream()
                test_stream.close()
                return True
            except Exception:
                test_stream.stop_stream()
                test_stream.close()
                return False
                
        except Exception:
            return False

    def _open_input_stream(self):
        """Open PyAudio input stream, with robust external mic support."""
        chosen = self._choose_supported_rate()
        self._last_used_rate = int(chosen)

        # For external mics, be more conservative with buffer sizes
        chunk_size = self.chunk
        if self.input_device_index is not None and self.input_device_index > 0:
            chunk_size = max(2048, self.chunk)  # Larger buffer for external mics

        # Try preferred channels first, then fallback to [2, 1]
        tried = set()
        for ch in [self.channels, 2, 1]:
            if ch in tried:
                continue
            tried.add(ch)
            try:
                kwargs = dict(
                    format=self.format,
                    channels=ch,
                    rate=self._last_used_rate,
                    input=True,
                    frames_per_buffer=chunk_size
                )
                if self.input_device_index is not None:
                    kwargs["input_device_index"] = self.input_device_index
                
                stream = self.audio.open(**kwargs)
                self._last_used_channels = ch
                self._actual_chunk = chunk_size
                
                # Additional validation for external mics
                if self.input_device_index is not None and self.input_device_index > 0:
                    try:
                        # Test read to ensure it's working
                        test_data = stream.read(chunk_size, exception_on_overflow=False)
                        if len(test_data) == 0:
                            stream.stop_stream()
                            stream.close()
                            continue
                    except Exception:
                        stream.stop_stream()
                        stream.close()
                        continue
                
                return stream
            except Exception as e:
                if self.input_device_index is not None and self.input_device_index > 0:
                    st.warning(f"Failed to open stream with {ch} channels at {self._last_used_rate}Hz: {e}")
                continue

        # Last resort: attempt original config (may raise)
        kwargs = dict(
            format=self.format,
            channels=self.channels,
            rate=self._last_used_rate,
            input=True,
            frames_per_buffer=chunk_size
        )
        if self.input_device_index is not None:
            kwargs["input_device_index"] = self.input_device_index
        self._last_used_channels = self.channels
        self._actual_chunk = chunk_size
        return self.audio.open(**kwargs)
    
    def record_audio(self, filename, duration=5):
        """
        Merekam audio dari mikrofon
        
        Args:
            filename (str): Path file untuk menyimpan audio
            duration (int): Durasi rekaman dalam detik
        
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        try:
            # Buka stream audio
            stream = self._open_input_stream()
            used_rate = getattr(self, "_last_used_rate", self.get_effective_rate())
            
            st.info(f"Mulai merekam... ({duration} detik) @ {used_rate} Hz")
            
            frames = []
            
            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Rekam audio
            actual_chunk = getattr(self, '_actual_chunk', self.chunk)
            total_iters = int(used_rate / actual_chunk * duration)
            
            # Add validation for external mics
            empty_reads = 0
            max_empty_reads = 5
            
            for i in range(0, total_iters):
                try:
                    data = stream.read(actual_chunk, exception_on_overflow=False)
                    
                    # Check for empty/invalid data (common with problematic external mics)
                    if len(data) == 0:
                        empty_reads += 1
                        if empty_reads > max_empty_reads:
                            st.error(f"Mikrofon eksternal tidak responsif. Coba pilih device lain atau gunakan mic built-in.")
                            break
                        continue
                    
                    frames.append(data)
                    empty_reads = 0  # Reset counter on successful read
                    
                    # Update progress
                    progress = (i + 1) / max(1, total_iters)
                    progress_bar.progress(progress)
                    status_text.text(f"Merekam... {int(progress * 100)}%")
                    
                except Exception as e:
                    st.error(f"Error membaca dari mikrofon: {e}")
                    break
            
            # Tutup stream
            stream.stop_stream()
            stream.close()
            
            # Simpan ke file WAV
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self._last_used_channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(used_rate)
                wf.writeframes(b''.join(frames))
            
            progress_bar.progress(1.0)
            status_text.text("Rekaman selesai!")
            
            return True
            
        except Exception as e:
            st.error(f"Error dalam merekam audio: {str(e)}")
            return False
    
    def record_with_button(self, filename, key="record_btn"):
        """
        Merekam audio dengan tombol start/stop
        
        Args:
            filename (str): Path file untuk menyimpan audio
            key (str): Unique key untuk tombol Streamlit
        
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🎤 Mulai Rekam", key=f"{key}_start"):
                if not self.recording:
                    self.start_recording()
        
        with col2:
            if st.button("⏹️ Stop Rekam", key=f"{key}_stop"):
                if self.recording:
                    return self.stop_recording(filename)
        
        if self.recording:
            st.warning("Sedang merekam... Klik 'Stop Rekam' untuk menghentikan.")
        
        return False
    
    def start_recording(self):
        """Mulai merekam audio"""
        try:
            self.stream = self._open_input_stream()
            
            self.recording = True
            self.frames = []
            
            # Start recording thread
            self.record_thread = threading.Thread(target=self._record_loop)
            self.record_thread.start()
            
            return True
            
        except Exception as e:
            st.error(f"Error memulai rekaman: {str(e)}")
            return False
    
    def _record_loop(self):
        """Loop untuk merekam audio dalam thread terpisah"""
        while self.recording:
            try:
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                self.frames.append(data)
            except:
                break
    
    def stop_recording(self, filename):
        """Stop merekam dan simpan file"""
        if not self.recording:
            return False
        
        self.recording = False
        
        # Wait for record thread to finish
        if hasattr(self, 'record_thread'):
            self.record_thread.join()
        
        # Stop and close stream
        self.stream.stop_stream()
        self.stream.close()
        
        # Save to file
        try:
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self._last_used_channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(getattr(self, "_last_used_rate", self.get_effective_rate()))
                wf.writeframes(b''.join(self.frames))
            
            st.success(f"Audio berhasil disimpan: {filename}")
            return True
            
        except Exception as e:
            st.error(f"Error menyimpan audio: {str(e)}")
            return False
    
    def __del__(self):
        """Cleanup saat object dihapus"""
        if hasattr(self, 'audio'):
            self.audio.terminate()
