import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
from pathlib import Path
import shutil
import zipfile
import json
import os
import re
import threading
import tempfile
from datetime import datetime

# --- SETTINGS ΕΜΦΑΝΙΣΗΣ ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class HelpWindow(ctk.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("DevToolbox Guide v16.5")
        self.geometry("750x850")
        self.attributes('-topmost', True)
        self.configure(fg_color="#141414")

        help_text = """
### 📖 ΟΔΗΓΟΣ ΛΕΙΤΟΥΡΓΙΩΝ DevToolbox v16.5

⚡ ΝΕΟ: ΕΞΥΠΝΗ ΜΑΖΙΚΗ ΑΝΤΙΚΑΤΑΣΤΑΣΗ ΣΕ ZIP (Merge & Overwrite)!
Όταν κάνετε "Μαζική Αντιγραφή" ενός φακέλου μέσα σε ZIP αρχεία:
• Αν κάποια αρχεία προϋπάρχουν, αντικαθίστανται αυτόματα από τα νέα.
• Αν υπάρχουν επιπλέον αρχεία μέσα στο ZIP που δεν επηρεάζονται, παραμένουν ανέπαφα!

📅 SCHEDULE MANAGER:
• Κάνε ΔΙΠΛΟ ΚΛΙΚ πάνω σε οποιοδήποτε Schedule στον πίνακα.
• Στο αναδυόμενο παράθυρο, μπορείς να πατήσεις "❌ Delete" δίπλα από ένα project για να διαγραφεί ΜΟΝΟ αυτό.
        """
        self.textbox = ctk.CTkTextbox(self, font=("Segoe UI", 14), corner_radius=15, fg_color="#1a1a1a")
        self.textbox.pack(padx=25, pady=25, fill="both", expand=True)
        self.textbox.insert("0.0", help_text)
        self.textbox.configure(state="disabled")


class ScheduleDetailsWindow(ctk.CTkToplevel):
    def __init__(self, schedule_title, items, main_app, tree_item_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title(f"Details: {schedule_title}")
        self.geometry("850x550")
        self.attributes('-topmost', True)
        self.configure(fg_color="#121212")

        self.schedule_title = schedule_title
        self.items = items
        self.main_app = main_app
        self.tree_item_id = tree_item_id

        ctk.CTkLabel(self, text=f"📅 Projects for: {schedule_title}", font=("Segoe UI", 16, "bold"), text_color="#3a7ebf").pack(pady=15, padx=20, anchor="w")

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#1a1a1a", border_width=1, border_color="#292929", corner_radius=12)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.render_project_list()

    def render_project_list(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        if not self.items:
            ctk.CTkLabel(self.scroll_frame, text="All projects deleted from this group.", font=("Segoe UI", 13, "italic"), text_color="#777").pack(pady=20)
            return

        for idx, item in enumerate(self.items):
            p_path = item["path"]
            p_type = item["type"]
            
            item_f = ctk.CTkFrame(self.scroll_frame, fg_color="#222222", corner_radius=8, height=50)
            item_f.pack(fill="x", pady=4, padx=5)
            item_f.pack_propagate(False)

            prefix = "📦 [ZIP] " if p_type == "ZIP" else "📁 [DIR] "
            ctk.CTkLabel(item_f, text=f"{prefix}{p_path.name}", font=("Segoe UI", 12, "bold"), text_color="#ffffff").pack(side="left", padx=15)
            ctk.CTkLabel(item_f, text=str(p_path.parent), font=("Consolas", 10), text_color="#777").pack(side="left", padx=10)

            btn_frame = ctk.CTkFrame(item_f, fg_color="transparent")
            btn_frame.pack(side="right", padx=5)

            target_dir = p_path.parent if p_type == "ZIP" else p_path
            
            ctk.CTkButton(btn_frame, text="Open Folder", width=95, height=28, fg_color="#3a7ebf", hover_color="#295987", 
                           font=("Segoe UI", 11, "bold"), command=lambda d=target_dir: os.startfile(d)).pack(side="left", padx=4)

            ctk.CTkButton(btn_frame, text="❌ Delete", width=85, height=28, fg_color="#c0392b", hover_color="#a0281d",
                           font=("Segoe UI", 11, "bold"), command=lambda i=idx: self.delete_single_project(i)).pack(side="left", padx=4)

    def delete_single_project(self, index):
        item = self.items[index]
        p_path = item["path"]
        p_type = item["type"]

        if messagebox.askyesno("Επιβεβαίωση", f"Θέλετε σίγουρα να διαγράψετε οριστικά το project;\n{p_path.name}"):
            try:
                if p_type == "Folder" and p_path.exists():
                    shutil.rmtree(p_path)
                elif p_type == "ZIP" and p_path.exists():
                    os.remove(p_path)
                
                self.main_app.log_message(f"Deleted specific project: {p_path.name}")
                self.items.pop(index)
                
                self.after(0, self.render_project_list)
                self.after(0, lambda: self.main_app.refresh_treeview_item(self.tree_item_id, self.schedule_title, len(self.items)))

            except Exception as e:
                messagebox.showerror("Σφάλμα", f"Αδυναμία διαγραφής αρχείου/φακέλου:\n{e}")


class DevToolboxApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        try:
            self.TkDnDVersion = TkinterDnD._require(self)
        except Exception as e:
            print(f"DND Error: {e}")

        self.title("DevToolbox v16.5")
        self.geometry("1150x980")
        self.configure(fg_color="#0f0f0f")

        self.paths = {
            "replace": "", "val": "", "rename": "",
            "dest": "", "zip": "", "mkdir": "", "shift": "", "sch_root": ""
        }
        self.source_paths = []
        self.path_labels = {}
        self.grouped_results = {}

        # --- HEADER ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=30, pady=(20, 10))

        ctk.CTkLabel(self.header_frame, text="DevToolbox", font=("Segoe UI", 32, "bold"), text_color="#ffffff").pack(side="left")
        ctk.CTkLabel(self.header_frame, text="PRO MERGE EDITION v16.5", font=("Segoe UI", 12, "bold"), text_color="#2ecc71").pack(side="left", padx=10, pady=(12, 0))

        self.help_btn = ctk.CTkButton(self.header_frame, text="?", width=38, height=38, corner_radius=10, fg_color="#222", hover_color="#333", font=("Arial", 16, "bold"), command=self.open_help)
        self.help_btn.pack(side="right")

        # --- TABS ---
        self.tabview = ctk.CTkTabview(self, segmented_button_fg_color="#1a1a1a", segmented_button_selected_color="#3a7ebf", segmented_button_selected_hover_color="#4a8ecf", corner_radius=15)
        self.tabview.pack(padx=20, pady=(5, 0), fill="both", expand=True)

        self.tab_sch = self.tabview.add("Schedules")
        self.tab_replace = self.tabview.add("Αντικατάσταση")
        self.tab_shift = self.tabview.add("Shifter")
        self.tab_validator = self.tabview.add("JSON Validator")
        self.tab_rename = self.tabview.add("Bulk Rename")
        self.tab_copy = self.tabview.add("Μαζική Αντιγραφή")
        self.tab_zip = self.tabview.add("Zip / Unzip")
        self.tab_mkdir = self.tabview.add("Folders")

        # --- FOOTER / LOGS ---
        self.footer_frame = ctk.CTkFrame(self, fg_color="#141414", corner_radius=0)
        self.footer_frame.pack(fill="x", side="bottom")

        self.prog_frame = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        self.prog_frame.pack(fill="x", padx=30, pady=(15, 5))

        self.progress_bar = ctk.CTkProgressBar(self.prog_frame, mode="determinate", height=10, progress_color="#2ecc71", fg_color="#222")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", side="left", expand=True)

        self.log_text = ctk.CTkTextbox(self.footer_frame, height=140, font=("Consolas", 12), state="disabled", fg_color="#0a0a0a", text_color="#00FF00", border_width=1, border_color="#222")
        self.log_text.pack(padx=20, pady=(5, 20), fill="x")

        self.setup_ui()

    def open_help(self):
        """ Ανοίγει το Help Window με ασφάλεια """
        help_win = HelpWindow(self)
        help_win.focus()

    def create_card(self, master, title):
        f = ctk.CTkFrame(master, fg_color="#1a1a1a", corner_radius=15, border_width=1, border_color="#292929")
        f.pack(padx=20, pady=10, fill="x")
        ctk.CTkLabel(f, text=title, font=("Segoe UI", 15, "bold"), text_color="#3a7ebf").pack(pady=(12, 8), padx=20, anchor="w")
        return f

    def create_preview_box(self, master):
        box = ctk.CTkTextbox(master, height=100, fg_color="#0f0f0f", font=("Consolas", 11), text_color="#3498db", state="disabled", border_width=1, border_color="#222", corner_radius=10)
        box.pack(padx=20, pady=5, fill="x")
        return box

    def setup_ui(self):
        # 1. SCHEDULE MANAGER
        f_sch = self.create_card(self.tab_sch, "📅 SCHEDULE SCANNER (💡 DOUBLE CLICK ROW TO EDIT INDIVIDUAL PROJECTS)")
        self.create_hybrid_input(f_sch, "Root Folder:", "sch_root")

        opt_f = ctk.CTkFrame(f_sch, fg_color="transparent")
        opt_f.pack(fill="x", padx=25, pady=5)
        self.sch_filename_entry = ctk.CTkEntry(opt_f, width=200, height=35, corner_radius=8, border_color="#333")
        self.sch_filename_entry.insert(0, "config.json")
        self.sch_filename_entry.pack(side="left")

        ctk.CTkButton(opt_f, text="SCAN PROJECTS", fg_color="#3a7ebf", height=35, corner_radius=8, command=lambda: self.run_threaded(self.run_schedule_scan)).pack(side="left", padx=10)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#1a1a1a", foreground="white", fieldbackground="#1a1a1a", borderwidth=0, rowheight=30)
        style.map("Treeview", background=[('selected', '#3a7ebf')])
        style.configure("Treeview.Heading", background="#252525", foreground="white", borderwidth=0, font=("Segoe UI", 10, "bold"))

        self.tree = ttk.Treeview(self.tab_sch, columns=("schedule", "count"), show="headings", height=12)
        self.tree.heading("schedule", text="Schedule Time (From - To)")
        self.tree.heading("count", text="Items")
        self.tree.column("schedule", width=700)
        self.tree.column("count", width=100, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=30, pady=10)

        self.tree.bind("<Double-1>", self.on_tree_double_click)

        ctk.CTkButton(self.tab_sch, text="DELETE SELECTED GROUPS", fg_color="#c0392b", hover_color="#922b21", height=45, corner_radius=12, font=("Segoe UI", 13, "bold"), command=lambda: self.run_threaded(self.run_schedule_delete)).pack(pady=15)

        # 2. REPLACE
        f_rep = self.create_card(self.tab_replace, "📁 PROJECT SELECTOR")
        self.create_hybrid_input(f_rep, "Target Path:", "replace")

        f_rep_opts = ctk.CTkFrame(f_rep, fg_color="transparent")
        f_rep_opts.pack(fill="x", padx=25, pady=5)

        self.search_all_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(f_rep_opts, text="Search ALL files", variable=self.search_all_var).pack(side="left", padx=15)

        self.ext_entry = ctk.CTkEntry(f_rep_opts, width=180, height=32, corner_radius=8)
        self.ext_entry.insert(0, ".html, .js, .json")
        self.ext_entry.pack(side="right")

        ctk.CTkLabel(self.tab_replace, text="Find String:", font=("Segoe UI", 12, "bold")).pack(padx=30, anchor="w")
        self.text_find = ctk.CTkTextbox(self.tab_replace, height=80, fg_color="#161616", border_width=1, border_color="#292929")
        self.text_find.pack(padx=25, pady=5, fill="x")

        ctk.CTkLabel(self.tab_replace, text="Replace With:", font=("Segoe UI", 12, "bold")).pack(padx=30, anchor="w")
        self.text_replace = ctk.CTkTextbox(self.tab_replace, height=80, fg_color="#161616", border_width=1, border_color="#292929")
        self.text_replace.pack(padx=25, pady=5, fill="x")

        ctk.CTkButton(self.tab_replace, text="EXECUTE REPLACEMENT", fg_color="#2ecc71", hover_color="#27ae60", height=45, corner_radius=12, font=("Segoe UI", 14, "bold"), command=lambda: self.run_threaded(self.run_replace)).pack(pady=20)

        # 3. SHIFTER
        f_sh = self.create_card(self.tab_shift, "🔄 STRING SHIFTER")
        self.shift_depth_var = tk.IntVar(value=1)
        self.create_hybrid_input(f_sh, "Target Folder:", "shift", lambda: self.update_preview_list("shift", self.shift_depth_var.get(), self.shift_preview))

        self.shift_zip_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(f_sh, text="Process inside ZIPs", variable=self.shift_zip_var).pack(padx=25, pady=5, anchor="w")

        ctk.CTkSlider(f_sh, from_=1, to=5, variable=self.shift_depth_var, button_color="#3a7ebf", command=lambda v: self.update_preview_list("shift", self.shift_depth_var.get(), self.shift_preview)).pack(padx=50, pady=10, fill="x")
        self.shift_preview = self.create_preview_box(f_sh)
        ctk.CTkButton(self.tab_shift, text="RUN SHIFTER", fg_color="#3498db", height=40, corner_radius=10, command=lambda: self.run_threaded(self.run_string_shift)).pack(pady=10)

        # 4. VALIDATOR
        f_v = self.create_card(self.tab_validator, "✅ JSON HEALTH CHECK")
        self.val_depth_var = tk.IntVar(value=1)
        self.create_hybrid_input(f_v, "Path:", "val", lambda: self.update_preview_list("val", self.val_depth_var.get(), self.val_preview, False))
        ctk.CTkSlider(f_v, from_=1, to=5, variable=self.val_depth_var, command=lambda v: self.update_preview_list("val", self.val_depth_var.get(), self.val_preview, False)).pack(padx=50, fill="x")
        self.val_preview = self.create_preview_box(f_v)
        ctk.CTkButton(self.tab_validator, text="VALIDATE & FORMAT", fg_color="#e67e22", height=40, command=lambda: self.run_threaded(self.run_validator)).pack(pady=10)

        # 5. RENAME
        f_r = self.create_card(self.tab_rename, "✏️ BULK RENAME")
        self.rename_depth_var = tk.IntVar(value=1)
        self.create_hybrid_input(f_r, "Root Folder:", "rename", lambda: self.update_preview_list("rename", self.rename_depth_var.get(), self.rename_preview))

        rn_f = ctk.CTkFrame(f_r, fg_color="transparent")
        rn_f.pack(fill="x", padx=20, pady=5)
        self.rename_find = ctk.CTkEntry(rn_f, placeholder_text="Find text...", height=32, corner_radius=8)
        self.rename_find.pack(side="left", expand=True, fill="x", padx=5)
        self.rename_replace = ctk.CTkEntry(rn_f, placeholder_text="Replace with...", height=32, corner_radius=8)
        self.rename_replace.pack(side="left", expand=True, fill="x", padx=5)

        ctk.CTkSlider(f_r, from_=1, to=5, variable=self.rename_depth_var, command=lambda v: self.update_preview_list("rename", self.rename_depth_var.get(), self.rename_preview)).pack(padx=50, pady=10, fill="x")
        self.rename_preview = self.create_preview_box(f_r)
        ctk.CTkButton(self.tab_rename, text="RENAME ALL", fg_color="#9b59b6", height=40, command=lambda: self.run_threaded(self.run_rename)).pack(pady=10)

        # 6. COPY 
        f_c = self.create_card(self.tab_copy, "📂 MULTI-SOURCE COPY (INTELLIGENT MERGE & OVERWRITE)")
        self.src_drop_area = ctk.CTkLabel(f_c, text="DRAG & DROP FOLDERS/FILES HERE", fg_color="#121212", height=50, corner_radius=10, text_color="#444")
        self.src_drop_area.pack(padx=20, pady=5, fill="x")
        self.src_drop_area.drop_target_register(DND_FILES)
        self.src_drop_area.dnd_bind('<<Drop>>', self.handle_multi_source_drop)

        self.src_list_frame = ctk.CTkScrollableFrame(f_c, height=100, fg_color="#0f0f0f", border_width=1, border_color="#222")
        self.src_list_frame.pack(padx=20, pady=5, fill="x")

        self.copy_depth_var = tk.IntVar(value=1)
        self.create_hybrid_input(f_c, "Destination Root:", "dest", lambda: self.update_preview_list("dest", self.copy_depth_var.get(), self.copy_preview))
        ctk.CTkSlider(f_c, from_=1, to=5, variable=self.copy_depth_var, command=lambda v: self.update_preview_list("dest", self.copy_depth_var.get(), self.copy_preview)).pack(padx=50, fill="x")
        self.copy_preview = self.create_preview_box(f_c)
        ctk.CTkButton(self.tab_copy, text="START INTELLIGENT COPY", fg_color="#34495e", height=40, command=lambda: self.run_threaded(self.run_mass_copy)).pack(pady=10)

        # 7. ZIP
        f_z = self.create_card(self.tab_zip, "📦 ZIP/UNZIP TOOLS")
        self.zip_depth_var = tk.IntVar(value=1)
        self.create_hybrid_input(f_z, "Root:", "zip", lambda: self.update_preview_list("zip", self.zip_depth_var.get(), self.zip_preview))
        ctk.CTkSlider(f_z, from_=1, to=5, variable=self.zip_depth_var, command=lambda v: self.update_preview_list("zip", self.zip_depth_var.get(), self.zip_preview)).pack(padx=50, fill="x")
        self.zip_preview = self.create_preview_box(f_z)
        self.del_zip_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(f_z, text="Delete source ZIP after extraction", variable=self.del_zip_var).pack(pady=5)

        btn_zf = ctk.CTkFrame(f_z, fg_color="transparent")
        btn_zf.pack(pady=10)
        ctk.CTkButton(btn_zf, text="ZIP ALL", fg_color="#e67e22", width=120, height=35, command=lambda: self.run_threaded(self.run_mass_zip)).pack(side="left", padx=10)
        ctk.CTkButton(btn_zf, text="UNZIP ALL", fg_color="#c0392b", width=120, height=35, command=lambda: self.run_threaded(self.run_mass_unzip)).pack(side="left", padx=10)

        # 8. FOLDER CREATOR
        f_mk = self.create_card(self.tab_mkdir, "🆕 BULK FOLDER CREATOR")
        self.create_hybrid_input(f_mk, "Root Path:", "mkdir")
        self.mkdir_text = ctk.CTkTextbox(f_mk, height=180, fg_color="#111", corner_radius=12, border_width=1, border_color="#292929")
        self.mkdir_text.pack(padx=20, pady=10, fill="x")
        ctk.CTkButton(f_mk, text="GENERATE FOLDERS", fg_color="#2ecc71", height=40, corner_radius=10, command=lambda: self.run_threaded(self.run_mkdir)).pack(pady=10)

    def on_tree_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        
        sch_key = self.tree.item(item_id)['values'][0]
        items = self.grouped_results.get(sch_key, [])
        
        if items:
            details_win = ScheduleDetailsWindow(sch_key, items, self, item_id)
            details_win.focus()
        else:
            self.log_message("No projects available for this schedule group.", is_error=True)

    def refresh_treeview_item(self, item_id, sch_key, remaining_count):
        if remaining_count > 0:
            self.tree.item(item_id, values=(sch_key, remaining_count))
        else:
            try:
                self.tree.delete(item_id)
                if sch_key in self.grouped_results:
                    del self.grouped_results[sch_key]
            except:
                pass

    def run_threaded(self, func):
        def wrapper():
            self.after(0, lambda: self.progress_bar.set(0))
            self.after(0, lambda: self.progress_bar.configure(mode="indeterminate"))
            self.after(0, self.progress_bar.start)
            try:
                func()
            finally:
                self.after(0, self.progress_bar.stop)
                self.after(0, lambda: self.progress_bar.configure(mode="determinate"))
                self.after(0, lambda: self.progress_bar.set(1))

        threading.Thread(target=wrapper, daemon=True).start()

    def run_schedule_scan(self):
        root = self.paths.get("sch_root")
        target_file = self.sch_filename_entry.get()
        if not root: return
        self.after(0, lambda: [self.tree.delete(i) for i in self.tree.get_children()])
        self.grouped_results = {}
        
        for p in Path(root).rglob(target_file):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    sch_str = self.extract_schedule_string(data)
                    if sch_str not in self.grouped_results: self.grouped_results[sch_str] = []
                    self.grouped_results[sch_str].append({"path": p.parent, "type": "Folder"})
            except:
                pass
        for p in Path(root).rglob("*.zip"):
            try:
                with zipfile.ZipFile(p, 'r') as z:
                    for name in z.namelist():
                        if name.endswith(target_file):
                            with z.open(name) as f:
                                data = json.load(f)
                                sch_str = self.extract_schedule_string(data)
                                if sch_str not in self.grouped_results: self.grouped_results[sch_str] = []
                                self.grouped_results[sch_str].append({"path": p, "type": "ZIP"})
            except:
                pass
                
        for sch, items in self.grouped_results.items():
            self.after(0, lambda s=sch, c=len(items): self.tree.insert("", "end", values=(s, c)))
        self.log_message(f"Scan complete. {len(self.grouped_results)} groups found.")

    def extract_schedule_string(self, data):
        sch = data.get("schedule")
        if not sch: return "⚠️ No Schedule Found"
        if not isinstance(sch, dict): return f"Invalid Format: {sch}"
        return f"FROM: {sch.get('from', 'N/A')}  |  TO: {sch.get('to', 'N/A')}"

    def run_schedule_delete(self):
        selected_indices = self.tree.selection()
        if not selected_indices: return
        for idx in selected_indices:
            sch_key = self.tree.item(idx)['values'][0]
            items_to_del = self.grouped_results.get(sch_key, [])
            for item in items_to_del:
                p = item["path"]
                try:
                    if item["type"] == "Folder" and p.exists():
                        shutil.rmtree(p)
                    elif item["type"] == "ZIP" and p.exists():
                        os.remove(p)
                    self.log_message(f"Deleted: {p.name}")
                except:
                    pass
            self.after(0, lambda i=idx: self.tree.delete(i))

    def run_replace(self):
        f_s, r_s = self.text_find.get("1.0", "end-1c"), self.text_replace.get("1.0", "end-1c")
        path = self.paths["replace"]
        if not path or not f_s: return
        
        exts = []
        for raw in self.ext_entry.get().split(","):
            ext = raw.strip().lower()
            if not ext: continue
            if not ext.startswith('.'): ext = '.' + ext
            exts.append(ext)
            
        root_path = Path(path)
        if root_path.is_file() and root_path.suffix.lower() == ".zip":
            self.process_zip_replace(root_path, f_s, r_s, exts)
        elif root_path.is_dir():
            for f in root_path.rglob("*"):
                if f.is_file():
                    if f.suffix.lower() == ".zip":
                        self.process_zip_replace(f, f_s, r_s, exts)
                    elif self.search_all_var.get() or f.suffix.lower() in exts:
                        try:
                            t = f.read_text(encoding='utf-8', errors='ignore')
                            if f_s in t:
                                f.write_text(t.replace(f_s, r_s), encoding='utf-8')
                                self.log_message(f"Updated: {f.name}")
                        except:
                            pass
        self.log_message("✅ Replace process finished.")

    def process_zip_replace(self, zip_path, find_str, replace_str, exts):
        temp_fd, temp_path = tempfile.mkstemp(dir=zip_path.parent)
        os.close(temp_fd)
        found = False
        binary_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.woff', '.woff2', '.ttf', '.mp3', '.mp4')

        try:
            with zipfile.ZipFile(zip_path, 'r') as zin, zipfile.ZipFile(temp_path, 'w', compression=zin.compression) as zout:
                for item in zin.infolist():
                    content = zin.read(item.filename)
                    file_name_lower = item.filename.lower()

                    if self.search_all_var.get():
                        should_search = not file_name_lower.endswith(binary_extensions)
                    elif exts:
                        should_search = any(file_name_lower.endswith(ex) for ex in exts)
                    else:
                        should_search = not file_name_lower.endswith(binary_extensions)

                    if should_search and not item.is_dir():
                        try:
                            text = content.decode('utf-8', errors='ignore')
                            if find_str in text:
                                content = text.replace(find_str, replace_str).encode('utf-8')
                                found = True
                                self.log_message(f"Updated inside ZIP: {zip_path.name} -> {item.filename}")
                        except Exception as encode_err:
                            self.log_message(f"Σφάλμα ανάγνωσης στο ZIP ({item.filename}): {encode_err}", True)

                    zout.writestr(item, content)

            if found:
                try:
                    os.replace(temp_path, zip_path)
                    self.log_message(f"Updated Inside ZIP: {zip_path.name}")
                except OSError as e:
                    self.log_message(f"Αδυναμία αντικατάστασης ZIP: {e}", True)
                    if os.path.exists(temp_path): os.remove(temp_path)
            else:
                if os.path.exists(temp_path): os.remove(temp_path)

        except Exception as general_err:
            self.log_message(f"Κρίσιμο σφάλμα στο ZIP {zip_path.name}: {general_err}", True)
            if os.path.exists(temp_path): os.remove(temp_path)

    def process_zip_json(self, zip_path):
        temp_fd, temp_path = tempfile.mkstemp(dir=zip_path.parent, suffix='.zip')
        os.close(temp_fd)
        changed = False
        try:
            with zipfile.ZipFile(zip_path, 'r') as zin, zipfile.ZipFile(temp_path, 'w') as zout:
                for item in zin.infolist():
                    content = zin.read(item.filename)
                    if item.is_dir() or not item.filename.lower().endswith('.json'):
                        zout.writestr(item, content)
                        continue
                    try:
                        text = content.decode('utf-8', errors='ignore')
                        data = json.loads(text)
                        formatted = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
                        zout.writestr(item, formatted)
                        if formatted != content:
                            changed = True
                            self.log_message(f"Validated JSON inside ZIP: {zip_path.name} -> {item.filename}")
                    except Exception as ex:
                        self.log_message(f"Invalid JSON in ZIP {zip_path.name}:{item.filename} - {ex}", True)
                        zout.writestr(item, content)
            if changed:
                os.replace(temp_path, zip_path)
            else:
                if os.path.exists(temp_path): os.remove(temp_path)
        except Exception as general_err:
            self.log_message(f"ZIP JSON validation error {zip_path.name}: {general_err}", True)
            if os.path.exists(temp_path): os.remove(temp_path)

    def process_zip_rename(self, zip_path, find_str, replace_str):
        temp_fd, temp_path = tempfile.mkstemp(dir=zip_path.parent, suffix='.zip')
        os.close(temp_fd)
        changed = False
        try:
            with zipfile.ZipFile(zip_path, 'r') as zin, zipfile.ZipFile(temp_path, 'w') as zout:
                for item in zin.infolist():
                    content = zin.read(item.filename)
                    name = item.filename
                    parts = name.split('/')
                    if parts:
                        tail = parts[-1]
                        if find_str in tail:
                            parts[-1] = tail.replace(find_str, replace_str)
                            name = "/".join(parts)
                            if item.is_dir() and not name.endswith('/'):
                                name += '/'
                            changed = True
                            self.log_message(f"Renamed ZIP entry: {zip_path.name} -> {item.filename} -> {name}")
                    if item.is_dir():
                        zout.writestr(name, b'')
                    else:
                        zout.writestr(name, content, compress_type=item.compress_type)
            if changed:
                os.replace(temp_path, zip_path)
            else:
                if os.path.exists(temp_path): os.remove(temp_path)
        except Exception as general_err:
            self.log_message(f"ZIP rename error {zip_path.name}: {general_err}", True)
            if os.path.exists(temp_path): os.remove(temp_path)

    def run_validator(self):
        root = self.paths["val"]
        if not root: return
        path = Path(root)
        if path.is_file() and path.suffix.lower() == ".zip":
            self.process_zip_json(path)
            return

        files = self.get_items_at_exact_depth(root, self.val_depth_var.get(), False)
        for f in files:
            if f.suffix.lower() == ".json":
                try:
                    with open(f, 'r', encoding='utf-8') as j: d = json.load(j)
                    with open(f, 'w', encoding='utf-8') as j: json.dump(d, j, indent=2, ensure_ascii=False)
                    self.log_message(f"✅ Valid: {f.name}")
                except Exception as e:
                    self.log_message(f"❌ Error: {f.name} - {e}", True)
            elif f.suffix.lower() == ".zip":
                self.process_zip_json(f)

    def run_rename(self):
        f_s, r_s = self.rename_find.get(), self.rename_replace.get()
        root = self.paths["rename"]
        if not root: return
        path = Path(root)
        if path.is_file() and path.suffix.lower() == ".zip":
            self.process_zip_rename(path, f_s, r_s)
            return

        items = self.get_items_at_exact_depth(root, self.rename_depth_var.get(), True)
        for i in items:
            if i.suffix.lower() == ".zip": self.process_zip_rename(i, f_s, r_s)
            if f_s in i.name:
                i.rename(i.parent / i.name.replace(f_s, r_s))
                self.log_message(f"Renamed: {i.name}")

    def run_mass_copy(self):
        targets = self.get_items_at_exact_depth(self.paths["dest"], self.copy_depth_var.get())
        
        for src_p in self.source_paths:
            src = Path(src_p)
            if not src.exists(): continue
            
            for t in targets:
                if t.is_dir():
                    dst = t / src.name
                    if src.is_dir():
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                        self.log_message(f"Merged folder '{src.name}' into folder '{t.name}'")
                    else:
                        shutil.copy2(src, t)
                        self.log_message(f"Copied file '{src.name}' into folder '{t.name}'")
                        
                elif t.is_file() and t.suffix.lower() == ".zip":
                    self.merge_into_zip(src, t)
                    
        self.log_message("✅ Intelligent Mass Copy Finished!")

    def merge_into_zip(self, src_path, zip_path):
        temp_fd, temp_path = tempfile.mkstemp(dir=zip_path.parent, suffix='.zip')
        os.close(temp_fd)
        
        new_files = {} 
        if src_path.is_dir():
            for f in src_path.rglob("*"):
                if f.is_file():
                    arcname = Path(src_path.name) / f.relative_to(src_path)
                    new_files[arcname.as_posix()] = f
        else:
            new_files[src_path.name] = src_path

        try:
            with zipfile.ZipFile(zip_path, 'r') as zin, zipfile.ZipFile(temp_path, 'w', compression=zin.compression) as zout:
                for item in zin.infolist():
                    if item.filename in new_files:
                        continue
                    zout.writestr(item, zin.read(item.filename))
                
                for arcname, local_f in new_files.items():
                    zout.write(local_f, arcname)
            
            os.replace(temp_path, zip_path)
            self.log_message(f"Successfully merged & overwrote items inside ZIP: {zip_path.name}")
            
        except Exception as e:
            self.log_message(f"❌ Error merging into ZIP {zip_path.name}: {e}", True)
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def run_mass_zip(self):
        targets = self.get_items_at_exact_depth(self.paths["zip"], self.zip_depth_var.get(), True)
        for t in targets: shutil.make_archive(str(t), 'zip', t); self.log_message(f"Zipped: {t.name}")

    def run_mass_unzip(self):
        zips = [f for f in self.get_items_at_exact_depth(self.paths["zip"], self.zip_depth_var.get(), False) if f.suffix == ".zip"]
        for z in zips:
            with zipfile.ZipFile(z, 'r') as zr: zr.extractall(z.parent / z.stem)
            if self.del_zip_var.get(): os.remove(z)
            self.log_message(f"Unzipped: {z.name}")

    def run_string_shift(self):
        root = self.paths.get("shift")
        if not root: return
        path = Path(root)
        pattern, depth = r"(\(\d+\))$", self.shift_depth_var.get()

        if path.is_file() and path.suffix.lower() == ".zip":
            if self.shift_zip_var.get(): self.shift_zip_filenames(path, pattern)
            return

        targets = self.get_items_at_exact_depth(root, depth, find_dirs=True) + \
                  [f for f in self.get_items_at_exact_depth(root, depth, find_dirs=False) if f.suffix.lower() == ".zip"]

        for item in targets:
            stem = item.stem
            match = re.search(pattern, stem)
            if match:
                new_name = f"{match.group(1)}{stem[:match.start()]}{item.suffix}"
                item.rename(item.parent / new_name)
                self.log_message(f"Shifted: {item.name} -> {new_name}")

        if self.shift_zip_var.get():
            for z in Path(root).rglob("*.zip"): self.shift_zip_filenames(z, pattern)

    def shift_zip_filenames(self, zip_path, pattern):
        temp = zip_path.with_suffix('.tmp.zip')
        found = False
        try:
            with zipfile.ZipFile(zip_path, 'r') as zin, zipfile.ZipFile(temp, 'w') as zout:
                for name in zin.namelist():
                    parts = name.split('/')
                    filename = parts[-1]
                    if filename:
                        f_stem, f_ext = Path(filename).stem, Path(filename).suffix
                        match = re.search(pattern, f_stem)
                        if match:
                            parts[-1] = f"{match.group(1)}{f_stem[:match.start()]}{f_ext}"
                            name = "/".join(parts)
                            found = True
                    zout.writestr(name, zin.read(name))
            if found:
                os.replace(temp, zip_path)
                self.log_message(f"ZIP Internal Shift: {zip_path.name}")
            else:
                os.remove(temp)
        except:
            pass

    def run_mkdir(self):
        root, names = self.paths["mkdir"], [l.strip() for l in self.mkdir_text.get("1.0", "end-1c").splitlines() if l.strip()]
        if not root: return
        for n in names:
            p = Path(root) / "".join(c for c in n if c not in '<>:"/\\|?*')
            p.mkdir(parents=True, exist_ok=True)
            self.log_message(f"Created: {p.name}")

    # --- UI HELPERS ---
    def handle_multi_source_drop(self, event):
        paths = event.data.strip('{}').split('} {') if '} {' in event.data else [event.data.strip('{}')]
        for p in paths:
            clean_p = p.strip('{}')
            if clean_p not in self.source_paths:
                self.source_paths.append(clean_p)
                f = ctk.CTkFrame(self.src_list_frame, fg_color="#1a1a1a", corner_radius=6)
                f.pack(fill="x", pady=2, padx=5)
                ctk.CTkLabel(f, text=f"📂 {Path(clean_p).name}", font=("Segoe UI", 11)).pack(side="left", padx=10)
                ctk.CTkButton(f, text="X", width=20, height=20, fg_color="#c0392b", command=lambda p=clean_p, fr=f: (self.source_paths.remove(p), fr.destroy())).pack(side="right", padx=5)

    def create_hybrid_input(self, master, label, key, update_fn=None):
        f = ctk.CTkFrame(master, fg_color="transparent")
        f.pack(padx=20, pady=5, fill="x")
        ctk.CTkLabel(f, text=label, font=("Segoe UI", 12, "bold")).pack(side="left")
        ctk.CTkButton(f, text="Browse", width=80, height=28, corner_radius=6, command=lambda: self.browse_path(key, update_fn)).pack(side="right")

        drop = ctk.CTkLabel(master, text="--- drop folder here ---", fg_color="#121212", height=38, corner_radius=10, text_color="#444", font=("Segoe UI", 10))
        drop.pack(pady=5, padx=20, fill="x")
        drop.drop_target_register(DND_FILES)
        drop.dnd_bind('<<Drop>>', lambda e: self.set_path(key, e.data.strip('{}'), update_fn))

        self.path_labels[key] = ctk.CTkLabel(master, text="No selection", text_color="#555", font=("Segoe UI", 11))
        self.path_labels[key].pack(padx=25, anchor="w", pady=(0, 5))
        return drop

    def get_items_at_exact_depth(self, root_path, target_depth, find_dirs=True):
        if not root_path: return []
        res = []

        def rec(p, d):
            if d > target_depth: return
            try:
                for i in p.iterdir():
                    if d == target_depth:
                        if i.is_dir() or i.suffix.lower() == ".zip":
                            res.append(i)
                    elif i.is_dir(): rec(i, d + 1)
            except:
                pass

        rec(Path(root_path), 1)
        return res

    def update_preview_list(self, key, depth, textbox, find_dirs=True):
        root = self.paths[key]
        if not root: return
        items = self.get_items_at_exact_depth(root, depth, find_dirs)
        textbox.configure(state="normal")
        textbox.delete("1.0", "end")
        textbox.insert("end", f"📍 Targets ({len(items)}):\n" + "".join([f" • {i.name}\n" for i in items[:15]]))
        textbox.configure(state="disabled")

    def set_path(self, key, path, update_fn=None):
        self.paths[key] = path
        self.path_labels[key].configure(text=f"📍 {Path(path).name}", text_color="#3a7ebf")
        if update_fn: update_fn()

    def browse_path(self, key, update_fn=None):
        p = filedialog.askdirectory()
        if p: self.set_path(key, p, update_fn)

    def log_message(self, message, is_error=False):
        def _append_log():
            t = datetime.now().strftime("%H:%M:%S")
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"{t} {'[!] ' if is_error else '[>] '} {message}\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.after(0, _append_log)


if __name__ == "__main__":
    app = DevToolboxApp()
    app.mainloop()