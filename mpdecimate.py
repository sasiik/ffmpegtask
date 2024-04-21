import os
import subprocess
import argparse
import sys


def process_video(input_file, output_file,is_interpolate,fps):
    """
    Process the given video to remove redundant frames using ffmpeg's mpdecimate filter.
    
    Args:
    input_file (str): Path to the input video file.
    output_file (str): Path to the output video file.
    """
    if is_interpolate:
        exec = f"mpdecimate,setpts=N/FRAME_RATE/TB,minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps={fps}'"
    else:
        exec = "mpdecimate,setpts=N/FRAME_RATE/TB"
    command = [
        'ffmpeg',
        '-i', input_file,
        '-vf', exec,
        '-an',  
        output_file
    ]

    try:
        # Execute the ffmpeg command
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.stderr:
            print("FFmpeg Info:", result.stderr)
    except Exception as e:
        print("Failed to process video:", str(e))
        sys.exit(1)

def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="Remove redundant frames from a video using ffmpeg's mpdecimate filter.")
    parser.add_argument('input_file', type=str, help='Path to the input video file.')
    parser.add_argument('output_file', type=str, help='Path to the output video file.')
    parser.add_argument('--interpolate', action="store_true", help='Interpolate the video. Slows the process but results in a higher FPS number')
    parser.add_argument('-f', '--fps', type=int, default=30, help="Desired fps of the video. Works only with interpolation parameter")
    
    args = parser.parse_args()
    
    if os.path.exists(args.output_file):
        os.remove(args.output_file)
        print(f"Deleted existing file: {args.output_file}")

    # Process the video with the given arguments
    process_video(args.input_file, args.output_file, args.interpolate, args.fps)

if __name__ == "__main__":
    main()
