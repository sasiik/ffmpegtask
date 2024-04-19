import re
import subprocess
import json
import os
import shutil
import logging

def setup_logging():
    logging.basicConfig(level=logging.DEBUG, 
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        handlers=[
                            logging.FileHandler("logfile.log"),  
                            logging.StreamHandler()  
                        ])
    
def rename_images(directory):
    files = sorted(os.listdir(directory), key=natural_sort_key)
    i = 0  # Start numbering from 1
    for file in files:
        if file.endswith(".jpg"):
            if not os.path.exists(os.path.join(directory, f"frame_renamed_{i}.jpg")):
                os.rename(
                    os.path.join(directory, file),
                    os.path.join(directory, f"frame_renamed_{i}.jpg")
                )
                i += 1

def clear_directory(folder):
    """Remove all files and directories in the specified folder and recreate it."""
    try:
        if os.path.exists(folder):
            shutil.rmtree(folder)
        os.makedirs(folder, exist_ok=True)
        logging.info(f"Directory cleared and recreated: {folder}")
    except Exception as e:
        logging.error(f"Failed to clear and recreate directory {folder}: {str(e)}")
        raise
    
def delete_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)

def run_command(command, wait_for_completion=True):
    """Execute a system command and optionally wait for it to complete."""
    if wait_for_completion:
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        logging.info(f"Command:{command}, Result:{result.stderr}")
        print(result.stderr)
    else:
        process = subprocess.Popen(command, shell=True)
        return process


def slice_video(input_name, segment_length=20, output_folder='slices/'):
    """Slice the input video into segments of specified length and save to output folder."""
    clear_directory(output_folder)
    command = f"ffmpeg -i {input_name} -reset_timestamps 1 -c copy -map 0 -segment_time {segment_length} -f segment {output_folder}output_%d.mp4"
    run_command(command)

def extract_metadata(input_folder, output_folder, threshold=0.0025):
    """Extract metadata from video segments and save as JSON files."""
    clear_directory(output_folder)
    segment_files = get_segment_files(input_folder)
    file_info_list = []
    for video_path in segment_files:
        json_file_name = os.path.basename(video_path)[:-4] + '_data.json' 
        metadata_path = os.path.join(output_folder, json_file_name).replace('\\', '/')
        command = f"ffprobe -f lavfi -i \"movie='{video_path}',select='gt(scene,{threshold})',metadata=print\" " \
                  f"-show_entries frame=pts_time " \
                  f"-of json > {metadata_path}"
        run_command(command)
        file_info_list.append({"video_path": video_path, "metadata_path": metadata_path})
    return file_info_list

def natural_sort_key(s, _nsre=re.compile('([0-9]+)')):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(_nsre, s)]

def get_segment_files(input_folder):
    # This assumes all video files in the directory are relevant
    return sorted(
        [os.path.join(input_folder, f) for f in os.listdir(input_folder)],
        key=natural_sort_key
    )

def process_timestamps(file_info_list, images_dir='images/', debug=False):
    """Process timestamps extracted from metadata files to generate images."""
    clear_directory(images_dir)
    total_frames = 0 

    for file_info in file_info_list:
        data = load_json_data(file_info['metadata_path'])
        timestamps = [frame['pts_time'] for frame in data['frames']]
        batch_size = 200
        for i in range(0, len(timestamps), batch_size):
            batch_timestamps = timestamps[i:i+batch_size]
            tolerance = 0.00015
            select_filter = '+'.join([f'between(t,{float(ts)-tolerance},{float(ts)+tolerance})' for ts in batch_timestamps])
            
            if debug:
                command = f"ffmpeg -i {file_info['video_path']} -vf \"showinfo\" -f null -"
            else:
                command = f"ffmpeg -i {file_info['video_path']} -vf \"select='{select_filter}'\" -start_number {total_frames} -vsync vfr -q:v 16 {images_dir}/frame_%d.jpg"
                total_frames += len(batch_timestamps)
            logging.info(f"Starting frame number for this batch: {total_frames}")
            run_command(command)

    logging.info('Images created based on timestamps')



def load_json_data(file_path):
    """Load and return JSON data from a file."""
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        logging.error(f"Error reading JSON file {file_path}: {str(e)}")
        raise

def create_video(source_folder, output_file="out.mp4"):
    rename_images('images/')
    """Create a video from images located in a specified folder."""
    delete_file(output_file)
    command = f"ffmpeg -framerate 30 -i {source_folder}frame_renamed_%d.jpg -c:v libx264 -r 30 -pix_fmt yuv420p {output_file}"
    run_command(command)
    logging.info("Video is created.")

def main():
    setup_logging()
    input_name = "input.mp4"
    slice_video(input_name)
    file_info_list = extract_metadata('slices/', 'metadatas/')
    process_timestamps(file_info_list, debug=False)
    create_video('images/')

if __name__ == "__main__":
    main()
