import assemblyai as aai
from dotenv import load_dotenv
import os
import json
from moviepy.editor import VideoFileClip
import streamlit as st
import tempfile

load_dotenv()

base_path = "/Users/mukuflash/Documents/Projects/Python/documentary-summarizer/" 
videos_list = [
  "Doc_1_Anchored",
  "Doc_2_Black_Mothers"
]

aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

# we add a TranscriptionConfig to turn on Auto Chapters
transcriber = aai.Transcriber(
	config=aai.TranscriptionConfig(
		auto_chapters=True,
		iab_categories=True
	)
)

# def create_transcript(video_name):
def create_transcript(input_video_path):
	print("Inside create transcript function...")
	transcript = transcriber.transcribe(
		# f"{base_path}{video_name}.mp4"  
		input_video_path
	)

	if transcript.error: raise RuntimeError(transcript.error)

	print("Transcript Text:")
	print(transcript.text, end='\n\n')
	print("*"*100)

	return transcript

def print_video_sections(transcript):
	for chapter in transcript.chapters:
		print(f"Start: {chapter.start}, End: {chapter.end}")
		print(f"Summary: {chapter.summary}")
		print(f"Headline: {chapter.headline}")
		print(f"Gist: {chapter.gist}")
		print("\n\n")
	print("*"*100)

def get_categories(transcript):
	# Get the parts of the transcript that were tagged with topics
	for result in transcript.iab_categories.results:
		print("\n\n")
		print(result.text)
		print(f"Timestamp: {result.timestamp.start} - {result.timestamp.end}")
		for label in result.labels:
			print(f"{label.label} ({label.relevance})")
	print("*"*100)
  		
	# Get a summary of all topics in the transcript
	for topic, relevance in transcript.iab_categories.summary.items():
		print("\n\n")
		print(f"Audio is {relevance * 100}% relevant to {topic}")
	print("*"*100)

def ms_to_hms(start):
	s, ms = divmod(start, 1000)
	m, s = divmod(s, 60)
	h, m = divmod(m, 60)
	return h, m, s

def create_timestamps(chapters):
	last_hour = ms_to_hms(chapters[-1].start)[0]
	time_format = "{m:02d}:{s:02d}" if last_hour == 0 else "{h:02d}:{m:02d}:{s:02d}"

	lines = []
	for idx, chapter in enumerate(chapters):
		# first YouTube timestamp must be at zero
		h, m, s = (0, 0, 0) if idx == 0 else ms_to_hms(chapter.start)
		lines.append(f"{time_format.format(h=h, m=m, s=s)} {chapter.headline}")

	return "\n".join(lines)

def generate_timestamps(transcript, video_name):
	timestamp_lines = create_timestamps(transcript.chapters)
	print("\n\n")
	print(timestamp_lines)
	print("*"*100)

	timestamp_dict = {}
	for line_number, line in enumerate(timestamp_lines.splitlines(), 1):
		timestamp, chapter = line.split(' ', 1)
		timestamp_dict[str(line_number)] = {
			"timestamp": timestamp,
			"chapter": chapter
		}

	with open(f'{video_name}.json', 'w') as f:
		json.dump(timestamp_dict, f, indent=2)

# if __name__ == "__main__":
# 	video_name = videos_list[0]
# 	# video_name = videos_list[1]
# 	print("Creating transcript...")
# 	transcript = create_transcript(video_name)
# 	print("Transcript created.")
# 	print("*"*100)
# 	print("Getting categories...")
# 	get_categories(transcript)
# 	print("Categories retrieved.")
# 	print("Printing video sections...")
# 	print_video_sections(transcript)
# 	print("Video sections printed.")
# 	print("*"*100)
# 	print("Generating timestamps...")
# 	generate_timestamps(transcript, video_name)
# 	print("Timestamps generated.")
# 	print("*"*100)

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
	st.title("Video Chapter Analysis")

	uploaded_file = st.file_uploader("Choose a video file", type=['mp4'])

	if uploaded_file is not None:
		print("Inside if uploaded file check...")
		
		# base_path = "/Users/mukuflash/Documents/Projects/Python/documentary-summarizer/"
		# input_video_path = os.path.join(base_path, "uploads", "input_video.mp4")
		# input_video_path = os.path.join("uploads", "input_video.mp4")
		# input_video_path = os.path.join("uploads", uploaded_file.name)

		with tempfile.TemporaryDirectory() as temp_dir:
			
			input_video_path = os.path.join(temp_dir, "input_video.mp4")
			with open(input_video_path, "wb") as f:
				f.write(uploaded_file.read())

			st.subheader("Original Video")
			with open(input_video_path, 'rb') as video_file:
				st.video(video_file.read())
		
			# Transcribe and analyze
			with st.spinner("Analyzing video..."):
				try:
					print("Getting transcript...")
					transcript = create_transcript(input_video_path)
					print("Transcript created.")
					print("*"*100)

					print("Printing video sections...")
					print_video_sections(transcript)
					print("Video sections printed.")
					print("*"*100)
					
					print("Generating timestamps...")
					generate_timestamps(transcript, input_video_path)
					print("Timestamps generated.")
					print("*"*100)
				
					# Display chapters
					st.subheader("Video Chapters")
					for idx, chapter in enumerate(transcript.chapters, 1):
						# with st.expander(f"Chapter {idx}: {chapter.headline}"):
						with st.expander(f"Chapter {idx}: {chapter.gist}"):
							col1, col2 = st.columns(2)
						
							with col1:
								st.write("**Timestamp:**")
								# st.write(f"Start: {ms_to_seconds(chapter.start):.2f}s")
								# st.write(f"End: {ms_to_seconds(chapter.end):.2f}s")
								st.write(f"Start: {ms_to_timecode(chapter.start)}")
								st.write(f"End: {ms_to_timecode(chapter.end)}")
								st.write(f"Duration: {ms_to_timecode(chapter.end - chapter.start)}")
							
							with col2:
								st.write("**Gist:**")
								st.write(chapter.gist)
								st.write("**Summary:**")
								st.write(chapter.summary)
								st.write("**Headline:**")
								st.write(chapter.headline)
						
							# Extract chapter clip button
							if st.button(f"Extract Chapter {idx} Clip"):
								clip_path = os.path.join(temp_dir, f"chapter_{idx}.mp4")
								with st.spinner("Extracting clip..."):
									extract_chapter_clip(
										input_video_path,
										chapter.start,
										chapter.end,
										clip_path
									)
								
									with open(clip_path, 'rb') as clip_file:
										st.video(clip_file.read())            

				
					# # Display IAB categories
					# st.subheader("Content Categories")
					# for topic, relevance in transcript.iab_categories.summary.items():
					# 	st.write(f"- {topic}: {relevance * 100:.1f}%")
				
				except Exception as e:
					st.error(f"Error processing video: {str(e)}")

if __name__ == "__main__":
	main()

# prompt = f"""
# ROLE:
# You are a YouTube content professional. You are very competent and able to come up with catchy names for the different sections of video transcripts that are submitted to you.
# CONTEXT:
# This transcript is of a logistics meeting at GitLab
# INSTRUCTION:
# You are provided information about the sections of the transcript under TIMESTAMPS, where the format for each line is `<TIMESTAMP> <SECTION SUMMARY>`."
# TIMESTAMPS:
# {timestamp_lines}
# FORMAT:
# <TIMESTAMP> <CATCHY SECTION TITLE>
# OUTPUT:
# """.strip()

# result = transcript.lemur.task(prompt)

# # Extract the response text and print
# output = result.response.strip()
# print(output)
# print("*"*100)


# import re

# def filter_timestamps(text):
#     lines = text.splitlines()
#     timestamped_lines = [line for line in lines if re.match(r'\d+:\d+', line)]  # Use regex to filter lines starting with a timestamp
#     filtered_text = '\n'.join(timestamped_lines)
#     return filtered_text

# filtered_output = filter_timestamps(output)

# original = timestamp_lines.splitlines()
# filtered = filtered_output.splitlines()

# for o, f in zip(original, filtered):
#     original_time = o.split(' ')[0]
#     filtered_time = f.split(' ')[0]
#     if not original_time == filtered_time:
#         raise RuntimeError(f"Timestamp mismatch - original timestamp '{original_time}' does not match LLM timestamp '{filtered_time}'")

# print(filtered_output)
# print("*"*100)


