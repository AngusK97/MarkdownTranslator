import os
import threading
import json
from tkinter import Tk
from ui_components import TranslationApp

if __name__ == '__main__':
    root = Tk()
    app = TranslationApp(root)
    root.mainloop()