import os
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, simpledialog
import threading
import time
import main  # Assuming main.py contains updated backend logic for Outlook, round-robin, etc.

# GUI Functions to interact with backend (`main.py`)

# Function to add a new request from GUI
def add_request():
    title = entry.get().strip()
    if not title:
        messagebox.showwarning("Input Error", "Please enter a title to add.")
        return

    result_message = main.add_request(title)
    scrolled_text.insert(tk.END, f"{result_message}\n")
    entry.delete(0, tk.END)
    update_request_lists()

# Function to delete selected items from request lists
def delete_selected_items():
    for title, var in {**movies_checkboxes, **tv_shows_checkboxes, **music_checkboxes}.items():
        if var.get():
            if title in movies_checkboxes:
                main.delete_request(title, main.FILMS_LIST_PATH)
            elif title in tv_shows_checkboxes:
                main.delete_request(title, main.TV_SHOWS_LIST_PATH)
            elif title in music_checkboxes:
                main.delete_request(title, main.MUSIC_LIST_PATH)
    update_request_lists()

# Function to edit selected item from request lists
def edit_selected_item():
    selected_items = [(title, var) for title, var in {**movies_checkboxes, **tv_shows_checkboxes, **music_checkboxes}.items() if var.get()]
    
    if len(selected_items) != 1:
        messagebox.showwarning("Selection Error", "Please select exactly one item to edit.")
        return

    title, var = selected_items[0]
    new_title = simpledialog.askstring("Edit Item", f"Edit title for '{title}':")
    if new_title:
        # Replace the old title with the new title
        if title in movies_checkboxes:
            main.delete_request(title, main.FILMS_LIST_PATH)
            main.add_request(new_title)
        elif title in tv_shows_checkboxes:
            main.delete_request(title, main.TV_SHOWS_LIST_PATH)
            main.add_request(new_title)
        elif title in music_checkboxes:
            main.delete_request(title, main.MUSIC_LIST_PATH)
            main.add_request(new_title)
        update_request_lists()

# Function to update request lists
def update_request_lists():
    # Clear previous checkboxes
    for widget in movies_scrollable_frame.winfo_children():
        widget.destroy()
    for widget in tv_scrollable_frame.winfo_children():
        widget.destroy()
    for widget in music_scrollable_frame.winfo_children():
        widget.destroy()

    # Load request lists from `main.py`
    movies, tv_shows, music = main.get_request_lists()

    # Create checkboxes for movies
    global movies_checkboxes
    movies_checkboxes = {}
    for movie in movies:
        var = tk.BooleanVar()
        checkbox = tk.Checkbutton(movies_scrollable_frame, text=movie, variable=var, bg="#f0f0f0", anchor="w")
        checkbox.pack(fill='x', padx=5, pady=2, anchor='w')
        movies_checkboxes[movie] = var

    # Create checkboxes for TV shows
    global tv_shows_checkboxes
    tv_shows_checkboxes = {}
    for tv_show in tv_shows:
        var = tk.BooleanVar()
        checkbox = tk.Checkbutton(tv_scrollable_frame, text=tv_show, variable=var, bg="#f0f0f0", anchor="w")
        checkbox.pack(fill='x', padx=5, pady=2, anchor='w')
        tv_shows_checkboxes[tv_show] = var

    # Create Checkboxes for Music
    global music_checkboxes
    music_checkboxes = {}
    for song in music:
        var = tk.BooleanVar()
        checkbox = tk.Checkbutton(music_scrollable_frame, text=song, variable=var, bg="#f0f0f0", anchor="w")
        checkbox.pack(fill='x', padx=5, pady=2, anchor='w')
        music_checkboxes[song] = var

# Function to display current downloads in the GUI
def update_current_downloads():
    while True:
        try:
            download_info = main.get_current_downloads()
            downloads_text.config(state=tk.NORMAL)
            downloads_text.delete(1.0, tk.END)
            downloads_text.insert(tk.END, "Current Downloads:\n")
            for info in download_info:
                downloads_text.insert(tk.END, f"{info}\n")
            downloads_text.config(state=tk.DISABLED)
        except Exception as e:
            downloads_text.insert(tk.END, f"Error fetching current downloads: {e}\n")
        time.sleep(10)  # Update every 10 seconds

# Updated function to display messages from Outlook
def display_outlook_messages():
    while True:
        try:
            messages = main.get_outlook_messages()  # Updated to call the Outlook function in main.py
            messages_text.config(state=tk.NORMAL)
            messages_text.delete(1.0, tk.END)
            messages_text.insert(tk.END, "Messages from Outlook:\n")
            for message in messages:
                messages_text.insert(tk.END, f"{message}\n")
            messages_text.config(state=tk.DISABLED)
        except Exception as e:
            messages_text.insert(tk.END, f"Error fetching messages from Outlook: {e}\n")
        time.sleep(60)

# Function to update the next item in queue
def update_next_in_queue():
    while True:
        try:
            movies, tv_shows, music = main.get_request_lists()

            # Determine the next item in the queue
            next_item = "None"
            if movies:
                next_item = f"{movies[0]} - Movie"
            elif tv_shows:
                next_item = f"{tv_shows[0]} - TV Show"
            elif music:
                next_item = f"{music[0]} - Music"

            # Update the label with the next item
            next_item_label.config(text=f"Next in Queue: {next_item}")

        except FileNotFoundError:
            next_item_label.config(text="Next in Queue: None")
        except Exception as e:
            next_item_label.config(text=f"Error: {e}")

        time.sleep(10)  # Update every 10 seconds

# GUI Setup
root = tk.Tk()
root.title("PhantomFetch")
root.geometry("1000x800")
root.configure(bg="#f0f0f0")

# Set up entry frame and add button
frame = tk.Frame(root, bg="#f0f0f0")
frame.pack(pady=10)

entry_label = ttk.Label(frame, text="Enter Title:")
entry_label.pack(side=tk.LEFT, padx=5)

entry = ttk.Entry(frame, width=50)
entry.pack(side=tk.LEFT, padx=10)

add_button = ttk.Button(frame, text="Add Request", command=add_request)
add_button.pack(side=tk.LEFT)

# Feedback Text for Added Requests
scrolled_text = scrolledtext.ScrolledText(frame, width=80, height=4, wrap=tk.WORD)
scrolled_text.pack(pady=5)

# Section to display the current downloads
downloads_frame = tk.LabelFrame(root, text="Current Downloads", padx=10, pady=10, bg="#f0f0f0")
downloads_frame.pack(fill="both", expand="yes", padx=20, pady=10)
downloads_text = scrolledtext.ScrolledText(downloads_frame, width=80, height=8, wrap=tk.WORD)
downloads_text.pack()

# Section to display messages from Outlook
teams_frame = tk.LabelFrame(root, text="Messages from Outlook", padx=10, pady=10, bg="#f0f0f0")
teams_frame.pack(fill="both", expand="yes", padx=20, pady=10)
messages_text = scrolledtext.ScrolledText(teams_frame, width=80, height=8, wrap=tk.WORD)
messages_text.pack()

# Section to display the next item in the download queue
queue_frame = tk.Frame(root, bg="#f0f0f0")
queue_frame.pack(pady=20)
next_item_label = ttk.Label(queue_frame, text="Next in Queue: None", font=("Helvetica", 14, "bold"))
next_item_label.pack()

# Request Lists Section for Movies, TV, and Music
request_lists_frame = tk.LabelFrame(root, text="Request Lists", padx=10, pady=10, bg="#f0f0f0")
request_lists_frame.pack(fill="both", expand="yes", padx=20, pady=10)

# Movies, TV Shows, and Music frames with checkboxes
movies_frame = tk.Frame(request_lists_frame, bg="#f0f0f0")
movies_frame.pack(side=tk.LEFT, fill="y", padx=10)

movies_label = ttk.Label(movies_frame, text="Movies Requests:")
movies_label.pack()

movies_canvas = tk.Canvas(movies_frame, bg="#f0f0f0")
movies_scrollbar = ttk.Scrollbar(movies_frame, orient="vertical", command=movies_canvas.yview)
movies_scrollable_frame = tk.Frame(movies_canvas, bg="#f0f0f0")

movies_scrollable_frame.bind(
    "<Configure>",
    lambda e: movies_canvas.configure(
        scrollregion=movies_canvas.bbox("all")
    )
)

movies_canvas.create_window((0, 0), window=movies_scrollable_frame, anchor="nw")
movies_canvas.configure(yscrollcommand=movies_scrollbar.set)

movies_canvas.pack(side="left", fill="both", expand=True)
movies_scrollbar.pack(side="right", fill="y")

tv_shows_frame = tk.Frame(request_lists_frame, bg="#f0f0f0")
tv_shows_frame.pack(side=tk.LEFT, fill="y", padx=10)

tv_shows_label = ttk.Label(tv_shows_frame, text="TV Shows Requests:")
tv_shows_label.pack()

tv_canvas = tk.Canvas(tv_shows_frame, bg="#f0f0f0")
tv_scrollbar = ttk.Scrollbar(tv_shows_frame, orient="vertical", command=tv_canvas.yview)
tv_scrollable_frame = tk.Frame(tv_canvas, bg="#f0f0f0")

tv_scrollable_frame.bind(
    "<Configure>",
    lambda e: tv_canvas.configure(
        scrollregion=tv_canvas.bbox("all")
    )
)

tv_canvas.create_window((0, 0), window=tv_scrollable_frame, anchor="nw")
tv_canvas.configure(yscrollcommand=tv_scrollbar.set)

tv_canvas.pack(side="left", fill="both", expand=True)
tv_scrollbar.pack(side="right", fill="y")

music_frame = tk.Frame(request_lists_frame, bg="#f0f0f0")
music_frame.pack(side=tk.LEFT, fill="y", padx=10)

music_label = ttk.Label(music_frame, text="Music Requests:")
music_label.pack()

music_canvas = tk.Canvas(music_frame, bg="#f0f0f0")
music_scrollbar = ttk.Scrollbar(music_frame, orient="vertical", command=music_canvas.yview)
music_scrollable_frame = tk.Frame(music_canvas, bg="#f0f0f0")

music_scrollable_frame.bind(
    "<Configure>",
    lambda e: music_canvas.configure(
        scrollregion=music_canvas.bbox("all")
    )
)

music_canvas.create_window((0, 0), window=music_scrollable_frame, anchor="nw")
music_canvas.configure(yscrollcommand=music_scrollbar.set)

music_canvas.pack(side="left", fill="both", expand=True)
music_scrollbar.pack(side="right", fill="y")

# Initialize and start GUI update threads
update_request_lists()
download_thread = threading.Thread(target=update_current_downloads, daemon=True)
download_thread.start()
outlook_thread = threading.Thread(target=display_outlook_messages, daemon=True)
outlook_thread.start()
queue_thread = threading.Thread(target=update_next_in_queue, daemon=True)
queue_thread.start()

root.mainloop()
