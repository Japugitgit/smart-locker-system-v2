import torch
import torchaudio
import numpy as np
import os
from speechbrain.pretrained import EncoderClassifier
import streamlit as st
from sklearn.metrics.pairwise import cosine_similarity
import json

class SpeakerRecognition:
    def __init__(self):
        """Initialize SpeechBrain speaker recognition model"""
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.load_model()
    @st.cache_resource
    def load_model(_self):
        """Load pre-trained model by first downloading it manually and then loading from the same local dir."""
        from huggingface_hub import snapshot_download
        import os

        # Define a consistent local directory for the model
        local_model_dir = os.path.abspath("models/spkrec-ecapa-voxceleb")

        # 1. Download the model files manually if they don't exist
        if not os.path.exists(os.path.join(local_model_dir, "hyperparams.yaml")):
            st.info("Model not found locally. Downloading... This may take a moment.")
            try:
                snapshot_download(
                    repo_id="speechbrain/spkrec-ecapa-voxceleb",
                    local_dir=local_model_dir,
                    local_dir_use_symlinks=False, # This is the key for downloading
                    repo_type="model"
                )
                st.info("Model download complete.")
            except Exception as e:
                st.error(f"Failed to download model: {e}")
                return None

        # 2. Load the model, telling SpeechBrain the source AND savedir are the same
        try:
            st.info(f"Loading model from: {local_model_dir}")
            # THE ULTIMATE FIX: Set 'source' and 'savedir' to the same path.
            # This prevents from_hparams from creating symlinks internally.
            model = EncoderClassifier.from_hparams(
                source=local_model_dir,
                savedir=local_model_dir, # <-- This is the crucial part
                run_opts={"device": "cpu"}
            )
            st.success("Model successfully loaded! You are all set.")
            return model
        except Exception as e:
            st.error(f"Error loading model from local directory: {str(e)}")
            st.error("This might be a persistent permissions issue. Please try running the terminal or your code editor as an Administrator.")
            return None
            return None
    
    def preprocess_audio(self, audio_file):
        """
        Preprocess audio file for speaker recognition
        
        Args:
            audio_file (str): Path to audio file
        
        Returns:
            torch.Tensor: Preprocessed audio tensor
        """
        try:
            # Load audio file (explicit backend to avoid warnings)
            waveform, sample_rate = torchaudio.load(audio_file, backend="soundfile")
            
            # Convert to mono if stereo
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            
            # Ensure we have the right shape [1, samples]
            if waveform.dim() == 1:
                waveform = waveform.unsqueeze(0)
            
            # Resample to 16kHz if needed
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                waveform = resampler(waveform)
            
            # Ensure minimum length (at least 1 second of audio)
            min_length = 16000  # 1 second at 16kHz
            if waveform.shape[1] < min_length:
                # Pad with zeros if too short
                padding = min_length - waveform.shape[1]
                waveform = torch.nn.functional.pad(waveform, (0, padding))
            
            # Ensure maximum length (limit to 10 seconds to avoid memory issues)
            max_length = 16000 * 10  # 10 seconds
            if waveform.shape[1] > max_length:
                waveform = waveform[:, :max_length]
            
            # Normalize audio
            waveform = waveform / (torch.max(torch.abs(waveform)) + 1e-8)
            
            return waveform
            
        except Exception as e:
            st.error(f"Error preprocessing audio: {str(e)}")
            return None
    
    def get_speaker_embedding(self, audio_file):
        """
        Extract speaker embedding from audio file
        
        Args:
            audio_file (str): Path to audio file
        
        Returns:
            numpy.ndarray: Speaker embedding vector
        """
        if self.model is None:
            self.model = self.load_model()
            if self.model is None:
                return None
        
        try:
            # Preprocess audio
            waveform = self.preprocess_audio(audio_file)
            if waveform is None:
                return None
            
            # Ensure correct shape for SpeechBrain model
            # SpeechBrain expects shape [batch_size, samples]
            if waveform.dim() == 3:  # Remove extra dimension if present
                waveform = waveform.squeeze(0)
            
            # Generate embedding
            with torch.no_grad():
                # SpeechBrain's encode_batch expects [batch_size, samples]
                if waveform.dim() == 1:
                    waveform = waveform.unsqueeze(0)  # Add batch dimension
                elif waveform.dim() == 2 and waveform.shape[0] == 1:
                    # Already correct shape [1, samples]
                    pass
                else:
                    # Reshape to [1, samples]
                    waveform = waveform.view(1, -1)
                
                # Create signal with batch dimension for SpeechBrain
                signal = waveform
                
                # Get embedding
                embedding = self.model.encode_batch(signal)
                
                # Convert to numpy
                if isinstance(embedding, torch.Tensor):
                    embedding = embedding.squeeze().cpu().numpy()
                else:
                    # Handle case where embedding might be a different type
                    embedding = np.array(embedding).squeeze()
            
            return embedding
            
        except Exception as e:
            st.error(f"Error generating embedding: {str(e)}")
            # Print more detailed error information for debugging
            st.error(f"Audio file: {audio_file}")
            if 'waveform' in locals():
                st.error(f"Waveform shape: {waveform.shape}")
            return None
    
    def compare_speakers(self, embedding1, embedding2, threshold=0.8):
        """
        Compare two speaker embeddings
        
        Args:
            embedding1 (numpy.ndarray): First speaker embedding
            embedding2 (numpy.ndarray): Second speaker embedding
            threshold (float): Similarity threshold for speaker verification
        
        Returns:
            tuple: (similarity_score, is_same_speaker)
        """
        try:
            # Calculate cosine similarity
            similarity = cosine_similarity(
                embedding1.reshape(1, -1), 
                embedding2.reshape(1, -1)
            )[0][0]
            
            is_same_speaker = similarity >= threshold
            
            return similarity, is_same_speaker
            
        except Exception as e:
            st.error(f"Error comparing speakers: {str(e)}")
            return 0.0, False
    
    def identify_speaker(self, audio_file, users_db_path, threshold=0.8):
        """
        Identify speaker from audio file against registered users
        
        Args:
            audio_file (str): Path to audio file
            users_db_path (str): Path to users database JSON
            threshold (float): Similarity threshold
        
        Returns:
            tuple: (identified_user_id, confidence_score, all_scores)
        """
        try:
            # Generate embedding for input audio
            test_embedding = self.get_speaker_embedding(audio_file)
            if test_embedding is None:
                return None, 0.0, {}
            
            # Load users database
            if not os.path.exists(users_db_path):
                return None, 0.0, {}
            
            with open(users_db_path, 'r') as f:
                users_db = json.load(f)
            
            if not users_db:
                return None, 0.0, {}
            
            # Compare with all registered users
            scores = {}
            best_match = None
            best_score = 0.0
            
            for user_id, user_data in users_db.items():
                if 'embedding' in user_data:
                    # Convert list back to numpy array
                    user_embedding = np.array(user_data['embedding'])
                    
                    # Calculate similarity
                    similarity, _ = self.compare_speakers(test_embedding, user_embedding, threshold)
                    scores[user_id] = similarity
                    
                    # Check if this is the best match
                    if similarity > best_score and similarity >= threshold:
                        best_score = similarity
                        best_match = user_id
            
            return best_match, best_score, scores
            
        except Exception as e:
            st.error(f"Error identifying speaker: {str(e)}")
            return None, 0.0, {}
    
    def get_model_info(self):
        """Get information about the loaded model"""
        if self.model is None:
            return "Model not loaded"
        
        return {
            "model_name": "ECAPA-TDNN",
            "source": "speechbrain/spkrec-ecapa-voxceleb",
            "device": str(self.device),
            "embedding_size": 192  # ECAPA-TDNN embedding size
        }
