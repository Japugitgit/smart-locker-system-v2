import streamlit as st
import soundfile as sf
import numpy as np
import os
import json
import time
from datetime import datetime
from voice_recorder import VoiceRecorder
from speaker_recognition import SpeakerRecognition

class UserRegistration:
    def __init__(self):
        self.data_dir = "data"
        self.models_dir = "models"
        self.users_db = os.path.join(self.data_dir, "users.json")
        self.voice_recorder = VoiceRecorder()
        self.speaker_model = SpeakerRecognition()
        
        # Pastikan direktori ada
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Load atau buat database users
        self.load_users_db()
    
    def load_users_db(self):
        """Load database users dari file JSON"""
        if os.path.exists(self.users_db):
            with open(self.users_db, 'r') as f:
                self.users = json.load(f)
        else:
            self.users = {}
    
    def save_users_db(self):
        """Simpan database users ke file JSON"""
        with open(self.users_db, 'w') as f:
            json.dump(self.users, f, indent=2)
    
    def register_user(self, user_id):
        """Proses pendaftaran user baru"""
        if user_id in self.users:
            st.warning(f"User {user_id} sudah terdaftar!")
            return False
        
        st.info("Silakan ucapkan beberapa kalimat untuk registrasi suara Anda:")
        
        # Kalimat-kalimat untuk diucapkan user
        registration_phrases = [
            "Halo, nama saya adalah pengguna baru",
            "Saya sedang mendaftarkan suara saya",
            "Sistem pengenalan suara sangat menarik",
            "Terima kasih telah menggunakan aplikasi ini"
        ]
        
        audio_files = []
        embeddings = []
        
        # Record multiple samples
        for i, phrase in enumerate(registration_phrases):
            st.write(f"Ucapkan kalimat {i+1}: '{phrase}'")
            
            if st.button(f"Rekam Kalimat {i+1}", key=f"record_{i}"):
                with st.spinner("Merekam audio..."):
                    # Record audio
                    audio_file = os.path.join(self.data_dir, f"{user_id}_sample_{i+1}.wav")
                    success = self.voice_recorder.record_audio(audio_file, duration=5)
                    
                    if success:
                        audio_files.append(audio_file)
                        st.success(f"Rekaman {i+1} berhasil!")
                        
                        # Play back recorded audio
                        st.audio(audio_file)
                        
                        # Generate speaker embedding
                        embedding = self.speaker_model.get_speaker_embedding(audio_file)
                        embeddings.append(embedding)
                    else:
                        st.error(f"Gagal merekam audio {i+1}")
                        return False
        
        # Simpan user ke database jika semua rekaman berhasil
        if len(audio_files) == len(registration_phrases):
            # Hitung rata-rata embedding
            avg_embedding = np.mean(embeddings, axis=0)
            
            # Simpan data user
            self.users[user_id] = {
                "name": user_id,
                "registration_date": datetime.now().isoformat(),
                "audio_files": audio_files,
                "embedding": avg_embedding.tolist(),  # Convert numpy array to list for JSON
                "sample_count": len(audio_files)
            }
            
            self.save_users_db()
            st.success(f"User {user_id} berhasil didaftarkan!")
            return True
        
        return False

# Wrapper function untuk kompatibilitas
def register_user(user_id):
    """Function wrapper untuk registrasi user"""
    registration = UserRegistration()
    return registration.register_user(user_id)
