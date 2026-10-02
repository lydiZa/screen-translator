import os
import json
import time
import threading
import tkinter as tk
from tkinter import scrolledtext

from dotenv import load_dotenv
from google import genai
from mss import mss
from PIL import Image

# ==============================================================================
# 1. INITIALIZATION & CONFIGURATION
# ==============================================================================

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY missing from .env file!")

client = genai.Client(api_key=api_key)

# ==============================================================================
# 2. APPLICATION CLASS
# ==============================================================================

class VNTranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Screen Translator")

        # CUSTOMIZE: Change the default visibility values here; user choices are saved in settings.json.
        self.settings_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "settings.json"
        )
        view_settings = self.load_view_settings()
        self.show_type_text = view_settings.get("show_type_text_view", True)
        self.show_original_text = view_settings.get("show_original_text_view", True)
        self.is_manual_input_expanded = False
        self.is_original_expanded = True
        self.is_translation_expanded = True
        self.show_type_text_var = tk.BooleanVar(
            master=self.root, value=self.show_type_text
        )
        self.show_original_text_var = tk.BooleanVar(
            master=self.root, value=self.show_original_text
        )
        # CUSTOMIZE: Set the startup language and edit this tuple to add or remove languages.
        self.target_lang = tk.StringVar(master=self.root, value="English")
        self.target_languages = (
            "English", "Spanish", "French", "German", "Chinese", "Japanese",
            "Korean", "Vietnamese"
        )
        self.create_view_menu()
        
        # CUSTOMIZE: Geometry is width x height + screen-x + screen-y.
        self.root.geometry("540x580+100+100")
        self.root.attributes("-topmost", True)
        
        self.active_region = None
        self.selection_win = None
        self.typed_translation_id = 0

        # Bind spacebar to quick-translate the active region
        self.root.bind("<space>", self.handle_spacebar)

        # --- MAIN UI CONTAINER ---
        self.card = tk.Frame(self.root, bg="#111827", padx=14, pady=12)
        self.card.pack(fill="both", expand=True)

        # ======================================================================
        # REGION 1: COLLAPSIBLE MANUAL INPUT
        # ======================================================================
        self.manual_input_section = tk.Frame(self.card, bg="#111827")
        if self.show_type_text:
            self.manual_input_section.pack(fill="x", pady=(8, 2))

        self.manual_input_header_frame = tk.Frame(self.manual_input_section, bg="#111827")
        self.manual_input_header_frame.pack(fill="x")

        self.btn_toggle_manual_input = tk.Button(
            self.manual_input_header_frame,
            text=("▼" if self.is_manual_input_expanded else "▶") + " TYPE TEXT TO TRANSLATE",
            command=self.toggle_manual_input_box,
            font=("Segoe UI", 8, "bold"),
            fg="#60A5FA", bg="#111827",
            relief="flat", activebackground="#111827", activeforeground="#93C5FD",
            bd=0
        )
        self.btn_toggle_manual_input.pack(side="left")

        # CUSTOMIZE: Adjust the font and colors to change the type-text field.
        self.manual_input = tk.Entry(
            self.manual_input_section,
            font=("Segoe UI", 9),
            bg="#1F2937",
            fg="#F9FAFB",
            insertbackground="white",
            relief="flat"
        )
        # CUSTOMIZE: Edit the input hint here; its font and color match the Entry above.
        self.manual_input_placeholder = "Press ENTER to confirm text"
        self.manual_input_showing_placeholder = True
        self.manual_input.insert(0, self.manual_input_placeholder)
        self.manual_input.config(fg="#9CA3AF")
        self.manual_input.bind("<FocusIn>", self.clear_manual_input_placeholder)
        self.manual_input.bind("<FocusOut>", self.restore_manual_input_placeholder)
        self.manual_input.bind("<Return>", self.translate_typed_text_on_enter)
        if self.is_manual_input_expanded:
            self.manual_input.pack(fill="x", ipady=6)

        # ======================================================================
        # REGION 2: COLLAPSIBLE ORIGINAL TEXT
        # ======================================================================
        self.original_text_section = tk.Frame(self.card, bg="#111827")
        if self.show_original_text:
            self.original_text_section.pack(fill="x", pady=(8, 2))

        self.orig_header_frame = tk.Frame(self.original_text_section, bg="#111827")
        self.orig_header_frame.pack(fill="x", pady=(8, 2))

        self.btn_toggle_orig = tk.Button(
            self.orig_header_frame,
            text=("▼" if self.is_original_expanded else "▶") + " ORIGINAL TEXT",
            command=self.toggle_original_box,
            font=("Segoe UI", 8, "bold"),
            fg="#60A5FA", bg="#111827",
            relief="flat", activebackground="#111827", activeforeground="#93C5FD",
            bd=0
        )
        self.btn_toggle_orig.pack(side="left")

        # CUSTOMIZE: Change this font and the background/foreground colors for recognized text.
        self.box_original = scrolledtext.ScrolledText(
            self.original_text_section,
            wrap="word",
            font=("Segoe UI", 9),
            bg="#1F2937",
            fg="#F9FAFB",
            insertbackground="white",
            height=4,
            relief="flat",
            padx=8,
            pady=6
        )
        if self.is_original_expanded and self.show_original_text:
            self.box_original.pack(fill="both", expand=True)
        self.box_original.config(state="disabled")

        # ======================================================================
        # REGION 3: TRANSLATED TEXT
        # ======================================================================
        self.lbl_translated = tk.Button(
            self.card, 
            text="▼ TRANSLATION:",
            command=self.toggle_translation_box,
            font=("Segoe UI", 8, "bold"), 
            fg="#34D399", 
            bg="#111827",
            relief="flat",
            activebackground="#111827",
            activeforeground="#34D399",
            bd=0
        )
        self.lbl_translated.pack(anchor="w", pady=(10, 2))

        # CUSTOMIZE: Negative font sizes are pixels; this sets translated text to 16 px.
        self.box_translated = scrolledtext.ScrolledText(
            self.card,
            wrap="word",
            font=("Segoe UI", -16, "bold"),
            bg="#1F2937",
            fg="#10B981",
            insertbackground="white",
            height=6,
            relief="flat",
            padx=8,
            pady=6
        )
        self.box_translated.pack(fill="both", expand=True)
        # CUSTOMIZE: This tag controls the initial placeholder's font size and style.
        self.box_translated.tag_configure(
            "placeholder", font=("Segoe UI", 10, "bold")
        )
        self.box_translated.config(state="disabled")

        self.set_boxes_text(
            original="1. Click 'Select Area' to draw a frame over the dialogue box once.\n2. Press SPACE or click 'Capture Next' to translate new text!", 
            translated="Translation will appear here...",
            translated_is_placeholder=True
        )

        # --- BUTTON CONTROLS BAR ---
        self.btn_frame = tk.Frame(self.card, bg="#111827")
        self.btn_frame.pack(fill="x", side="bottom", pady=(10, 0))

        # Select Box
        self.btn_select = tk.Button(
            self.btn_frame, 
            text="🎯 Select Area", 
            command=self.start_selection,
            bg="#2563EB", 
            fg="white", 
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=8,
            pady=4
        )
        self.btn_select.pack(side="left", padx=(0, 5))

        # Capture / Next Button (Spacebar trigger)
        self.btn_capture = tk.Button(
            self.btn_frame, 
            text="📸 Capture Next [Space]", 
            command=self.trigger_single_capture,
            bg="#059669", 
            fg="white", 
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=4
        )
        self.btn_capture.pack(side="left", padx=5)

        # Clear Region
        self.btn_exit = tk.Button(
            self.btn_frame, 
            text="🛑 Clear Region", 
            command=self.clear_region,
            bg="#DC2626", 
            fg="white", 
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=8,
            pady=4
        )
        self.btn_exit.pack(side="right")

    # ==========================================================================
    # 3. HELPER & UI TOGGLE METHODS
    # ==========================================================================

    def load_view_settings(self):
        try:
            with open(self.settings_path, "r", encoding="utf-8") as settings_file:
                settings = json.load(settings_file)
            if isinstance(settings, dict):
                return settings
        except (OSError, json.JSONDecodeError):
            pass
        return {}

    def save_view_settings(self):
        try:
            with open(self.settings_path, "w", encoding="utf-8") as settings_file:
                json.dump(
                    {
                        "show_type_text_view": self.show_type_text,
                        "show_original_text_view": self.show_original_text,
                    },
                    settings_file,
                    indent=2,
                )
        except OSError:
            pass

    def create_view_menu(self):
        self.menu_bar = tk.Menu(self.root)
        self.view_menu = tk.Menu(self.menu_bar, tearoff=False)
        self.view_menu.add_checkbutton(
            label="Show Type Text",
            variable=self.show_type_text_var,
            command=self.apply_type_text_visibility,
        )
        self.view_menu.add_checkbutton(
            label="Show Original Text",
            variable=self.show_original_text_var,
            command=self.apply_original_text_visibility,
        )
        self.language_menu = tk.Menu(self.menu_bar, tearoff=False)
        for language in self.target_languages:
            self.language_menu.add_radiobutton(
                label=language,
                variable=self.target_lang,
                value=language,
            )
        self.menu_bar.add_cascade(label="Select Language", menu=self.language_menu)
        self.menu_bar.add_cascade(label="View", menu=self.view_menu)
        self.root.config(menu=self.menu_bar)

    def apply_type_text_visibility(self):
        self.set_type_text_visibility(self.show_type_text_var.get())

    def set_type_text_visibility(self, visible):
        self.show_type_text = visible
        self.show_type_text_var.set(visible)
        self.repack_text_sections()
        self.save_view_settings()

    def apply_original_text_visibility(self):
        self.set_original_text_visibility(self.show_original_text_var.get())

    def set_original_text_visibility(self, visible):
        self.show_original_text = visible
        self.show_original_text_var.set(visible)
        self.repack_text_sections()
        self.save_view_settings()

    def repack_text_sections(self):
        self.manual_input_section.pack_forget()
        self.original_text_section.pack_forget()

        if self.show_type_text:
            self.manual_input_section.pack(
                fill="x", pady=(8, 2), before=self.lbl_translated
            )
        if self.show_original_text:
            self.original_text_section.pack(
                fill="x", pady=(8, 2), before=self.lbl_translated
            )

    def set_boxes_text(self, original, translated, translated_is_placeholder=False):
        """Helper method to safely update text boxes."""
        self.box_original.config(state="normal")
        self.box_original.delete("1.0", tk.END)
        self.box_original.insert("1.0", original)
        self.box_original.config(state="disabled")

        self.set_translated_text(translated, placeholder=translated_is_placeholder)

    def set_translated_text(self, text, placeholder=False):
        self.box_translated.config(state="normal")
        self.box_translated.delete("1.0", tk.END)
        if placeholder:
            self.box_translated.insert("1.0", text, "placeholder")
        else:
            self.box_translated.insert("1.0", text)
        self.box_translated.config(state="disabled")

    def handle_spacebar(self, event):
        if self.root.focus_get() == self.manual_input:
            return
        self.trigger_single_capture()

    def clear_manual_input_placeholder(self, event=None):
        if self.manual_input_showing_placeholder:
            self.manual_input.delete(0, tk.END)
            self.manual_input.config(fg="#F9FAFB")
            self.manual_input_showing_placeholder = False

    def restore_manual_input_placeholder(self, event=None):
        if not self.manual_input.get().strip():
            self.manual_input.insert(0, self.manual_input_placeholder)
            self.manual_input.config(fg="#9CA3AF")
            self.manual_input_showing_placeholder = True

    def translate_typed_text_on_enter(self, event=None):
        if self.manual_input_showing_placeholder:
            return "break"
        self.typed_translation_id += 1
        request_id = self.typed_translation_id
        self.translate_typed_text(request_id)
        return "break"

    def translate_typed_text(self, request_id):
        if request_id != self.typed_translation_id:
            return

        original_text = self.manual_input.get().strip()
        if not original_text:
            self.set_translated_text("")
            return

        target_language = self.target_lang.get()
        self.set_translated_text("Translating...")
        threading.Thread(
            target=self.process_typed_text,
            args=(original_text, target_language, request_id),
            daemon=True
        ).start()

    def process_typed_text(self, original_text, target_language, request_id):
        try:
            # CUSTOMIZE: Choose the Gemini model used for typed text here.
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=(
                    f"Translate the following text into {target_language}. "
                    f"Return only the translation, without explanations:\n\n{original_text}"
                ),
                config={"automatic_function_calling": {"disable": True}}
            )
            translated_text = (response.text or "").strip()
            self.root.after(
                0, self.show_typed_translation, request_id, translated_text
            )
        except Exception as err:
            self.root.after(
                0, self.show_typed_translation, request_id,
                f"Error translating text: {err}"
            )

    def show_typed_translation(self, request_id, translated_text):
        if request_id != self.typed_translation_id:
            return
        self.set_translated_text(translated_text)

    def toggle_original_box(self):
        """Collapses or expands the original text box."""
        if self.is_original_expanded:
            self.box_original.pack_forget()
            self.btn_toggle_orig.config(text="▶ ORIGINAL TEXT")
            self.is_original_expanded = False
        else:
            self.box_original.pack(fill="both", expand=True)
            self.btn_toggle_orig.config(text="▼ ORIGINAL TEXT")
            self.is_original_expanded = True

    def toggle_manual_input_box(self):
        if self.is_manual_input_expanded:
            self.manual_input.pack_forget()
            self.btn_toggle_manual_input.config(text="▶ TYPE TEXT TO TRANSLATE")
            self.is_manual_input_expanded = False
        else:
            self.manual_input.pack(fill="x", ipady=6)
            self.btn_toggle_manual_input.config(text="▼ TYPE TEXT TO TRANSLATE")
            self.is_manual_input_expanded = True

    def toggle_translation_box(self):
        if self.is_translation_expanded:
            self.box_translated.pack_forget()
            self.lbl_translated.config(text="▶ TRANSLATION:")
            self.lbl_translated.pack_configure(pady=0)
            self.is_translation_expanded = False
        else:
            self.box_translated.pack(fill="both", expand=True, before=self.btn_frame)
            self.lbl_translated.config(text="▼ TRANSLATION:")
            self.lbl_translated.pack_configure(pady=(10, 2))
            self.is_translation_expanded = True
        self.resize_to_content()

    def resize_to_content(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_reqheight()
        self.root.geometry(f"{width}x{height}")

    def change_opacity(self, value):
        """Dynamically adjusts window opacity."""
        self.root.attributes("-alpha", float(value))

    # ==========================================================================
    # 4. SCREEN SELECTION OVERLAY
    # ==========================================================================

    def start_selection(self):
        if self.selection_win and self.selection_win.winfo_exists():
            self.selection_win.destroy()

        self.selection_win = tk.Toplevel(self.root)
        self.selection_win.attributes("-fullscreen", True)
        # CUSTOMIZE: Set overlay opacity from 0.0 (transparent) to 1.0 (opaque).
        self.selection_win.attributes("-alpha", 0.3)
        self.selection_win.attributes("-topmost", True)
        self.selection_win.config(cursor="cross")

        self.canvas = tk.Canvas(self.selection_win, cursor="cross", bg="grey")
        self.canvas.pack(fill="both", expand=True)

        self.start_x = None
        self.start_y = None
        self.rect = None

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.selection_win.bind("<Escape>", lambda e: self.selection_win.destroy())

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, 1, 1, outline="red", width=2
        )

    def on_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        end_x, end_y = event.x, event.y

        left = min(self.start_x, end_x)
        top = min(self.start_y, end_y)
        width = abs(end_x - self.start_x)
        height = abs(end_y - self.start_y)

        if width < 10 or height < 10:
            self.selection_win.destroy()
            return

        # Save selected region permanently until cleared or re-selected
        self.active_region = {"top": top, "left": left, "width": width, "height": height}
        self.selection_win.destroy()

        # Trigger initial capture immediately
        self.trigger_single_capture()

    # ==========================================================================
    # 5. CAPTURE & TRANSLATE LOGIC
    # ==========================================================================

    def trigger_single_capture(self):
        """Triggers a single translation pass on the saved region."""
        if not self.active_region:
            self.set_boxes_text(
                original="No region selected!", 
                translated="Please click 'Select Area' first to set the dialogue area."
            )
            return

        self.set_boxes_text(
            original="Reading text box...", 
            translated="Translating..."
        )
        threading.Thread(target=self.process_region, daemon=True).start()

    def process_region(self):
        """Captures the active region and sends it to Gemini."""
        try:
            with mss() as sct:
                sct_img = sct.grab(self.active_region)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

                target_language = self.target_lang.get()

                # CUSTOMIZE: Keep this model aligned with the typed-text translator.
                response = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=[
                        img, 
                        f"Extract all text in this image crop. Format your response exactly as follows:\n"
                        f"ORIGINAL: <extracted original text>\n"
                        f"TRANSLATION: <{target_language} translation>"
                    ],
                    config={"automatic_function_calling": {"disable": True}}
                )

                text_output = response.text.strip()
                
                orig_text = ""
                trans_text = ""
                
                if "ORIGINAL:" in text_output and "TRANSLATION:" in text_output:
                    parts = text_output.split("TRANSLATION:")
                    orig_text = parts[0].replace("ORIGINAL:", "").strip()
                    trans_text = parts[1].strip()
                else:
                    orig_text = "Extracted Dialogue"
                    trans_text = text_output

                self.root.after(0, self.set_boxes_text, orig_text, trans_text)

        except Exception as err:
            err_msg = str(err)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                self.root.after(0, self.set_boxes_text, 
                    "Quota Limit Hit (429)", 
                    "Daily free limit reached. Wait a moment or add a billing account to your project."
                )
            else:
                self.root.after(0, self.set_boxes_text, "Error reading region.", f"Error: {err_msg}")

    def clear_region(self):
        self.active_region = None
        self.set_boxes_text(
            original="Region cleared.", 
            translated="Click 'Select Area' to choose a new dialogue area."
        )

# ==============================================================================
# 6. ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = VNTranslatorApp(root)
    root.mainloop()