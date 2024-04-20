import subprocess
import argparse
import sys

def process_video(input_file, output_file):
    """
    Process the given video to remove redundant frames using ffmpeg's mpdecimate filter.
    
    Args:
    input_file (str): Path to the input video file.
    output_file (str): Path to the output video file.
    """
    command = [
        'ffmpeg',
        '-i', input_file,
        '-vf', 'mpdecimate,setpts=N/FRAME_RATE/TB',
        '-an',  # Remove audio
        output_file
    ]

    try:
        # Execute the ffmpeg command
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.stderr:
            print("FFmpeg Info:", result.stderr)
        print("Video processed successfully. Output saved to:", output_file)
    except Exception as e:
        print("Failed to process video:", str(e))
        sys.exit(1)

def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="Remove redundant frames from a video using ffmpeg's mpdecimate filter.")
    parser.add_argument('input_file', type=str, help='Path to the input video file.')
    parser.add_argument('output_file', type=str, help='Path to the output video file.')

    args = parser.parse_args()

    # Process the video with the given arguments
    process_video(args.input_file, args.output_file)

if __name__ == "__main__":
    main()
