import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import json
import yaml
import re
import os
from transformers import AutoTokenizer

class JSONTextEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("JSON Text Editor")
        self.font_size = 16
        self.text_areas = []
        self.current_file_path = None
        self.load_config()
        self.load_tokenizers()

        self.token_count_label = tk.Label(self.root, text="Token Counts: ", font=("TkDefaultFont", 14))
        self.token_count_label.pack(side=tk.TOP, pady=10)

        self._create_main_frame()
        self._create_initial_text_boxes()
        self._create_menu()
        self._setup_hotkeys()

    def load_config(self):
        try:
            with open('config.yml', 'r') as file:
                self.config = yaml.safe_load(file)
        except FileNotFoundError:
            self.config = {
                'highlights': [
                    {'pattern': r'\*(.+?)\*', 'color': 'red'},
                    {'pattern': r'\bSicarius\b', 'color': 'green'}
                ],
                'text_background_from_yml': {
                    'color': 'grey'
                },
                'txtbox_main_size': {
                    'height': 8,
                    'width': 150
                },
                'txtbox_others_size': {
                    'height': 4,
                    'width': 150
                }
            }
            with open('config.yml', 'w') as file:
                yaml.dump(self.config, file)

    def open_file(self):
        file_path = filedialog.askopenfilename(defaultextension=".json",
                                               filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if file_path:
            self._load_file(file_path)

    def load_tokenizers(self):
        with open('token_count.yml', 'r') as file:
            token_config = yaml.safe_load(file)
        self.tokenizers = {}
        for name, paths in token_config.items():
            for path in paths:
                self.tokenizers[name] = AutoTokenizer.from_pretrained(path)

    def _create_main_frame(self):
        self.canvas = tk.Canvas(self.root)
        self.scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def _create_token_count_label(self):
        self.token_count_label = tk.Label(self.root, text="Token Counts: N/A", font=("TkDefaultFont", 14))
        self.token_count_label.pack(anchor='n')

    def _create_initial_text_boxes(self):
        self._add_text_box("System Prompt", "system", is_main=True)
        self._add_tuplet()

    def _add_text_box(self, label, role, is_main=False):
        frame = tk.Frame(self.scrollable_frame)
        frame.pack(expand=1, fill='both', pady=5)

        label_widget = tk.Label(frame, text=f"{label} (Tokens: 0)")
        label_widget.pack()

        text_background = self.config.get('text_background_from_yml', {}).get('color', 'grey')

        if is_main:
            size = self.config.get('txtbox_main_size', {'height': 8, 'width': 150})
        else:
            size = self.config.get('txtbox_others_size', {'height': 4, 'width': 150})

        text_area = scrolledtext.ScrolledText(frame, wrap='word',
                                              width=size['width'], height=size['height'],
                                              font=("TkDefaultFont", self.font_size),
                                              background=text_background)
        text_area.pack(expand=1, fill='both')

        text_area.bind("<KeyRelease>", lambda event: self._on_text_change(text_area, label_widget))

        self.text_areas.append((text_area, role, frame, label_widget))

    def _add_tuplet(self):
        human_count = sum(1 for _, role, _, _ in self.text_areas if role == 'human')
        gpt_count = sum(1 for _, role, _, _ in self.text_areas if role == 'gpt')

        self._add_text_box(f"Human {human_count + 1}", "human", is_main=False)
        self._add_text_box(f"GPT {gpt_count + 1}", "gpt", is_main=False)
        self._update_buttons()

    def _remove_tuplet(self):
        if len(self.text_areas) > 3:
            self.text_areas[-1][2].destroy()
            self.text_areas[-2][2].destroy()
            del self.text_areas[-2:]
            self._update_buttons()

    def _update_buttons(self):
        if hasattr(self, 'button_frame'):
            self.button_frame.destroy()

        self.button_frame = tk.Frame(self.scrollable_frame)
        self.button_frame.pack()

        self.add_tuplet_button = tk.Button(self.button_frame, text="Add Tuplet", command=self._add_tuplet)
        self.add_tuplet_button.pack(side=tk.LEFT)

        self.remove_tuplet_button = tk.Button(self.button_frame, text="Remove Tuplet", command=self._remove_tuplet)
        self.remove_tuplet_button.pack(side=tk.LEFT)
        self.remove_tuplet_button.config(state=tk.NORMAL if len(self.text_areas) > 3 else tk.DISABLED)

    def _create_menu(self):
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)

        file_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New (Ctrl+N)", command=self.new_file)
        file_menu.add_command(label="Open (Ctrl+O)", command=self.open_file)
        file_menu.add_command(label="Save (Ctrl+S)", command=self.save_file)
        file_menu.add_command(label="Save As (Ctrl+D)", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        edit_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Increase Font Size (Ctrl+=)", command=self._increase_font_size)
        edit_menu.add_command(label="Decrease Font Size (Ctrl+-)", command=self._decrease_font_size)

        misc_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Misc", menu=misc_menu)
        misc_menu.add_command(label="Count Tokens (Ctrl+T)", command=self.count_tokens)

    def _on_text_change(self, text_widget, label_widget):
        content = text_widget.get("1.0", tk.END).strip()

        for tag in text_widget.tag_names():
            if tag.startswith("highlight_"):
                text_widget.tag_remove(tag, "1.0", tk.END)

        for i, highlight in enumerate(self.config['highlights']):
            pattern = highlight['pattern']
            color = highlight['color']
            tag_name = f"highlight_{i}"

            for match in re.finditer(pattern, content):
                start = text_widget.index(f"1.0 + {match.start()} chars")
                end = text_widget.index(f"1.0 + {match.end()} chars")
                text_widget.tag_add(tag_name, start, end)
                text_widget.tag_config(tag_name, foreground=color)

        # Count tokens and update the label
        tokenizer = self.tokenizers.get("default")  # Use appropriate tokenizer key
        if tokenizer:
            tokens = tokenizer.encode(content, add_special_tokens=False)
            token_count = len(tokens)
            label_text = label_widget.cget("text").split(" (Tokens: ")[0]
            label_widget.config(text=f"{label_text} (Tokens: {token_count})")

    def new_file(self):
        if self._confirm_discard_changes():
            for _, _, frame, _ in self.text_areas:
                frame.destroy()
            self.text_areas.clear()
            self._create_initial_text_boxes()
            self.root.title("JSON Text Editor")
            self.current_file_path = None

    def _confirm_discard_changes(self):
        response = messagebox.askyesnocancel("Confirm", "Do you want to save changes?")
        if response is None:  # Cancel
            return False
        elif response:  # Yes
            self.save_file()
            return True
        else:  # No
            return True

    def _load_file(self, file_path):
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                conversations = data[0]['conversations']

            for _, _, frame, _ in self.text_areas:
                frame.destroy()
            self.text_areas.clear()

            for i, conv in enumerate(conversations):
                role = conv['from']
                label = f"{role.capitalize()} {i + 1}"
                self._add_text_box(label, role, is_main=(i == 0))
                text_area = self.text_areas[-1][0]
                text_area.insert(tk.END, conv['value'])
                self._on_text_change(text_area, self.text_areas[-1][3])

            self.root.title(f"JSON Text Editor - {os.path.basename(file_path)}")
            self.current_file_path = file_path
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid JSON file.")
        except FileNotFoundError:
            messagebox.showerror("Error", "File not found.")

    def save_file(self):
        if self.current_file_path:
            self._save_file_to_path(self.current_file_path)
        else:
            self.save_file_as()

    def save_file_as(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json",
                                                 filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if file_path:
            self._save_file_to_path(file_path)

    def _save_file_to_path(self, file_path):
        try:
            data = []
            conversations = []
            for text_area, role, _, _ in self.text_areas:
                conversations.append({
                    'from': role,
                    'value': text_area.get("1.0", tk.END).strip()
                })
            data.append({'conversations': conversations})

            with open(file_path, 'w') as file:
                json.dump(data, file, indent=4)

            self.current_file_path = file_path
            self.root.title(f"JSON Text Editor - {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {e}")

    def _increase_font_size(self):
        self.font_size += 1
        for text_area, _, _, _ in self.text_areas:
            text_area.config(font=("TkDefaultFont", self.font_size))

    def _decrease_font_size(self):
        if self.font_size > 1:
            self.font_size -= 1
            for text_area, _, _, _ in self.text_areas:
                text_area.config(font=("TkDefaultFont", self.font_size))

    def count_tokens(self):
        total_counts = {}
        for tokenizer_name, tokenizer in self.tokenizers.items():
            total_count = 0
            for text_area, _, _, _ in self.text_areas:
                content = text_area.get("1.0", tk.END).strip()
                tokens = tokenizer.encode(content, add_special_tokens=False)
                total_count += len(tokens)
            total_counts[tokenizer_name] = total_count

        counts_text = ", ".join(f"{name}: {count}" for name, count in total_counts.items())
        self.token_count_label.config(text=f"Token Counts: {counts_text}")

    def _setup_hotkeys(self):
        self.root.bind("<Control-n>", lambda event: self.new_file())
        self.root.bind("<Control-o>", lambda event: self.open_file())
        self.root.bind("<Control-s>", lambda event: self.save_file())
        self.root.bind("<Control-d>", lambda event: self.save_file_as())
        self.root.bind("<Control-equal>", lambda event: self._increase_font_size())
        self.root.bind("<Control-minus>", lambda event: self._decrease_font_size())
        self.root.bind("<Control-t>", lambda event: self.count_tokens())
        self.root.bind("<y>", lambda event: self._confirm_discard_changes())
        self.root.bind("<n>", lambda event: self.root.quit())

if __name__ == "__main__":
    root = tk.Tk()
    app = JSONTextEditor(root)
    root.geometry("600x400")
    root.mainloop()
