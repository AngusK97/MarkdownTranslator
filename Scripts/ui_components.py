import os
import threading
import json
import html
import re
from tkinter import Frame, Button, Label, filedialog, messagebox, StringVar, Entry, Checkbutton, BooleanVar, OptionMenu, Text
from tkinter.ttk import Progressbar
from config import load_credentials, save_credentials
from translator import translate_file, process_markdown_line

COLOR_BG = "#2d2d2d"         # Background color - Dark Gray
COLOR_FG = "#ffffff"         # Foreground color - White
COLOR_BUTTON = "#3d3d3d"     # Button background color
COLOR_HOVER = "#4d4d4d"      # Button hover color
FONT_NAME = "微软雅黑"        # Main font
FONT_SIZE = 10               # Base font size

# Supported languages for translation
LANGUAGES = {
    "English": "en",
    "Chinese": "zh-CN",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Japanese": "ja",
    "Korean": "ko",
    "Russian": "ru",
    "Italian": "it",
    "Portuguese": "pt"
}

class TranslationApp:
    def __init__(self, master):
        self.master = master
        master.title("Markdown Translation Tool")

        # 获取屏幕宽度和高度
        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()

        # 设置窗口的宽度和高度
        window_width = 680
        window_height = 680

        # 计算居中位置
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)

        # 设置窗口大小和位置
        master.geometry(f"{window_width}x{window_height}+{x}+{y}")
        master.configure(bg=COLOR_BG)

        # ======================== Variable Initialization ========================
        self.input_path = StringVar(value="Input file or folder not selected")
        self.output_folder = StringVar(value="Output folder not selected")
        self.credentials_path = StringVar(value="Google credentials file not selected")
        self.source_language = StringVar(value="Chinese")  # Default source language
        self.target_language = StringVar(value="English")  # Default target language
        
        self.obsidian_var = BooleanVar(value=False)

        # ======================== Main Frame ========================
        self.main_frame = Frame(master, bg=COLOR_BG)
        self.main_frame.pack(padx=20, pady=15, fill="both", expand=True)

        # ======================== Google Credentials Section ========================
        self.cred_frame = Frame(self.main_frame, bg=COLOR_BG)
        self.cred_frame.pack(fill="x", pady=5)
        
        self.cred_button = self.create_button(self.cred_frame, "Select Google Credentials File", self.select_credentials)
        self.cred_button.pack(side="left", padx=5)
        
        self.cred_label = Label(self.cred_frame, 
                              textvariable=self.credentials_path,
                              wraplength=500,
                              font=("Consolas", FONT_SIZE),
                              fg="#a0a0a0",  # Light gray text
                              bg=COLOR_BG,
                              anchor="w")
        self.cred_label.pack(side="left", fill="x", expand=True)

        # ======================== Input Path Section ========================
        self.input_frame = Frame(self.main_frame, bg=COLOR_BG)
        self.input_frame.pack(fill="x", pady=5)

        self.file_button = self.create_button(self.input_frame, "Select Input File", self.select_input_file)
        self.file_button.pack(side="left", padx=5)

        self.folder_button = self.create_button(self.input_frame, "Select Input Folder", self.select_input_folder)
        self.folder_button.pack(side="left", padx=5)

        self.input_label = Label(self.input_frame, 
                                textvariable=self.input_path,
                                wraplength=500,
                                font=("Consolas", FONT_SIZE),
                                fg="#a0a0a0",  # Light gray text
                                bg=COLOR_BG,
                                anchor="w")
        self.input_label.pack(side="left", fill="x", expand=True)

        # ======================== Output Path Section ========================
        self.create_path_section("Output Folder", self.select_output_folder, self.output_folder)

        # ======================== Language Selection ========================
        self.create_language_selection()

        # ======================== Obsidian Option ========================
        self.obsidian_check = Checkbutton(self.main_frame,
                                        text="Keep Obsidian Links [[]]",
                                        variable=self.obsidian_var,
                                        command=self.check_ready,
                                        font=("微软雅黑", FONT_SIZE),
                                        fg=COLOR_FG,
                                        bg=COLOR_BG,
                                        selectcolor=COLOR_BG,
                                        activebackground=COLOR_BG,
                                        activeforeground=COLOR_FG)
        self.obsidian_check.pack(pady=10)

        # ======================== Action Buttons ========================
        self.btn_frame = Frame(self.main_frame, bg=COLOR_BG)
        self.btn_frame.pack(pady=15)
        
        self.translate_button = self.create_button(self.btn_frame, "Start Translation", self.start_translation, state="disabled")
        self.translate_button.pack(side="left", padx=10)

        self.close_button = self.create_button(self.btn_frame, "Close Program", master.quit)
        self.close_button.pack(side="left", padx=10)

        # ======================== Progress Bar ========================
        self.progress = Progressbar(self.main_frame,
                                  orient="horizontal",
                                  length=500,
                                  mode="determinate")
        self.progress.pack(pady=10)

        # ======================== Log Text Box ========================
        self.log_text = Text(self.main_frame,
                           height=12,
                           width=80,
                           wrap="word",
                           font=("Consolas", FONT_SIZE),
                           bg="#1a1a1a",  # Dark background
                           fg="#c0c0c0",  # Light gray text
                           insertbackground=COLOR_FG)  # Cursor color
        self.log_text.pack()
        self.log_text.insert("end", ">>> Ready, waiting to start translation...\n")

        # ======================== Initialize Configuration ========================
        self.load_credentials()
        self.check_ready()

    def create_language_selection(self):
        """Create language selection dropdowns for source and target languages."""
        lang_frame = Frame(self.main_frame, bg=COLOR_BG)
        lang_frame.pack(pady=10)

        Label(lang_frame, text="Source Language:", font=("微软雅黑", FONT_SIZE), fg=COLOR_FG, bg=COLOR_BG).pack(side="left", padx=5)
        OptionMenu(lang_frame, self.source_language, *LANGUAGES.keys()).pack(side="left", padx=5)

        Label(lang_frame, text="Target Language:", font=("微软雅黑", FONT_SIZE), fg=COLOR_FG, bg=COLOR_BG).pack(side="left", padx=5)
        OptionMenu(lang_frame, self.target_language, *LANGUAGES.keys()).pack(side="left", padx=5)

    def create_button(self, parent, text, command, state="normal"):
        """Create a button with a unified style"""
        return Button(parent,
                    text=text,
                    command=command,
                    state=state,
                    font=("微软雅黑", FONT_SIZE),
                    bg=COLOR_BUTTON,
                    fg=COLOR_FG,
                    activebackground=COLOR_HOVER,
                    activeforeground=COLOR_FG,
                    relief="flat",
                    padx=12,
                    pady=6)

    def create_path_section(self, title, command, variable):
        """Create path selection module"""
        frame = Frame(self.main_frame, bg=COLOR_BG)
        frame.pack(fill="x", pady=5)
        
        btn = self.create_button(frame, f"Select {title}", command)
        btn.pack(side="left", padx=5)

        self.input_label = Label(frame, 
                                textvariable=variable,
                                wraplength=500,
                                font=("Consolas", FONT_SIZE),
                                fg="#a0a0a0",  # Light gray text
                                bg=COLOR_BG,
                                anchor="w")
        self.input_label.pack(side="left", fill="x", expand=True)

    def load_credentials(self):
        saved_path = load_credentials()
        if saved_path:
            self.credentials_path.set(saved_path)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = saved_path

    def select_credentials(self):
        file_selected = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file_selected:
            self.credentials_path.set(file_selected)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = file_selected
            save_credentials(file_selected)
            self.check_ready()
    
    # 选择文件的方法
    def select_input_file(self):
        """Allow user to select a file for translation."""
        path_selected = filedialog.askopenfilename(filetypes=[("Markdown Files", "*.md"), ("All Files", "*.*")])
        if path_selected:
            self.input_path.set(path_selected)

    # 选择文件夹的方法
    def select_input_folder(self):
        """Allow user to select a folder for translation."""
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.input_path.set(folder_selected)

    def select_output_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_folder.set(folder_selected)
            os.makedirs(folder_selected, exist_ok=True)
            self.check_ready()

    def check_ready(self):
        ready_conditions = [
            self.credentials_path.get() != "Google credentials file not selected",
            self.input_path.get() not in ["Input file or folder not selected", ""],
            self.output_folder.get() not in ["Output folder not selected", ""]
        ]
        
        if all(ready_conditions):
            self.translate_button.config(state="normal", bg=COLOR_BUTTON)
        else:
            self.translate_button.config(state="disabled", bg="#404040")  # Disabled state color
        
        # Force refresh the interface
        self.master.update_idletasks()

    def start_translation(self):
        input_path = self.input_path.get()
        output_folder = self.output_folder.get()
        source_lang = LANGUAGES[self.source_language.get()]  # Get the code for source language
        target_lang = LANGUAGES[self.target_language.get()]  # Get the code for target language

        if not os.path.exists(input_path):
            messagebox.showerror("Error", "Input file or folder does not exist!")
            return

        self.toggle_buttons(False)
        thread = threading.Thread(target=self.run_translation, args=(input_path, output_folder, source_lang, target_lang))
        thread.start()

    def run_translation(self, input_path, output_folder, source_lang, target_lang):
        try:
            self.progress["value"] = 0
            files = []

            # Check if input path is a file or folder
            if os.path.isfile(input_path):
                files = [input_path]  # Single file
            elif os.path.isdir(input_path):
                files = [f for f in os.listdir(input_path) if f.endswith('.md')]
                files = [os.path.join(input_path, f) for f in files]  # Full paths of files in the folder

            total_files = len(files)

            if total_files == 0:
                messagebox.showwarning("Warning", "No Markdown files found in the selected folder.")
                return

            for idx, filename in enumerate(files):
                self.log(f"Processing: {filename} ({idx+1}/{total_files})")
                translated_file_path = os.path.join(output_folder, os.path.basename(filename))
                translate_file(filename, translated_file_path, source_lang, target_lang)
                self.progress["value"] = (idx + 1) / total_files * 100
                self.master.update_idletasks()

            self.log("✅ All files translated successfully!")
            messagebox.showinfo("Completed", "Translation task completed!")
        except Exception as e:
            self.log(f"❌ Error occurred: {str(e)}")
            messagebox.showerror("Error", f"An error occurred during translation:\n{str(e)}")
        finally:
            self.toggle_buttons(True)
            self.progress["value"] = 0

    def toggle_buttons(self, enable=True):
        state = "normal" if enable else "disabled"
        self.translate_button.config(state=state)
        self.cred_button.config(state=state)

    def log(self, message):
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.master.update_idletasks()
