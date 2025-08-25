import streamlit as st
from registration import UserRegistration
import os
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Voice Identification", page_icon="🎯")
st.title("🎯 Voice Identification")
st.write("Test sistem pengenalan suara dengan berbicara")

# Initialize
registration = UserRegistration()

# Check if there are registered users
if not registration.users:
    st.warning("⚠️ Belum ada pengguna terdaftar. Silakan daftar terlebih dahulu di halaman utama.")
    st.stop()

st.info(f"📊 {len(registration.users)} pengguna terdaftar dalam sistem")

# Show registered users
with st.expander("👥 Pengguna Terdaftar"):
    for user_id, user_data in registration.users.items():
        st.write(f"👤 **{user_id}** - Terdaftar: {user_data.get('registration_date', 'Unknown')}")

st.write("---")

# Voice identification section
st.subheader("🎤 Identifikasi Suara")
st.write("Ucapkan sesuatu untuk mengidentifikasi siapa Anda:")

# Record test audio
if st.button("🎤 Mulai Rekam untuk Identifikasi"):
    test_audio_file = os.path.join("data", "test_identification.wav")
    
    with st.spinner("🔴 Sedang merekam... (5 detik)"):
        success = registration.voice_recorder.record_audio(test_audio_file, duration=5)
    
    if success:
        st.success("✅ Rekaman berhasil!")
        st.audio(test_audio_file)
        
        # Identify speaker
        with st.spinner("🧠 Menganalisis dan mengidentifikasi suara..."):
            identified_user, confidence, all_scores = registration.speaker_model.identify_speaker(
                test_audio_file, 
                registration.users_db,
                threshold=0.7  # Lower threshold for testing
            )
        
        st.write("---")
        st.subheader("📊 Hasil Identifikasi")
        
        if identified_user:
            st.success(f"🎉 **Teridentifikasi sebagai: {identified_user}**")
            st.write(f"🎯 **Confidence Score: {confidence:.3f}**")
            
            # Show confidence level
            if confidence >= 0.9:
                st.success("🟢 Kepercayaan Tinggi")
            elif confidence >= 0.8:
                st.warning("🟡 Kepercayaan Sedang")
            else:
                st.info("🔵 Kepercayaan Rendah")
        else:
            st.error("❌ **Tidak dapat mengidentifikasi pengguna**")
            st.write("Kemungkinan:")
            st.write("- Suara tidak cocok dengan pengguna yang terdaftar")
            st.write("- Kualitas audio kurang baik")
            st.write("- Perlu registrasi ulang dengan suara yang lebih jelas")
        
        # Show similarity scores for all users
        if all_scores:
            st.subheader("📈 Skor Kesamaan dengan Semua Pengguna")
            
            # Create bar chart
            users = list(all_scores.keys())
            scores = list(all_scores.values())
            
            fig = go.Figure(data=[
                go.Bar(
                    x=users, 
                    y=scores,
                    marker_color=['green' if user == identified_user else 'lightblue' for user in users],
                    text=[f'{score:.3f}' for score in scores],
                    textposition='auto',
                )
            ])
            
            fig.update_layout(
                title="Skor Kesamaan Suara",
                xaxis_title="Pengguna",
                yaxis_title="Skor Kesamaan",
                yaxis=dict(range=[0, 1]),
                showlegend=False
            )
            
            # Add threshold line
            fig.add_hline(y=0.7, line_dash="dash", line_color="red", 
                         annotation_text="Threshold (0.7)")
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show detailed scores
            st.subheader("📋 Detail Skor")
            for user, score in sorted(all_scores.items(), key=lambda x: x[1], reverse=True):
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    if user == identified_user:
                        st.write(f"🏆 **{user}**")
                    else:
                        st.write(f"👤 {user}")
                with col2:
                    st.write(f"{score:.3f}")
                with col3:
                    if score >= 0.7:
                        st.write("✅ Pass")
                    else:
                        st.write("❌ Fail")
    else:
        st.error("❌ Gagal merekam audio. Coba lagi.")

# Tips section
st.write("---")
st.subheader("💡 Tips untuk Identifikasi yang Baik")
st.write("""
- 🎤 Pastikan mikrofon berfungsi dengan baik
- 🔇 Rekam di lingkungan yang tenang
- 🗣️ Berbicara dengan volume normal dan jelas
- ⏱️ Gunakan waktu rekaman 5 detik dengan optimal
- 🎯 Ucapkan kalimat lengkap, bukan hanya kata pendek
""")

# Model info
with st.expander("ℹ️ Informasi Model"):
    model_info = registration.speaker_model.get_model_info()
    if isinstance(model_info, dict):
        for key, value in model_info.items():
            st.write(f"**{key}:** {value}")
    else:
        st.write(model_info)
