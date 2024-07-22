import time
import re
import os
import scrapetube
from pytube import YouTube
import vertexai
from youtube_transcript_api import YouTubeTranscriptApi
import tempfile
import logging
from google.cloud import storage
from vertexai.generative_models import GenerativeModel, Part
import json
import ffmpeg_streaming
from ffmpeg_streaming import Formats, Bitrate, Representation, Size
# from moviepy.editor import *
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip



from pytube.innertube import _default_clients

_default_clients["ANDROID"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["IOS"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["ANDROID_EMBED"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["IOS_EMBED"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["IOS_MUSIC"]["context"]["client"]["clientVersion"] = "6.41"
_default_clients["ANDROID_MUSIC"] = _default_clients["ANDROID_CREATOR"]

GEMINI_PROJECT_ID = "video-search-429010"
GEMINI_LOCATION = "us-central1"
GCP_CREDENTIALS = "video-search-429010-f06b9a02b80f.json"
GEMINI_MODEL = "gemini-1.5-flash-001"
GCP_BUCKET_NAME = "video-search-1"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCP_CREDENTIALS

# vertexai.init(project=GEMINI_PROJECT_ID, location=GEMINI_LOCATION)
# model = GenerativeModel(GEMINI_MODEL)

topic = 'Ford Mustang Shelby'
max_results = 3

def get_video_urls(topic, max_results):
    videos = scrapetube.get_search(topic, max_results)
    video_ids = [video['videoId'] for video in videos]
    return video_ids

# def upload_blob(
#     proj_id, credentials, bucket_name, source_file_name, destination_blob_name
# ):
#     storage_client = storage.Client.from_service_account_json(credentials)
#     bucket = storage_client.bucket(bucket_name)
#     blob = bucket.blob(destination_blob_name)

#     # Optional: set a generation-match precondition to avoid potential race conditions
#     # and data corruptions. The request to upload is aborted if the object's
#     # generation number does not match your precondition. For a destination
#     # object that does not yet exist, set the if_generation_match precondition to 0.
#     # If the destination object already exists in your bucket, set instead a
#     # generation-match precondition using its generation number.
#     generation_match_precondition = 0

#     blob.upload_from_filename(
#         source_file_name,
#         # if_generation_match=generation_match_precondition
#     )

#     print(f"File {source_file_name} uploaded to {destination_blob_name}.")

#     return f"gs://{bucket_name}/{destination_blob_name}"


# def Download(link):
#     youtubeObject = YouTube(link)
#     youtubeObject = youtubeObject.streams.get_highest_resolution()
#     try:
#         youtubeObject.download()
#         print(f"Download completed successfully: {link}")
#     except Exception as e:
#         print(f"An error has occurred: {e}")
        
def upload_to_gcs(bucket_name, blob_name, file_path):
    storage_client = storage.Client.from_service_account_json(GCP_CREDENTIALS)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(file_path)
    logging.info(f"Uploaded to {bucket_name}/{blob_name}")

# def DownloadAndUpload(link, bucket_name):
#     youtubeObject = YouTube(link)
#     stream = youtubeObject.streams.get_highest_resolution()
#     video_id = youtubeObject.video_id
#     try:
#         with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp_file:
#             stream.download(filename=tmp_file.name)
#             # Upload to GCS
#             blob_name = f"{video_id}.mp4"
#             upload_to_gcs(bucket_name, blob_name, tmp_file.name)

#         print(f"Download and upload completed successfully: {link}")
#     except Exception as e:
#         print(f"An error has occurred: {e}")
#         logging.info(e)

def DownloadAndUpload(link, bucket_name):
    try:
        # Download transcript
        video_id = YouTube(link).video_id
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        
        if not transcript:
            logging.error(f"No transcript available for video: {video_id}")
            return None

        # Serialize transcript to JSON
        transcript_data = json.dumps(transcript, indent=2)

        # Upload to GCS
        blob_name = f"{video_id}_transcript.json"
        with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
            tmp_file.write(transcript_data.encode('utf-8'))
            tmp_file.flush()  # Ensure all data is written before uploading
            upload_to_gcs(bucket_name, blob_name, tmp_file.name)

        logging.info(f"Downloaded and uploaded transcript successfully for: {link}")
        return transcript
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        
# def GenerateVideoDescription(video_file_uri):
#     # project_id = "your-project-id"  # Replace with your project ID
#     # vertexai.init(project='project_video-search-429010id', location="us-central1")

#     try:
#         vertexai.init(project=GEMINI_PROJECT_ID, location=GEMINI_LOCATION)

#         model = GenerativeModel(model_name=GEMINI_MODEL)

#         prompt = """
#         Provide a description of the video.
#         The description should also contain anything important which people say in the video.
#         """

#         video_file = Part.from_uri(video_file_uri, mime_type="video/mp4")

#         contents = [video_file, prompt]

#         response = model.generate_content(contents)
#         print(response.text)
#         logging.info(response.text)
#     except Exception as e:
#         logging.error(f"An error occurred while generating video description: {e}")
        
def GenerateVideoDescription(transcript):
    try:
        vertexai.init(project=GEMINI_PROJECT_ID, location=GEMINI_LOCATION)

        model = GenerativeModel(model_name=GEMINI_MODEL)

        prompt = """
        Analyze the following transcript and provide the most interesting points and their timestamps where the range of each point sums to 45 seconds - 1 minute.
        Provide the 3 best points...each point should be 45 seconds- 1 minute
        Let it be in the format sl number. **title** newline "Start" : starttime newline "End": endtime make sure it is in that format no stars should be added in the answer
        """

        # transcript_file = Part.from_uri(transcript_file_uri, mime_type="application/json")
        
        transcript_text = "\n".join([f"{item['start']} - {item['text']}" for item in transcript])
        
        contents = [transcript_text, prompt]
        response = model.generate_content(contents)
        
        if not response:
            logging.error(f"No transcript available for video: {video_id}")
            return None
        
        print(response.text)
        logging.info(response.text)
        return response.text
    except Exception as e:
        logging.error(f"An error occurred while generating video description: {e}")

def trim_video(video_path, start_time, end_time, output_path):
    try:
        logging.info(f"Trimming video from {start_time} to {end_time}")
        ffmpeg_extract_subclip(video_path, start_time, end_time, targetname=output_path)
        logging.info(f"Trimmed video from {start_time} to {end_time} and saved to {output_path}")
    except Exception as e:
        logging.error(f"An error occurred while trimming the video: {e}")
        
def convert_to_hls(video_path, output_dir):
    try:
        _360p  = Representation(Size(640, 360), Bitrate(276 * 1024, 128 * 1024))
        _480p  = Representation(Size(854, 480), Bitrate(750 * 1024, 192 * 1024))
        _720p  = Representation(Size(1280, 720), Bitrate(2048 * 1024, 320 * 1024))

        video = ffmpeg_streaming.input(video_path)
        hls = video.hls(Formats.h264())
        hls.representations(_360p, _480p, _720p)

        hls_output_path = os.path.join(output_dir, "hls.m3u8")
        hls.output(hls_output_path)

        logging.info(f"Converted video to HLS segments in directory: {output_dir}")
        return hls_output_path
    except Exception as e:
        logging.error(f"An error occurred while converting the video to HLS: {e}")
        return None

def process_video_point(video_id, title, start, end, bucket_name):
    try:
        link = f"https://www.youtube.com/watch?v={video_id}"
        youtubeObject = YouTube(link)
        stream = youtubeObject.streams.get_highest_resolution()
        
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            video_path = tmp_file.name
            logging.info(f"Downloading video to temporary file: {video_path}")
            stream.download(filename=video_path)
            logging.info("Video download completed.")
            
            # Trim the video based on the interesting points
            output_path = os.path.join(tempfile.gettempdir(), f"{title}_trimmed_{int(start)}_{int(end)}.mp4")
            logging.info(f"Trimming video and saving to: {output_path}")
            trim_video(video_path, start, end, output_path)
            logging.info("Video trimming completed.")
            
            # # Upload the trimmed video to GCS
            # blob_name = f"{title}_trimmed_{int(start)}_{int(end)}.mp4"
            # logging.info(f"Uploading trimmed video to GCS: {bucket_name}/{blob_name}")
            # upload_to_gcs(bucket_name, blob_name, output_path)
            # logging.info("Trimmed video upload completed.")
            
            # # Clean up the temporary video file
            # os.remove(video_path)
            # logging.info("Temporary video file removed.")
            trimmed_blob_name = f"{title}_trimmed_{int(start)}_{int(end)}.mp4"
            upload_to_gcs(bucket_name, trimmed_blob_name, output_path)
            
            with tempfile.TemporaryDirectory() as tmp_dir:
                logging.info(f"Converting trimmed video to HLS segments in: {tmp_dir}")
                hls_output_path = convert_to_hls(output_path, tmp_dir)
                if hls_output_path:
                    logging.info("Video conversion to HLS completed.")
                    for segment in os.listdir(tmp_dir):
                        segment_path = os.path.join(tmp_dir, segment)
                        blob_name = f"{title}_trimmed_{int(start)}_{int(end)}/{segment}"
                        logging.info(f"Uploading HLS segment to GCS: {bucket_name}/{blob_name}")
                        upload_to_gcs(bucket_name, blob_name, segment_path)
                        logging.info("HLS segment upload completed.")
            
            os.remove(video_path)
            logging.info("Temporary video file removed.")
            os.remove(output_path)
            logging.info("Temporary trimmed video file removed.")
    
    except Exception as e:
        logging.error(f"An error occurred while processing the point: {e}")

def extract_timestamps(video_id, text):
    points = []
    pattern = r"\*\*(.*?)\*\*\s*\"Start\":\s*(\d+\.\d+)\s*\"End\":\s*(\d+\.\d+)"
    matches = re.findall(pattern, text, re.DOTALL)
    
    for match in matches:
        title = match[0].strip()
        start = float(match[1])
        end = float(match[2])
        points.append((video_id, title, start, end))
    
    return points
        
if __name__ == "__main__":
    video_ids = get_video_urls(topic, max_results)
    print(video_ids)
    for video_id in video_ids:
        link = f"https://www.youtube.com/watch?v={video_id}"
        print(link)
        transcript = DownloadAndUpload(link,GCP_BUCKET_NAME)
        all_points = []
        if transcript:
            print("Entering the transcript processing block")
            response = GenerateVideoDescription(transcript)
            if response:
                point = extract_timestamps(video_id, response)
                # print(points)
                for video_id, title, start, end in point:
                    try:
                        print("process_video block")
                        process_video_point(video_id, title, start, end, GCP_BUCKET_NAME)
                    except Exception as e:
                        logging.error(f"One error occurred while processing the point: {e}")
            else:
                print("No response from model, skipping to next video")
        else:
            print("Transcript is None, skipping to next video")
        
    # while True:
    #     time.sleep(1)  # Keep the script running
