import pyaudio
import wave
import streamlit as st
import threading
import time
import numpy as np

class VoiceRecorder:
    def __init__(self, sample_rate=16000, channels=1, chunk=1024, format=pyaudio.paInt16):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk = chunk
        self.format = format
        self.audio = pyaudio.PyAudio()
        self.recording = False
        self.frames = []
    
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
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk
            )
            
            st.info(f"Mulai merekam... ({duration} detik)")
            
            frames = []
            
            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Rekam audio
            for i in range(0, int(self.sample_rate / self.chunk * duration)):
                data = stream.read(self.chunk)
                frames.append(data)
                
                # Update progress
                progress = (i + 1) / int(self.sample_rate / self.chunk * duration)
                progress_bar.progress(progress)
                status_text.text(f"Merekam... {int(progress * 100)}%")
            
            # Tutup stream
            stream.stop_stream()
            stream.close()
            
            # Simpan ke file WAV
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.sample_rate)
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
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk
            )
            
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
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.sample_rate)
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
