import tkinter as tk
from tkinter import filedialog

class FileDialog:
    def __init__(self, initial_dir="C:/Users/mathe/Documents"):
        self.initial_dir = initial_dir

    def select_json_file(self):
        root = tk.Tk()
        root.withdraw()  # Hide the main tkinter window
        file_path = filedialog.askopenfilename(
            title="Select a JSON file",
            filetypes=[("JSON files", "*.json")],
            initialdir=self.initial_dir
        )
        return file_path

if __name__ == "__main__":
    file_dialog = FileDialog()
    selected_file = file_dialog.select_json_file()
    if selected_file:
        print(f"Selected file: {selected_file}")
    else:
        print("No file selected.")