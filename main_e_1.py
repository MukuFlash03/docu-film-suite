import streamlit as st
import assemblyai as aai
from moviepy.editor import VideoFileClip
import os
from dotenv import load_dotenv
import json

load_dotenv()

# Configure AssemblyAI
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
transcriber = aai.Transcriber(
    config=aai.TranscriptionConfig(
        auto_chapters=True,
        iab_categories=True
    )
)

# Get current directory and create necessary folders
CURRENT_DIR = os.getcwd()
UPLOADS_DIR = os.path.join(CURRENT_DIR, "uploads")
CHAPTERS_DIR = os.path.join(CURRENT_DIR, "chapters")
TRANSCRIPTS_DIR = os.path.join(CURRENT_DIR, "transcripts")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(CHAPTERS_DIR, exist_ok=True)
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

def get_chapter_clip_path(video_name, chapter_idx):
    """Get the path for a chapter clip"""
    return os.path.join(CHAPTERS_DIR, f"chapter_{chapter_idx}_{video_name}")

def create_transcript(input_video_path, video_name):
    transcript_path = os.path.join(TRANSCRIPTS_DIR, f"{video_name}_transcript.json")
    
    # Check if transcript already exists
    if os.path.exists(transcript_path):
        print("Loading existing transcript...")
        with open(transcript_path, 'r') as f:
            transcript_data = json.load(f)
            return transcript_data
    
    print("Creating new transcript...")
    transcript = transcriber.transcribe(input_video_path)
    
    if transcript.error: raise RuntimeError(transcript.error)
    print("Transcript Text:")
    print(transcript.text, end='\n\n')
    print("*"*100)
    
    # Save transcript data
    transcript_data = {
        'text': transcript.text,
        'chapters': [
            {
                'start': chapter.start,
                'end': chapter.end,
                'headline': chapter.headline,
                'summary': chapter.summary,
                'gist': chapter.gist
            }
            for chapter in transcript.chapters
        ],
        'categories': {
            topic: relevance
            for topic, relevance in transcript.iab_categories.summary.items()
        }
    }
    
    with open(transcript_path, 'w') as f:
        json.dump(transcript_data, f)
    
    return transcript_data

def ms_to_timecode(ms):
    """Convert milliseconds to HH:MM:SS format"""
    seconds = int(ms / 1000)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def ms_to_seconds(ms):
    """Convert milliseconds to seconds"""
    return ms / 1000.0

def extract_chapter_clip(video_path, start_ms, end_ms, output_path):
    """Extract a clip from the video based on start and end times"""
    with VideoFileClip(video_path) as video:
        start_sec = ms_to_seconds(start_ms)
        end_sec = ms_to_seconds(end_ms)
        clip = video.subclip(start_sec, end_sec)
        clip.write_videofile(output_path, codec='libx264')

def main():
    st.title("Documentary Film Suite")
    
    uploaded_file = st.file_uploader("Choose a video file", type=['mp4'])
    
    if uploaded_file is not None:
        # Initialize session state
        if 'current_video' not in st.session_state:
            st.session_state.current_video = None
            st.session_state.transcript_data = None
        
        # Check if this is a new video
        if (st.session_state.current_video != uploaded_file.name):
            # Save uploaded video
            video_path = os.path.join(UPLOADS_DIR, uploaded_file.name)
            with open(video_path, "wb") as f:
                f.write(uploaded_file.read())
            
            # Update session state
            st.session_state.current_video = uploaded_file.name
            
            # Process transcript
            with st.spinner("Analyzing video..."):
                print("Getting transcript...")
                try:
                    # transcript = create_transcript(video_path)
                    st.session_state.transcript_data = create_transcript(
                        video_path,
                        os.path.splitext(uploaded_file.name)[0]
                    )
                    print("Transcript created.")
                    print("*"*100)
                except Exception as e:
                    st.error(f"Error processing video: {str(e)}")
                    print(f"Error details: {str(e)}")
                    return
        
        # Display video and analysis
        video_path = os.path.join(UPLOADS_DIR, uploaded_file.name)
        
        # Display original video
        st.subheader("Original Video")
        with open(video_path, 'rb') as video_file:
            st.video(video_file.read())
        
        if st.session_state.transcript_data:
            # Display chapters
            st.subheader("Video Chapters")
            for idx, chapter in enumerate(st.session_state.transcript_data['chapters'], 1):
                with st.expander(f"Chapter {idx}: {chapter['gist']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Timestamp:**")
                        st.write(f"Start: {ms_to_timecode(chapter['start'])}")
                        st.write(f"End: {ms_to_timecode(chapter['end'])}")
                        st.write(f"Duration: {ms_to_timecode(chapter['end'] - chapter['start'])}")
                    
                    with col2:
                        st.write("**Gist:**")
                        st.write(chapter['gist'])
                        st.write("**Headline:**")
                        st.write(chapter['headline'])                        
                        st.write("**Summary:**")
                        st.write(chapter['summary'])     

                    # Create unique key for each button
                    button_key = f"extract_chapter_{idx}_{uploaded_file.name}"
                    if st.button(f"Extract Chapter {idx} Clip", key=button_key):
                        clip_path = os.path.join(
                            CHAPTERS_DIR, 
                            f"chapter_{idx}_{uploaded_file.name}"
                        )
                        with st.spinner("Extracting clip..."):
                            extract_chapter_clip(
                                video_path,
                                chapter['start'],
                                chapter['end'],
                                clip_path
                            )
                            # Read and display the clip
                            with open(clip_path, 'rb') as clip_file:
                                st.video(clip_file.read())
            
            # Display chapter timeline
            # st.subheader("Chapter Timeline")
            # timeline_data = []
            # for idx, chapter in enumerate(st.session_state.transcript_data['chapters'], 1):
            #     timeline_data.append(f"{ms_to_timecode(chapter['start'])} - {chapter['headline']}")
            # st.code('\n'.join(timeline_data))

if __name__ == "__main__":
    main()