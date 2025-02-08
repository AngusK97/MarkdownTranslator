import os
import time
import re
import threading
import json
from tkinter import Tk, Button, Label, filedialog, messagebox, StringVar, Entry, Frame, Text, Checkbutton, BooleanVar, OptionMenu
from tkinter.ttk import Progressbar
from google.cloud import translate_v2 as translate

CONFIG_FILE = "config.json"

# ======================== Style Configuration ========================
COLOR_BG = "#2d2d2d"         # Background color - Dark Gray
COLOR_FG = "#ffffff"         # Foreground color - White
COLOR_BUTTON = "#3d3d3d"     # Button background color
COLOR_HOVER = "#4d4d4d"      # Button hover color
FONT_NAME = "微软雅黑"        # Main font
FONT_SIZE = 10               # Base font size
WINDOW_WIDTH = 680
WINDOW_HEIGHT = 680  # Increased height for additional options

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
        master.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")  

        # ===== Center the window =====
        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()
        x = (screen_width - WINDOW_WIDTH) // 2  
        y = (screen_height - WINDOW_HEIGHT) // 2  
        master.geometry(f"+{x}+{y}")  
        # ===== End of positioning =====

        master.configure(bg=COLOR_BG)  # Set main window background color

        # ======================== Font Definition ========================
        self.font_normal = (FONT_NAME, FONT_SIZE)
        self.font_title = (FONT_NAME, FONT_SIZE+2, "bold")
        self.font_mono = ("Consolas", FONT_SIZE)  # Monospace font for path display

        # ======================== Variable Initialization ========================
        self.folder_path = StringVar()
        self.output_folder = StringVar()
        self.credentials_path = StringVar()
        self.source_language = StringVar(value="Chinese")  # Default source language
        self.target_language = StringVar(value="English")  # Default target language
        
        # Set initial values
        self.folder_path.set("Input folder not selected")
        self.output_folder.set("Output folder not selected")
        self.credentials_path.set("Google credentials file not selected")
        
        # Add variable tracking
        self.folder_path.trace_add("write", lambda *_: self.check_ready())
        self.output_folder.trace_add("write", lambda *_: self.check_ready())
        self.credentials_path.trace_add("write", lambda *_: self.check_ready())
        
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
                              font=self.font_mono,
                              fg="#a0a0a0",  # Light gray text
                              bg=COLOR_BG,
                              anchor="w")
        self.cred_label.pack(side="left", fill="x", expand=True)

        # ======================== Input and Output Path Section ========================
        self.create_path_section("Input Folder", self.select_input_folder, self.folder_path)
        self.create_path_section("Output Folder", self.select_output_folder, self.output_folder)

        # ======================== Language Selection ========================
        self.create_language_selection()

        # ======================== Obsidian Option ========================
        self.obsidian_var = BooleanVar(value=False)
        self.obsidian_check = Checkbutton(self.main_frame,
                                        text="Keep Obsidian Links [[]]",
                                        variable=self.obsidian_var,
                                        command=self.check_ready,
                                        font=self.font_normal,
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
                                  mode="determinate",
                                  style="custom.Horizontal.TProgressbar")
        self.progress.pack(pady=10)

        # ======================== Log Text Box ========================
        self.log_text = Text(self.main_frame,
                           height=12,
                           width=80,
                           wrap="word",
                           font=self.font_mono,
                           bg="#1a1a1a",  # Dark background
                           fg="#c0c0c0",  # Light gray text
                           insertbackground=COLOR_FG)  # Cursor color
        self.log_text.pack()
        self.log_text.insert("end", ">>> Ready, waiting to start translation...\n")

        # ======================== Initialize Configuration ========================
        self.load_credentials()
        self.check_ready()
        self.setup_style()

    # ======================== Create Language Selection ========================
    def create_language_selection(self):
        """Create language selection dropdowns for source and target languages."""
        lang_frame = Frame(self.main_frame, bg=COLOR_BG)
        lang_frame.pack(pady=10)

        Label(lang_frame, text="Source Language:", font=self.font_normal, fg=COLOR_FG, bg=COLOR_BG).pack(side="left", padx=5)
        OptionMenu(lang_frame, self.source_language, *LANGUAGES.keys()).pack(side="left", padx=5)

        Label(lang_frame, text="Target Language:", font=self.font_normal, fg=COLOR_FG, bg=COLOR_BG).pack(side="left", padx=5)
        OptionMenu(lang_frame, self.target_language, *LANGUAGES.keys()).pack(side="left", padx=5)

    # ======================== Custom Style Method ========================
    def setup_style(self):
        """Configure progress bar style"""
        from tkinter import ttk
        style = ttk.Style()
        style.theme_use('default')
        style.configure("custom.Horizontal.TProgressbar",
                        thickness=15,
                        troughcolor=COLOR_BG,
                        bordercolor=COLOR_BG,
                        background="#4CAF50",  # Progress bar green
                        lightcolor="#66BB6A",
                        darkcolor="#388E3C")

    def create_button(self, parent, text, command, state="normal"):
        """Create a button with a unified style"""
        return Button(parent,
                    text=text,
                    command=command,
                    state=state,
                    font=self.font_normal,
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
        
        Label(frame,
            text=f"{title}:",
            font=self.font_normal,
            fg=COLOR_FG,
            bg=COLOR_BG,
            width=10,
            anchor="w").pack(side="left", padx=5)
            
        btn = self.create_button(frame, f"Select {title}", command)
        btn.pack(side="left", padx=5)
        
        # Save button reference to instance variable
        if title == "Input Folder":
            self.input_button = btn
        elif title == "Output Folder":
            self.output_button = btn
        
        entry = Entry(frame,
                    textvariable=variable,
                    state='readonly',
                    font=self.font_mono,
                    fg="#a0a0a0",
                    readonlybackground="#404040",
                    relief="flat",
                    width=40)
        entry.pack(side="left", fill="x", expand=True)

    # ======================== Original Functionality Methods ========================
    def load_credentials(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    saved_path = data.get("credentials", "")
                    if saved_path and os.path.exists(saved_path):
                        self.credentials_path.set(saved_path)
                        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = saved_path
            except Exception as e:
                self.log(f"Failed to load configuration: {e}")

    def save_credentials(self, path):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"credentials": path}, f, ensure_ascii=False, indent=4)

    def select_credentials(self):
        file_selected = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file_selected:
            self.credentials_path.set(file_selected)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = file_selected
            self.save_credentials(file_selected)
            self.check_ready()

    def select_input_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(folder_selected)
            self.check_ready()

    def select_output_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_folder.set(folder_selected)
            os.makedirs(folder_selected, exist_ok=True)
            self.check_ready()

    def check_ready(self, *args):
        ready_conditions = [
            self.credentials_path.get() != "Google credentials file not selected",
            self.folder_path.get() not in ["Input folder not selected", ""],
            self.output_folder.get() not in ["Output folder not selected", ""]
        ]
        
        if all(ready_conditions):
            self.translate_button.config(state="normal", bg=COLOR_BUTTON)
        else:
            self.translate_button.config(state="disabled", bg="#404040")  # Disabled state color
        
        # Force refresh the interface
        self.master.update_idletasks()

    def start_translation(self):
        folder = self.folder_path.get()
        output_folder = self.output_folder.get()
        source_lang = LANGUAGES[self.source_language.get()]  # Get the code for source language
        target_lang = LANGUAGES[self.target_language.get()]  # Get the code for target language

        if not os.path.exists(folder):
            messagebox.showerror("Error", "Input folder does not exist!")
            return

        self.toggle_buttons(False)
        thread = threading.Thread(target=self.run_translation, args=(folder, output_folder, source_lang, target_lang))
        thread.start()

    def run_translation(self, input_folder, output_folder, source_lang, target_lang):
        try:
            self.progress["value"] = 0
            files = [f for f in os.listdir(input_folder) if f.endswith('.md')]
            total_files = len(files)

            for idx, filename in enumerate(files):
                self.log(f"Processing: {filename} ({idx+1}/{total_files})")
                file_path = os.path.join(input_folder, filename)
                translated_file_path = os.path.join(output_folder, filename)
                self.translate_file(file_path, translated_file_path, source_lang, target_lang)
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

    def translate_file(self, input_path, output_path, source_lang, target_lang):
        translate_client = translate.Client()
        with open(input_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        translated_lines = []
        for line in lines:
            line_content = line.rstrip('\n')
            if not line_content.strip():
                translated_lines.append('\n')
                continue
            translated_line = self.process_markdown_line(translate_client, line_content, source_lang, target_lang)
            translated_lines.append(translated_line + '\n')

        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(translated_lines)

    def process_markdown_line(self, translate_client, line, source_lang, target_lang):
        patterns = [
            (r'(\[\[.*?\]\])', 'obsidian_link'),
            (r'^(\s*[-*+]\s+)(.*)', 'list'),
            (r'^(\s*\d+\.\s+)(.*)', 'ordered_list'),
            (r'^(#+\s+)(.*)', 'header'),
            (r'(\[.*?\]\(.*?\))', 'markdown_link'),
            (r'(`.+?`)', 'inline_code')
        ]

        for pattern, pattern_type in patterns:
            match = re.search(pattern, line)
            if match:
                if pattern_type == 'obsidian_link' and self.obsidian_var.get():
                    return line
                if pattern_type in ['list', 'ordered_list', 'header']:
                    symbol, content = match.groups()
                    translated_content = translate_client.translate(content, source_language=source_lang, target_language=target_lang)['translatedText']
                    return f"{symbol}{translated_content}"
                elif pattern_type in ['markdown_link', 'inline_code']:
                    return line
        return translate_client.translate(line, source_language=source_lang, target_language=target_lang)['translatedText']

    # ======================== Helper Methods ========================
    def toggle_buttons(self, enable=True):
        state = "normal" if enable else "disabled"
        self.translate_button.config(state=state)
        self.cred_button.config(state=state)
        self.input_button.config(state=state)
        self.output_button.config(state=state)

    def log(self, message):
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.master.update_idletasks()

if __name__ == '__main__':
    root = Tk()
    app = TranslationApp(root)
    
    root.mainloop()
