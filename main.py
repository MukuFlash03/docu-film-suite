import streamlit as st
import assemblyai as aai
from moviepy.editor import VideoFileClip
import os
from dotenv import load_dotenv
import json
from anthropic import Anthropic
import re
import zipfile
import io
import base64
from datetime import datetime

client = Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)

claude3_sonnet_model = "claude-3-5-sonnet-20240620"


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

def create_export_package(video_name, transcript_data):
    """Create a ZIP file containing all generated content"""
    # Create a timestamp for the export
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"{video_name}_export_{timestamp}.zip"
    zip_path = os.path.join(TRANSCRIPTS_DIR, zip_filename)
    
    # Create a ZIP file
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add transcript data
        if transcript_data:
            transcript_json = os.path.join(TRANSCRIPTS_DIR, f"{video_name}_transcript.json")
            if os.path.exists(transcript_json):
                zipf.write(transcript_json, os.path.basename(transcript_json))
        
        # Add chapter clips
        chapters_dir = os.path.join(CHAPTERS_DIR)
        for chapter_file in os.listdir(chapters_dir):
            if chapter_file.startswith(f"chapter_") and chapter_file.endswith(f"{video_name}"):
                chapter_path = os.path.join(chapters_dir, chapter_file)
                zipf.write(chapter_path, os.path.join("chapter_clips", chapter_file))
        
        # Add generated content files
        content_files = {
            "summary": f"{video_name}_summary.txt",
            "target_audience": f"{video_name}_target_audience.txt",
            "discussion_guide": f"{video_name}_discussion_guide.txt",
            "social_posts": f"{video_name}_social_posts.txt"
        }
        
        for content_type, filename in content_files.items():
            file_path = os.path.join(TRANSCRIPTS_DIR, filename)
            if os.path.exists(file_path):
                zipf.write(file_path, os.path.join("generated_content", filename))
        
        # Add a README with content overview
        readme_content = f"""Documentary Film Content Package
			Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
			Video: {video_name}

			Contents:
			1. Transcript and Chapters (JSON)
			2. Chapter Video Clips
			3. Generated Content:
			- Summary
			- Target Audience Analysis
			- Discussion Guide
			- Social Media Posts

			Note: This package contains all available generated content at the time of export.
		"""
        zipf.writestr("README.txt", readme_content)
    
    return zip_path

def get_binary_file_downloader_html(bin_file, file_label='File'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    href = f'<a href="data:application/zip;base64,{bin_str}" download="{os.path.basename(bin_file)}">Download {file_label}</a>'
    return href

def get_completion(client, prompt):
	try:
		return client.messages.create(
			model=claude3_sonnet_model,
			max_tokens=2048,
			messages=[{
				"role": 'user', "content":  prompt
			}]
		).content[0].text
	except Exception as e:
		st.error(f"Error generating completion: {str(e)}")
		return None

def generate_summary(transcript_text):
	summary = get_completion(client,
	f"""Here is an documentary film transcript: 
		{transcript_text}

	Please do the following:
	1. Summarize the transcript at a graduate students reading level.
	2. Highlight the key moments / topics from the transcript as 3-5 word sub headings. Then for each of these subheadings, add a one sentence summary.
	"""
	)
	print(summary)
	return summary

def generate_target_audience(transcript_text):
    prompt = f"""Analyze the transcript of my documentary film and identify potential target audiences based on the salient themes. For each audience, explain how their receptivity to various issues and content framing might differ, considering factors such as demographics, interests, and values.

    Transcript:
    {transcript_text}
    """
    return get_completion(client, prompt)

def generate_discussion_guide(transcript_text):
    prompt = f"""Create thought-provoking discussion / study guide questions for my documentary film that challenge the audience to engage with its themes, reflect on their own experiences, and explore actionable solutions. Give me 15-20 questions.

    Transcript:
    {transcript_text}
    """
    return get_completion(client, prompt)

def generate_social_posts(transcript_text):
    prompt = f"""Create impactful social media posts to promote my documentary film. The posts should capture attention, highlight key themes, and encourage viewers to watch and engage with the film. Include calls to action, thought-provoking questions, and hashtags relevant to the social issue. Posts should be tailored for platforms like Instagram, Twitter, and Facebook.

    Transcript:
    {transcript_text}
    """
    return get_completion(client, prompt)

# def extract_tagged_content(text, tag):
#     """Extract content between XML-style tags"""
#     pattern = f"<{tag}>(.*?)</{tag}>"
#     match = re.search(pattern, text, re.DOTALL)
#     return match.group(1).strip() if match else ""

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
    
    if 'current_video' not in st.session_state:
        st.session_state.current_video = None
        
    if 'transcript_data' not in st.session_state:
        st.session_state.transcript_data = None
        
    if 'summary' not in st.session_state:
        st.session_state.summary = None
        
    if 'target_audience' not in st.session_state:
        st.session_state.target_audience = None
        
    if 'discussion_guide' not in st.session_state:
        st.session_state.discussion_guide = None
        
    if 'social_posts' not in st.session_state:
        st.session_state.social_posts = None
    
    uploaded_file = st.file_uploader("Choose a video file", type=['mp4'])
    
    if uploaded_file is not None:
        # Initialize session state
        # if 'current_video' not in st.session_state:
        #     st.session_state.current_video = None
            # st.session_state.transcript_data = None
        
        # Check if this is a new video
        if (st.session_state.current_video != uploaded_file.name):
            st.session_state.summary = None
            st.session_state.discussion_guide = None
            st.session_state.target_audience = None
            st.session_state.discussion_questions = None
            st.session_state.social_posts = None

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
            
        st.divider()
        
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

                    # Check if clip already exists
                    clip_path = get_chapter_clip_path(uploaded_file.name, idx)
                    
                    if os.path.exists(clip_path):
                        st.write("**Chapter Clip:**")
                        with open(clip_path, 'rb') as clip_file:
                            st.video(clip_file.read())

                    button_key = f"extract_chapter_{idx}_{uploaded_file.name}"
                    if not os.path.exists(clip_path):
                        if st.button(f"Extract Chapter {idx} Clip", key=button_key):
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
                    else:
                        st.info("Chapter clip already extracted")
        	
            st.divider()
        
            st.subheader("Summary")
            if st.button("Generate Summary") or st.session_state.summary:
                if not st.session_state.summary: 
                    with st.spinner("Generating summary..."):
                        try:
                            transcript_text = st.session_state.transcript_data['text']
                            completion = generate_summary(transcript_text)
                            
                            if completion:
                                st.session_state.summary = completion
                                
                                # Save the guide
                                guide_path = os.path.join(
                                    TRANSCRIPTS_DIR, 
                                    f"{os.path.splitext(uploaded_file.name)[0]}_summary.txt"
                                )
                                with open(guide_path, 'w') as f:
                                    f.write(completion)
                                
                                st.success("Summary generated and saved!")
                        except Exception as e:
                            st.error(f"Error generating summary: {str(e)}")
                
                # Display the guide if it exists
                if st.session_state.summary:
                    st.markdown(st.session_state.summary)
                    
                    # Add regenerate option
                    # if st.button("Regenerate Summary"):
                    #     st.session_state.summary = None
                    #     st.rerun()
            
            # Display chapter timeline
            # st.subheader("Chapter Timeline")
            # timeline_data = []
            # for idx, chapter in enumerate(st.session_state.transcript_data['chapters'], 1):
            #     timeline_data.append(f"{ms_to_timecode(chapter['start'])} - {chapter['headline']}")
            # st.code('\n'.join(timeline_data))
            
            st.divider()

            st.header("Film Marketing Content")
                    
            # Target Audience Analysis
            st.subheader("Target Audience Analysis")
            if 'target_audience' not in st.session_state:
                st.session_state.target_audience = None
                
            if st.button("Generate Target Audience Analysis") or st.session_state.target_audience:
                if not st.session_state.target_audience:
                    with st.spinner("Analyzing target audiences..."):
                        try:
                            analysis = generate_target_audience(st.session_state.transcript_data['text'])
                            if analysis:
                                st.session_state.target_audience = analysis

                                target_audience_path = os.path.join(
                                    TRANSCRIPTS_DIR, 
                                    f"{os.path.splitext(uploaded_file.name)[0]}_target_audience.txt"
                                )
                                with open(target_audience_path, 'w') as f:
                                    f.write(analysis)
                                
                                st.success("Target audience analysis generated and saved!")
                        except Exception as e:
                            st.error(f"Error generating target audience analysis: {str(e)}")
                
                if st.session_state.target_audience:
                    st.markdown(st.session_state.target_audience)
                    # if st.button("Regenerate Target Audience Analysis"):
                    #     st.session_state.target_audience = None
                    #     st.rerun()

            st.divider()
            
            # Discussion Guide
            st.subheader("Discussion Guide")
            if 'discussion_guide' not in st.session_state:
                st.session_state.discussion_guide = None
                
            if st.button("Generate Discussion Guide") or st.session_state.discussion_guide:
                if not st.session_state.discussion_guide:
                    with st.spinner("Generating discussion guide..."):
                        try:
                            questions = generate_discussion_guide(st.session_state.transcript_data['text'])
                            if questions:
                                st.session_state.discussion_guide = questions
                                discussion_guide_path = os.path.join(
                                    TRANSCRIPTS_DIR, 
                                    f"{os.path.splitext(uploaded_file.name)[0]}_discussion_guide.txt"
                                )
                                with open(discussion_guide_path, 'w') as f:
                                    f.write(questions)
                                
                                st.success("Discussion guide analysis generated and saved!")
                        except Exception as e:
                            st.error(f"Error generating discussion guide: {str(e)}")
                
                if st.session_state.discussion_guide:
                    st.markdown(st.session_state.discussion_guide)
                    # if st.button("Regenerate Discussion Guide"):
                    #     st.session_state.discussion_guide = None
                    #     st.rerun()

            st.divider()

            # Social Media Posts
            st.subheader("Social Media Posts")
            if 'social_posts' not in st.session_state:
                st.session_state.social_posts = None
                
            if st.button("Generate Social Media Posts") or st.session_state.social_posts:
                if not st.session_state.social_posts:
                    with st.spinner("Generating social media content..."):
                        try:
                            posts = generate_social_posts(st.session_state.transcript_data['text'])
                            if posts:
                                st.session_state.social_posts = posts
                                social_posts_path = os.path.join(
                                    TRANSCRIPTS_DIR, 
                                    f"{os.path.splitext(uploaded_file.name)[0]}_social_posts.txt"
                                )
                                with open(social_posts_path, 'w') as f:
                                    f.write(posts)
                                
                                st.success("Social media posts generated and saved!")
                        except Exception as e:
                            st.error(f"Error generating social media posts: {str(e)}")
                
                if st.session_state.social_posts:
                    st.markdown(st.session_state.social_posts)
                    # if st.button("Regenerate Social Media Posts"):
                    #     st.session_state.social_posts = None
                    #     st.rerun()
            st.divider()
            
            # Export section at the bottom
            st.header("Export Content Package")
            if st.button("Create Content Package"):
                try:
                    with st.spinner("Creating content package..."):
                        video_name = os.path.splitext(uploaded_file.name)[0]
                        zip_path = create_export_package(video_name, st.session_state.transcript_data)
                        
                        # Create download link
                        st.markdown(
                            get_binary_file_downloader_html(
                                zip_path, 
                                f'{video_name} Content Package'
                            ),
                            unsafe_allow_html=True
                        )
                        st.success("Content package created successfully!")
                except Exception as e:
                    st.error(f"Error creating content package: {str(e)}")

if __name__ == "__main__":
    main()

