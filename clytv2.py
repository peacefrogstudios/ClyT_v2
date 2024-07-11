import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, PhotoImage
from threading import Thread
from pytube import YouTube
from moviepy.audio.io.AudioFileClip import AudioFileClip
import requests
from bs4 import BeautifulSoup
import re
import os
#from PIL import Image, ImageTk  # To make user icon show on top left

individual_download_index = 0
batch_download_index = 0
batch_file_path = None
active_threads = []


def browse_directory():
    directory = filedialog.askdirectory()
    if directory:
        output_entry.delete(0, tk.END)
        output_entry.insert(0, directory)

def start_download(event=None):
    if batch_file_path:
        process_batch_download(batch_file_path)
    else:
        url = url_entry.get()
        output_dir = output_entry.get()
        custom_name = custom_name_entry.get().strip()

        if not url:
            messagebox.showerror("Error", "Please enter a valid YouTube URL.")
            return

        if not output_dir or not os.path.exists(output_dir):
            messagebox.showerror("Error", "Please select a valid output directory.")
            return

        format_selected = format_var.get()

        if not format_selected:
            messagebox.showerror("Error", "Please select a format (MP3 or MP4).")
            return

        download_button.config(state=tk.DISABLED)
        Thread(target=download_video, args=(url, output_dir, custom_name, format_selected)).start()

def log_individual_download(title, format_selected):
    global individual_download_index
    individual_download_index += 1
    line_index = "1.0"
    track_log.insert(line_index, f"{individual_download_index}. {title}.{format_selected}\n")
    track_log.see(line_index)
    return line_index

def log_download_status(title, status, line_index=None, format_selected=None):
    global batch_download_index
    if line_index is None:
        batch_download_index += 1
        line_index = "1.0"
        track_log.insert(line_index, f"{batch_download_index}. {title}\n")
        if format_selected == "mp4":
            track_log.tag_add("mp4", line_index, f"{line_index} lineend")
        track_log.see(line_index)
        return line_index
    else:
        current_text = track_log.get(line_index, f"{line_index} lineend")
        match = re.match(r"(\d+)\.", current_text)
        if match:
            number = match.group(1)
            new_text = f"{number}. {title}"
            track_log.delete(line_index, f"{line_index} lineend")
            track_log.insert(line_index, new_text)
            track_log.tag_add("completed", line_index, f"{line_index} lineend")
            if "mp4" in new_text:
                track_log.tag_add("mp4", line_index, f"{line_index} lineend")
            track_log.see(line_index)

def download_video(url, output_dir, custom_name, format_selected, is_batch=False):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        video_title = soup.find('title').get_text().strip()

        video_title = re.sub(r'[\\/*?:"<>|]', '', video_title)
        video_title = re.sub(r' - YouTube$', '', video_title)

        if custom_name:
            custom_name = re.sub(r'\.[^.]*$', '', custom_name).rstrip('.')
            video_title_with_format = f"{custom_name}.{format_selected}"
        else:
            video_title_with_format = f"{video_title}.{format_selected}"

        youtube = YouTube(url)
        if format_selected == "mp3":
            video = youtube.streams.get_audio_only()
            temp_video_filepath = os.path.join(output_dir, f"{video_title}_temp.mp4")
            output_file_path = os.path.join(output_dir, video_title_with_format)
        elif format_selected == "mp4":
            video = youtube.streams.get_highest_resolution()
            output_file_path = os.path.join(output_dir, video_title_with_format)

        if os.path.exists(output_file_path):
            messagebox.showerror("Error", f"File already exists at \"{output_file_path}\".")
            download_button.config(state=tk.NORMAL)
            return

        if not is_batch:
            line_index = log_individual_download(video_title, format_selected)
        if format_selected == "mp3":
            out_video_filepath = video.download(output_dir, filename=f"{video_title}_temp.mp4")
            moviepy_audio_clip = AudioFileClip(out_video_filepath)
            moviepy_audio_clip.write_audiofile(output_file_path, verbose=False, logger=None)
            moviepy_audio_clip.close()
            os.remove(out_video_filepath)
        else:
            out_video_filepath = video.download(output_dir, filename=video_title_with_format)
            if not out_video_filepath.endswith('.mp4'):
                os.rename(out_video_filepath, out_video_filepath + '.mp4')

        if not is_batch:
            log_download_status(video_title_with_format, "Completed", line_index, format_selected)
        
        # Write to download list only if it is a batch download
        write_download_list(output_dir, video_title_with_format, is_batch)
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to download: {str(e)}")
    finally:
        download_button.config(state=tk.NORMAL)
        if is_batch:
            active_threads.remove(Thread.current_thread())


def upload_batch_file():
    global batch_file_path
    batch_file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    if batch_file_path:
        url_entry.delete(0, tk.END)
        url_entry.insert(0, batch_file_path)
        
        # Check which format is selected based on the format_var
        selected_format = format_var.get()
        if selected_format != "mp3" and selected_format != "mp4":
            format_var.set("mp3")  # Default to MP3 if neither is selected
        
        custom_name_entry.config(state=tk.DISABLED)

def clear_batch():
    global batch_file_path
    batch_file_path = None
    url_entry.delete(0, tk.END)
    custom_name_entry.config(state=tk.NORMAL)
    format_var.set("mp3")  # Reset to MP3 when clearing batch

def process_batch_download(batch_file_path):
    global batch_download_index, active_threads
    with open(batch_file_path, 'r') as file:
        urls = file.read().splitlines()

    output_dir = output_entry.get()

    if not output_dir or not os.path.exists(output_dir):
        messagebox.showerror("Error", "Please select a valid output directory.")
        return

    if format_var.get() == "mp3" and any(file.endswith('.mp3') for file in os.listdir(output_dir)):
        messagebox.showerror("Error", "Output directory must not contain existing MP3 files for batch MP3 downloads.")
        return

    if format_var.get() == "mp4" and any(file.endswith('.mp4') for file in os.listdir(output_dir)):
        messagebox.showerror("Error", "Output directory must not contain existing MP4 files for batch MP4 downloads.")
        return

    if os.listdir(output_dir):
        messagebox.showerror("Error", "Please select an empty output directory for batch download.")
        return

    download_button.config(state=tk.DISABLED)
    active_threads = []
    for url in urls:
        thread = Thread(target=download_video, args=(url, output_dir, '', format_var.get(), True))
        active_threads.append(thread)
        thread.start()

    # Check if batch download is complete every 100ms
    root.after(100, check_batch_download_complete)

def check_batch_download_complete():
    if not any(thread.is_alive() for thread in active_threads):
        global batch_download_index
        batch_download_index = 0
        download_button.config(state=tk.NORMAL)
    else:
        root.after(100, check_batch_download_complete)

def get_download_count(output_dir):
    downloads_list_path = os.path.join(output_dir, "downloads_list.txt")
    if os.path.exists(downloads_list_path):
        with open(downloads_list_path, "r") as f:
            return len(f.readlines())
    return 0

def write_download_list(output_dir, video_title_with_format, is_batch):
    if not is_batch:
        return

    download_list_path = os.path.join(output_dir, "downloads_list.txt")
    global batch_download_index
    batch_download_index += 1
    with open(download_list_path, "a") as file:
        file.write(f"{batch_download_index}. {video_title_with_format}\n")
        
def reset_fields():
    url_entry.delete(0, tk.END)
    custom_name_entry.delete(0, tk.END)
    output_entry.delete(0, tk.END)
    format_var.set("mp3")  # Reset format selection to MP3
    track_log.delete(1.0, tk.END)  # Clear songs downloaded box
    
    global individual_download_index
    individual_download_index = 0  # Reset individual download index counter to 0

#################################### GUI PART ####################################

# Set up the main application window
root = tk.Tk()
root.title("CLyT [v2.0.0] - YouTube Downloader for DJs")  
root.iconbitmap('smally.ico') # Line commented for exe creation. Uncomment if you want to run .py file. 

# YouTube URL input
tk.Label(root, text="YouTube URL:").grid(row=0, column=0, padx=(10, 0), pady=10)
url_entry = tk.Entry(root, width=53)
url_entry.grid(row=0, column=1, padx=(10, 0), pady=10, sticky='w')

# Bind the Enter key to the URL entry field
url_entry.bind("<Return>", start_download)

# Upload batch file button
upload_button = tk.Button(root, text="Get Batch", width=10, command=upload_batch_file)
upload_button.grid(row=0, column=2, padx=(5, 10), pady=10, sticky='w')

# Custom file name input
tk.Label(root, text="File Name:").grid(row=1, column=0, padx=(10, 0), pady=10)
custom_name_entry = tk.Entry(root, width=53)
custom_name_entry.grid(row=1, column=1, padx=(10, 0), pady=10, sticky='w')

# Bind the Enter key to the custom name entry field
custom_name_entry.bind("<Return>", start_download)

# Clear batch button
clear_button = tk.Button(root, text="Clear Batch", width=10, command=clear_batch)
clear_button.grid(row=1, column=2, padx=(5, 10), pady=10, sticky='w')

# Format selection
format_var = tk.StringVar(value="mp3")
mp3_radio = tk.Radiobutton(root, text="MP3", variable=format_var, value="mp3")
mp3_radio.grid(row=2, column=1, padx=(10, 0), pady=5, sticky='w')
mp4_radio = tk.Radiobutton(root, text="MP4", variable=format_var, value="mp4")
mp4_radio.grid(row=2, column=1, padx=(70, 0), pady=5, sticky='w')

# Output directory input
tk.Label(root, text="Output Folder:").grid(row=3, column=0, padx=(10, 0), pady=10)
output_entry = tk.Entry(root, width=53)
output_entry.grid(row=3, column=1, padx=(10, 0), pady=10, sticky='w')
browse_button = tk.Button(root, text="Browse", width=10, command=browse_directory)
browse_button.grid(row=3, column=2, padx=(5, 10), pady=10, sticky='w')

# Download button
download_button = tk.Button(root, text="Download", command=start_download)
download_button.grid(row=4, column=0, columnspan=3, pady=10)

# Space for DJ features
additional_frame = tk.Frame(root)
additional_frame.grid(row=5, column=0, columnspan=3, pady=5, sticky='nsew')

# Reset button
reset_button = tk.Button(root, text="Clear All", command=reset_fields)
reset_button.grid(row=4, column=2, padx=(5, 10), pady=10, sticky='nsew')

# Log of downloaded tracks (left half)
left_frame = tk.Frame(additional_frame)
left_frame.grid(row=0, column=0, padx=(5, 2), pady=5, sticky='nsew')

track_log_label = tk.Label(left_frame, text=f"Songs Downloaded")
track_log_label.pack(side=tk.TOP, padx=2, pady=5)

track_log_frame = tk.Frame(left_frame)
track_log_frame.pack(fill=tk.BOTH, expand=True)

track_log = tk.Text(track_log_frame, wrap=tk.NONE, height=10, width=29)
track_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Create vertical scrollbar for track_log
track_log_scrollbar_y = tk.Scrollbar(track_log_frame, command=track_log.yview)
track_log_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

# Link scrollbar to track_log
track_log.config(yscrollcommand=track_log_scrollbar_y.set)

# Define the tag for the MP4 color
track_log.tag_config("mp4", foreground="#1E90FF")  # Light blue color for MP4
track_log.tag_config("completed", font=("TkDefaultFont", 9, "bold"))

# Song request area (right half)
right_frame = tk.Frame(additional_frame)
right_frame.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')

song_request_label = tk.Label(right_frame, text="Songs Requested")
song_request_label.pack(side=tk.TOP, padx=2, pady=5)

# Create a Text widget for song_request_text with vertical scrollbar
song_request_text = scrolledtext.ScrolledText(right_frame, wrap=tk.NONE, height=10, width=29)
song_request_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Configure grid weights
root.grid_rowconfigure(5, weight=1)
root.grid_columnconfigure(1, weight=1)
additional_frame.grid_columnconfigure(0, weight=1)
additional_frame.grid_columnconfigure(1, weight=1)
additional_frame.grid_rowconfigure(0, weight=1)
left_frame.grid_rowconfigure(0, weight=1)
left_frame.grid_columnconfigure(0, weight=1)
right_frame.grid_rowconfigure(0, weight=1)
right_frame.grid_columnconfigure(0, weight=1)

# Start the main tkinter loop
root.mainloop()
