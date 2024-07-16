import time
import os
import scrapetube
from pytube import YouTube
import vertexai
import tempfile
import logging
from google.cloud import storage
from vertexai.generative_models import GenerativeModel, Part
from pytube.innertube import _default_clients

_default_clients["ANDROID"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["IOS"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["ANDROID_EMBED"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["IOS_EMBED"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["IOS_MUSIC"]["context"]["client"]["clientVersion"] = "6.41"
_default_clients["ANDROID_MUSIC"] = _default_clients["ANDROID_CREATOR"]

GEMINI_PROJECT_ID = "abc"
GEMINI_LOCATION = "abc"
GCP_CREDENTIALS = "abc"
GEMINI_MODEL = "gemini-1.5-flash-001"
GCP_BUCKET_NAME = "abc"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCP_CREDENTIALS

# vertexai.init(project=GEMINI_PROJECT_ID, location=GEMINI_LOCATION)
# model = GenerativeModel(GEMINI_MODEL)

topic = 'Football Rules'
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

def DownloadAndUpload(link, bucket_name):
    youtubeObject = YouTube(link)
    stream = youtubeObject.streams.get_highest_resolution()
    video_id = youtubeObject.video_id
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp_file:
            stream.download(filename=tmp_file.name)
            # Upload to GCS
            blob_name = f"{video_id}.mp4"
            upload_to_gcs(bucket_name, blob_name, tmp_file.name)

        print(f"Download and upload completed successfully: {link}")
    except Exception as e:
        print(f"An error has occurred: {e}")
        logging.info(e)
        
def GenerateVideoDescription(video_file_uri):
    # project_id = "your-project-id"  # Replace with your project ID
    # vertexai.init(project='project_video-search-429010id', location="us-central1")

    try:
        vertexai.init(project=GEMINI_PROJECT_ID, location=GEMINI_LOCATION)

        model = GenerativeModel(model_name=GEMINI_MODEL)

        prompt = """
        Provide a description of the video.
        The description should also contain anything important which people say in the video.
        """

        video_file = Part.from_uri(video_file_uri, mime_type="video/mp4")

        contents = [video_file, prompt]

        response = model.generate_content(contents)
        print(response.text)
        logging.info(response.text)
    except Exception as e:
        logging.error(f"An error occurred while generating video description: {e}")

if __name__ == "__main__":
    video_ids = get_video_urls(topic, max_results)
    time.sleep(10)
    print(video_ids)
    for video_id in video_ids:
        link = f"https://www.youtube.com/watch?v={video_id}"
        print(link)
        DownloadAndUpload(link,GCP_BUCKET_NAME)
        video_file_uri = f"gs://{GCP_BUCKET_NAME}/{video_id}.mp4"
        GenerateVideoDescription(video_file_uri)
    while True:
        time.sleep(10)  # Keep the script running
