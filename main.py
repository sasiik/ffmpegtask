import argparse
import functools
import re
import subprocess
import json
import os
import shutil
import logging


def setup_logging(debug, logfile):
    level = logging.DEBUG if debug else logging.INFO
    if logfile:
        handlers = [logging.FileHandler("logfile.log"), logging.StreamHandler()]
    else:
        handlers = [logging.StreamHandler()]
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', handlers=handlers)


def rename_images(directory: str):
    files = sorted(os.listdir(directory), key=natural_sort_key)
    i = 0
    for file in files:
        if file.endswith(".jpg"):
            if not os.path.exists(os.path.join(directory, f"frame_renamed_{i}.jpg")):
                os.rename(
                    os.path.join(directory, file),
                    os.path.join(directory, f"frame_renamed_{i}.jpg")
                )
                i += 1


def setup_and_cleanup_directories(*dirs):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Setup: Create directories if they don't exist
            for directory in dirs:
                if not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)
                    logging.debug(f"Directory created: {directory}")
                else:
                    logging.debug(f"Directory already exists: {directory}")

            try:
                # Execute the function
                result = func(*args, **kwargs)
            finally:
                # Cleanup: Remove the directories after function execution
                for directory in dirs:
                    if os.path.exists(directory):
                        shutil.rmtree(directory)
                        logging.debug(f"Directory removed: {directory}")

            return result
        return wrapper
    return decorator

def run_command(command, wait_for_completion=True):
    """Execute a system command and optionally wait for it to complete."""
    if wait_for_completion:
        result = subprocess.run(
            command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        logging.info(f"Command:{command}, Result:{result.stderr}")
        print(result.stderr)
    else:
        process = subprocess.Popen(command, shell=True)
        return process


def slice_video(input_name: str, segment_length: int):
    """Slice the input video into segments of specified length and save to output folder."""
    command = f"ffmpeg -i {input_name} -reset_timestamps 1 -c copy -map 0 -segment_time {segment_length} -f segment slices/output_%d.mp4"
    run_command(command)


def extract_metadata(threshold: int) -> list:
    """Extract metadata from video segments and save as JSON files."""
    segment_files = get_segment_files('slices/')
    file_info_list = []
    for video_path in segment_files:
        json_file_name = os.path.basename(video_path)[:-4] + '_data.json'
        metadata_path = os.path.join(
            'metadatas/', json_file_name).replace('\\', '/')
        command = f"ffprobe -f lavfi -i \"movie='{video_path}',select='gt(scene,{threshold})',metadata=print\" " \
                  f"-show_entries frame=pts_time " \
                  f"-of json > {metadata_path}"
        run_command(command)
        file_info_list.append(
            {"video_path": video_path, "metadata_path": metadata_path})
    return file_info_list


def natural_sort_key(s, _nsre=re.compile('([0-9]+)')) -> list:
    return [int(text) if text.isdigit() else text.lower() for text in re.split(_nsre, s)]


def get_segment_files(input_folder: str):
    return sorted(
        [os.path.join(input_folder, f) for f in os.listdir(input_folder)],
        key=natural_sort_key
    )


def process_timestamps(file_info_list: list, batch_size: int, quality: int):

    if not 2 <= quality <= 31:
        raise ValueError(
            f"Quality number should be between 2 and 31, got {quality}")

    if not 1 <= batch_size <= 250:
        raise ValueError(
            f"Batch size should be between 1 and 250, got {batch_size}")

    """Process timestamps extracted from metadata files to generate images."""
    total_frames = 0

    for file_info in file_info_list:
        data = load_json_data(file_info['metadata_path'])
        timestamps = [frame['pts_time'] for frame in data['frames']]
        for i in range(0, len(timestamps), batch_size):
            batch_timestamps = timestamps[i:i+batch_size]
            tolerance = 0.00015
            select_filter = '+'.join(
                [f'between(t,{float(ts)-tolerance},{float(ts)+tolerance})' for ts in batch_timestamps])
            command = f"ffmpeg -i {file_info['video_path']} -vf \"select='{select_filter}'\" -start_number {total_frames} -vsync vfr -q:v {quality} images/frame_%d.jpg"
            total_frames += len(batch_timestamps)

            logging.info(
                f"Starting frame number for this batch: {total_frames}")
            run_command(command)

    logging.info('Images created based on timestamps')


def load_json_data(file_path: str):
    """Load and return JSON data from a file."""
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        logging.error(f"Error reading JSON file {file_path}: {str(e)}")
        raise


def check_output_validity(output_path):
    directory = os.path.dirname(output_path)

    # Create directory if it does not exist
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        logging.info(f"Created directory: {directory}")

    # Delete the file if it already exists
    if os.path.exists(output_path):
        os.remove(output_path)
        logging.info(f"Deleted existing file: {output_path}")

    return output_path


def create_video(output_path: str, framerate: int):
    if not 1 <= framerate <= 600:
        raise ValueError(f"Framerate should be between 1 and 600, got {framerate}")
    
    path_to_file = check_output_validity(output_path)
    rename_images('images/')

    command = f"ffmpeg -framerate {framerate} -i images/frame_renamed_%d.jpg -c:v libx264 -r {framerate} -pix_fmt yuv420p \"{path_to_file}\""
    run_command(command)
    logging.info("Video created at: " + path_to_file)


@setup_and_cleanup_directories("images/", 'slices/', "metadatas/")
def main():
    parser = argparse.ArgumentParser(description="Deletes idle timeframes from the video")
    
    # Add arguments
    parser.add_argument('-i', '--input', type=str, help='Path to the input file')
    parser.add_argument('-t', '--threshold', type=int, default=0.002, help='Increase/decrease sensitivity of the algoritm')
    parser.add_argument('-q', '--quality', type=int, default=16, help='Quailty of the video (number from 2 to 31)')
    parser.add_argument('--logfile', action='store_true', help='Creates a logfile in the script folder')
    parser.add_argument('-sl', '--segment_length', type=int, default=20, help='Length of each slice of the video (in sec)')
    parser.add_argument('-bs', '--batch_size', type=int, default=200, help="Size of the batch (1-250)")
    parser.add_argument('-o', '--output', type=str, default='result/out.mp4', help='Output file destination')
    parser.add_argument('-f', '--framerate', type=int, default=30, help="Framerate of the output video")
    parser.add_argument('--debug', action='store_true', help='Enable debug mode for verbose output.')
    
    
    # Parse arguments
    args = parser.parse_args()
    
    setup_logging(args.debug, args.logfile)
    slice_video(args.input, args.segment_length)
    file_info_list = extract_metadata(args.threshold)
    process_timestamps(file_info_list, args.batch_size, args.quality)
    create_video(args.output, args.framerate)


if __name__ == "__main__":
    main()
