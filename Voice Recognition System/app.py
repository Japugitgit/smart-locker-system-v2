import streamlit as st
from registration import UserRegistration
import os

st.set_page_config(page_title="Voice Recognition System", page_icon="🎤", layout="wide")
st.title("🎤 Voice Recognition System")
st.write("Daftarkan suara Anda untuk dapat dikenal oleh sistem")

# Navigation
with st.sidebar:
    st.header("📋 Menu")
    st.write("🏠 **Pendaftaran Pengguna** (Halaman Ini)")
    st.info("💡 **Tip:** Halaman 'Identifikasi Suara' akan muncul di sidebar setelah ada pengguna terdaftar.")
    
    st.write("---")
    st.subheader("ℹ️ Tentang Sistem")
    st.write("""
    Sistem ini menggunakan:
    - **SpeechBrain** untuk ekstraksi fitur suara
    - **ECAPA-TDNN** model untuk speaker recognition  
    - **Cosine Similarity** untuk perbandingan suara
    """)

# Initialize session state
if 'registration_started' not in st.session_state:
    st.session_state.registration_started = False
if 'current_step' not in st.session_state:
    st.session_state.current_step = 0
if 'audio_files' not in st.session_state:
    st.session_state.audio_files = []
if 'embeddings' not in st.session_state:
    st.session_state.embeddings = []
if 'user_id' not in st.session_state:
    st.session_state.user_id = ""

# Initialize registration object
registration = UserRegistration()

# Check existing users
if os.path.exists("data/users.json"):
    with st.expander("📋 Lihat Pengguna Terdaftar"):
        if registration.users:
            for user_id, user_data in registration.users.items():
                st.write(f"👤 **{user_id}** - Terdaftar: {user_data.get('registration_date', 'Unknown')}")
        else:
            st.write("Belum ada pengguna terdaftar.")

# User ID input
user_id = st.text_input("Masukkan ID Pengguna:", value=st.session_state.user_id)

if user_id != st.session_state.user_id:
    st.session_state.user_id = user_id
    st.session_state.registration_started = False
    st.session_state.current_step = 0
    st.session_state.audio_files = []
    st.session_state.embeddings = []

# Start registration button
if not st.session_state.registration_started:
    if st.button("🚀 Mulai Pendaftaran", disabled=not user_id):
        if user_id in registration.users:
            st.error(f"❌ User {user_id} sudah terdaftar!")
        else:
            st.session_state.registration_started = True
            st.rerun()

# Registration process
if st.session_state.registration_started and user_id:
    registration_phrases = [
        "Halo, nama saya adalah pengguna baru",
        "Saya sedang mendaftarkan suara saya", 
        "Sistem pengenalan suara sangat menarik",
        "Terima kasih telah menggunakan aplikasi ini"
    ]
    
    st.info(f"📝 Pendaftaran untuk: **{user_id}**")
    st.write("Silakan rekam suara Anda untuk setiap kalimat berikut:")
    
    # Progress bar
    progress = len(st.session_state.audio_files) / len(registration_phrases)
    st.progress(progress, text=f"Progress: {len(st.session_state.audio_files)}/{len(registration_phrases)} rekaman")
    
    # Show recording steps
    for i, phrase in enumerate(registration_phrases):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if i < len(st.session_state.audio_files):
                st.success(f"✅ Kalimat {i+1}: '{phrase}' - Sudah direkam!")
                # Show audio player for recorded files
                if os.path.exists(st.session_state.audio_files[i]):
                    st.audio(st.session_state.audio_files[i])
            elif i == len(st.session_state.audio_files):
                st.write(f"🎯 **Rekam kalimat {i+1}:** '{phrase}'")
            else:
                st.write(f"⏳ Kalimat {i+1}: '{phrase}' - Menunggu...")
        
        with col2:
            if i == len(st.session_state.audio_files):
                if st.button(f"🎤 Rekam", key=f"record_{i}"):
                    # Record audio
                    audio_file = os.path.join("data", f"{user_id}_sample_{i+1}.wav")
                    
                    with st.spinner("🔴 Sedang merekam..."):
                        success = registration.voice_recorder.record_audio(audio_file, duration=5)
                    
                    if success:
                        st.session_state.audio_files.append(audio_file)
                        
                        # Generate embedding
                        with st.spinner("🧠 Menganalisis suara..."):
                            embedding = registration.speaker_model.get_speaker_embedding(audio_file)
                            if embedding is not None:
                                st.session_state.embeddings.append(embedding)
                                st.success(f"✅ Rekaman {i+1} berhasil!")
                                st.rerun()
                            else:
                                st.error("❌ Gagal menganalisis suara. Coba lagi.")
                                # Remove failed audio file
                                if os.path.exists(audio_file):
                                    os.remove(audio_file)
                                if audio_file in st.session_state.audio_files:
                                    st.session_state.audio_files.remove(audio_file)
                    else:
                        st.error("❌ Gagal merekam audio. Coba lagi.")
    
    # Complete registration when all recordings are done
    if len(st.session_state.audio_files) == len(registration_phrases):
        st.success("🎉 Semua rekaman selesai!")
        
        if st.button("💾 Selesaikan Pendaftaran"):
            # Calculate average embedding
            import numpy as np
            avg_embedding = np.mean(st.session_state.embeddings, axis=0)
            
            # Save user to database
            from datetime import datetime
            registration.users[user_id] = {
                "name": user_id,
                "registration_date": datetime.now().isoformat(),
                "audio_files": st.session_state.audio_files,
                "embedding": avg_embedding.tolist(),
                "sample_count": len(st.session_state.audio_files)
            }
            
            registration.save_users_db()
            st.success(f"🎊 User {user_id} berhasil didaftarkan!")
            
            # Reset session state
            st.session_state.registration_started = False
            st.session_state.current_step = 0
            st.session_state.audio_files = []
            st.session_state.embeddings = []
            st.session_state.user_id = ""
            
            st.balloons()
            st.rerun()
