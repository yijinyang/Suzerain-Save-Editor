import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import re
import json
import shutil

class SaveGameEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Don't Forget Who Your Suzerain Is: A Suzerain Save Editor")
        self.root.geometry("1000x700")
        
        # Set maroon background
        self.root.configure(bg='maroon')
        
        # Setup default save directory
        self.default_dir = self.get_default_save_dir()
        
        # Create UI elements
        self.create_widgets()
        self.file_path = None
        self.original_vars = []
        self.tree_items = {}
        
    def get_default_save_dir(self):
        """Get the default save directory path"""
        user_profile = os.getenv('USERPROFILE')
        if not user_profile:
            user_profile = os.path.expanduser('~')
        return os.path.join(user_profile, 'AppData', 'LocalLow', 'Torpor Games', 'Suzerain')
    
    def create_widgets(self):
        """Create all UI widgets with maroon theme"""
        # Configure styles
        style = ttk.Style()
        style.configure('TFrame', background='#f0d9c7')
        style.configure('TButton', background='#f0d9c7', foreground='black')
        style.configure('TLabel', background='#f0d9c7', foreground='black')
        style.configure('Treeview', background='white', fieldbackground='white', foreground='black')
        style.configure('Treeview.Heading', background='#e0c9b7', foreground='black')
        style.configure('TEntry', fieldbackground='white', background='white')
        style.configure('TCombobox', fieldbackground='white', background='white')
        
        # Top button frame
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.load_btn = ttk.Button(button_frame, text="Load Savegame", command=self.load_savegame)
        self.load_btn.pack(side=tk.LEFT, padx=5)
        
        self.save_btn = ttk.Button(button_frame, text="Save Savegame", command=self.save_savegame, state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        # Search frame
        search_frame = ttk.Frame(self.root)
        search_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.bind("<KeyRelease>", self.filter_tree)
        
        # Treeview frame with scrollbars
        tree_frame = ttk.Frame(self.root)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.tree = ttk.Treeview(tree_frame, columns=("Key", "Value"), show="headings", selectmode="browse")
        self.tree.heading("Key", text="Key")
        self.tree.heading("Value", text="Value")
        self.tree.column("Key", width=700, anchor=tk.W)
        self.tree.column("Value", width=100, anchor=tk.W)
        
        self.vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bind double-click event for editing
        self.tree.bind("<Double-1>", self.on_double_click)
        
        # Status bar with maroon theme
        self.status = tk.Label(
            self.root, text="Ready", 
            bd=1, relief=tk.SUNKEN, anchor=tk.W,
            bg='maroon', fg='white', font=('Arial', 10))
        self.status.pack(side=tk.BOTTOM, fill=tk.X)
    
    def load_savegame(self):
        """Load a savegame file"""
        file_path = filedialog.askopenfilename(
            initialdir=self.default_dir,
            title="Select Savegame File",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*"))
        )
        
        if not file_path:
            return
            
        self.file_path = file_path
        self.status.config(text=f"Loaded: {os.path.basename(file_path)}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            
            # Extract the variables string
            variables_str = save_data.get("variables", "")
            self.original_vars = self.parse_variables(variables_str)
            
            # Populate treeview
            self.populate_tree(self.original_vars)
            self.save_btn.config(state=tk.NORMAL)
            self.search_var.set("")  # Clear search filter
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load savegame:\n{str(e)}")
            self.status.config(text="Error loading file")
    
    def parse_variables(self, variables_str):
        """Parse the variables string into a list of (key, value) tuples"""
        # Extract the inner part of the Variable={...} string
        match = re.search(r'Variable=\{(.*?)\};', variables_str, re.DOTALL)
        if not match:
            return []
        
        inner = match.group(1).strip()
        items = []
        current = ""
        in_quotes = False
        bracket_depth = 0
        
        # Parse the string manually to handle nested commas
        for char in inner:
            if char == '[':
                bracket_depth += 1
            elif char == ']':
                bracket_depth -= 1
            elif char == '"':
                in_quotes = not in_quotes
                
            # Split only at top-level commas
            if char == ',' and bracket_depth == 0 and not in_quotes:
                items.append(current.strip())
                current = ""
            else:
                current += char
        
        if current.strip():
            items.append(current.strip())
        
        # Parse each item into key-value pairs
        parsed = []
        for item in items:
            if not item:
                continue
            
            # Improved regex to handle quoted values and complex strings
            match = re.match(r'\["(.*?)"\]\s*=\s*(".*?"|\w+)', item)
            if match:
                key = match.group(1)
                val_str = match.group(2)
                
                # Handle quoted values
                if val_str.startswith('"') and val_str.endswith('"'):
                    value = val_str[1:-1]  # Remove quotes
                # Handle boolean values
                elif val_str.lower() == "true":
                    value = True
                elif val_str.lower() == "false":
                    value = False
                # Handle integers
                else:
                    try:
                        value = int(val_str)
                    except ValueError:
                        value = val_str  # Fallback to string
                parsed.append((key, value))
        
        return parsed
    
    def populate_tree(self, data):
        """Populate treeview with data"""
        self.tree.delete(*self.tree.get_children())
        self.tree_items = {}
        
        for key, value in data:
            if isinstance(value, bool):
                display_value = "true" if value else "false"
            elif isinstance(value, int):
                display_value = str(value)
            else:
                display_value = value
                
            item_id = self.tree.insert("", "end", values=(key, display_value))
            self.tree_items[item_id] = (key, value)
    
    def filter_tree(self, event=None):
        """Filter treeview based on search text - completely hide non-matching items"""
        search_text = self.search_var.get().lower()
        
        # Show all items if search is empty
        if not search_text:
            self.populate_tree(self.original_vars)
            return
        
        # Filter items that match the search text
        filtered_data = []
        for key, value in self.original_vars:
            if search_text in key.lower():
                filtered_data.append((key, value))
        
        self.populate_tree(filtered_data)
    
    def on_double_click(self, event):
        """Handle double-click event for editing values"""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
            
        column = self.tree.identify_column(event.x)
        selected_items = self.tree.selection()
        
        if not selected_items:
            return
            
        item = selected_items[0]
        
        if column == "#2":  # Only edit the Value column
            key, original_value = self.tree_items[item]
            current_value = self.tree.item(item, "values")[1]
            
            # Get the cell coordinates
            x, y, width, height = self.tree.bbox(item, column="#2")
            
            # Create editing widget based on data type
            if isinstance(original_value, bool):
                self.edit_bool(item, key, current_value, x, y)
            elif isinstance(original_value, int):
                self.edit_int(item, key, current_value, x, y)
            elif isinstance(original_value, str):
                self.edit_str(item, key, current_value, x, y)
    
    def edit_bool(self, item, key, current_value, x, y):
        """Create combobox for boolean values with proper positioning"""
        combo = ttk.Combobox(self.tree, values=["true", "false"], state="readonly")
        combo.set(current_value)
        combo.place(in_=self.tree, x=x, y=y, anchor="nw", width=100)
        
        combo.bind("<<ComboboxSelected>>", lambda e, i=item, k=key: self.save_combo(combo, i, k))
        combo.bind("<FocusOut>", lambda e: combo.destroy())
        combo.focus_set()
    
    def edit_int(self, item, key, current_value, x, y):
        """Create entry for integer values with proper positioning"""
        entry = ttk.Entry(self.tree)
        entry.insert(0, current_value)
        entry.place(in_=self.tree, x=x, y=y, anchor="nw", width=100)
        
        entry.bind("<Return>", lambda e, i=item, k=key: self.save_entry(entry, i, k))
        entry.bind("<FocusOut>", lambda e: entry.destroy())
        entry.focus_set()
    
    def edit_str(self, item, key, current_value, x, y):
        """Create entry for string values with proper positioning"""
        entry = ttk.Entry(self.tree)
        entry.insert(0, current_value)
        entry.place(in_=self.tree, x=x, y=y, anchor="nw", width=300)
        
        entry.bind("<Return>", lambda e, i=item, k=key: self.save_string(entry, i, k))
        entry.bind("<FocusOut>", lambda e: entry.destroy())
        entry.focus_set()
    
    def save_combo(self, combo, item, key):
        """Save boolean value from combobox"""
        new_value = combo.get()
        self.tree.set(item, "Value", new_value)
        
        # Update stored value
        for i, (k, v) in enumerate(self.original_vars):
            if k == key:
                self.original_vars[i] = (key, new_value == "true")
                break
        
        combo.destroy()
        self.status.config(text=f"Updated {key} to {new_value}")
    
    def save_entry(self, entry, item, key):
        """Save integer value from entry"""
        new_value = entry.get()
        
        # Validate integer input
        if new_value.lstrip('-').isdigit():
            self.tree.set(item, "Value", new_value)
            
            # Update stored value
            for i, (k, v) in enumerate(self.original_vars):
                if k == key:
                    self.original_vars[i] = (key, int(new_value))
                    break
            
            self.status.config(text=f"Updated {key} to {new_value}")
        else:
            self.status.config(text="Invalid integer value")
        
        entry.destroy()
    
    def save_string(self, entry, item, key):
        """Save string value from entry"""
        new_value = entry.get()
        self.tree.set(item, "Value", new_value)
        
        # Update stored value
        for i, (k, v) in enumerate(self.original_vars):
            if k == key:
                self.original_vars[i] = (key, new_value)
                break
        
        entry.destroy()
        self.status.config(text=f"Updated {key} to {new_value}")
    
    def save_savegame(self):
        """Save changes back to the savegame file with backup"""
        if not self.file_path:
            return
            
        # Create backup
        backup_path = self.file_path + ".bak"
        try:
            if os.path.exists(self.file_path):
                shutil.copy2(self.file_path, backup_path)
                self.status.config(text=f"Created backup: {os.path.basename(backup_path)}")
        except Exception as e:
            messagebox.showerror("Backup Error", f"Failed to create backup:\n{str(e)}")
            return
        
        # Load the original save data
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load savegame for saving:\n{str(e)}")
            return
        
        # Rebuild the variables string
        var_str = "Variable={"
        for i, (key, value) in enumerate(self.original_vars):
            if isinstance(value, bool):
                val_str = "true" if value else "false"
            elif isinstance(value, int):
                val_str = str(value)
            elif isinstance(value, str):
                val_str = f'"{value}"'  # Add quotes around strings
            else:
                val_str = str(value)
                
            var_str += f'["{key}"]={val_str}'
            if i < len(self.original_vars) - 1:
                var_str += ", "
        var_str += "};"
        
        # Update the save data
        save_data["variables"] = var_str
        
        # Save the modified file
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, separators=(',', ':'))
            self.status.config(text=f"Saved: {os.path.basename(self.file_path)}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save file:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SaveGameEditor(root)
    root.mainloop()