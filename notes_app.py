import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
from pathlib import Path
import re
import sys

# ---------- Storage ----------
def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent

current_folder = None
def notes_dir() -> Path:
    base = app_dir() / "notes"
    base.mkdir(exist_ok=True)
    if current_folder:
        folder = base / current_folder
        folder.mkdir(exist_ok=True)
        return folder
    return base

def slugify(title: str) -> str:
    slug = title.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"\s+", "_", slug)   
    slug = re.sub(r"_+", "_", slug)     
    slug = slug[:80] or "untitled"
    return f"{slug}.txt"

def list_folders():
    base = app_dir() / "notes"
    return [f.name for f in base.iterdir() if f.is_dir()]

def list_notes():
    out = []
    for p in notes_dir().glob("*.txt"):
        title = p.stem.replace("_", " ").title()
        out.append((title, p))
    return sorted(out, key=lambda t: t[0])

def read_notes(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""
    
def write_note(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")

def resource_path(rel: str) -> str:
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / rel)
    candidates.append(app_dir() / rel)

    for p in candidates:
        if p.exists():
            return str(p)
    return str(app_dir() / rel)

# ---------- Editor Window ----------
def open_editor(parent: tk.Tk, title: str, path: Path):
    win = tk.Toplevel(parent)
    win.title(f"Edit - {title}")
    win.geometry("600x400")

    txt = tk.Text(win, wrap="word", undo=True)
    txt.pack(fill="both", expand=True, padx=10, pady=10)

    txt.insert("1.0", read_notes(path))
    txt.edit_reset()
    txt.focus_set()

    status = tk.StringVar(value="Saved")
    tk.Label(win, textvariable=status, anchor="w").pack(fill="x", padx=10, pady=(0,8))

    def mark_dirty(_evt=None):
        status.set("Unsaved...")
    txt.bind("<<Modified>>", lambda e: (txt.edit_modified(0), mark_dirty()))

    def do_save():
        write_note(path, txt.get("1.0", "end-1c"))
        status.set("Saved")
        old = win.title()
        win.title("Saved")
        win.after(600, lambda: win.title(old))

    def do_save_and_close():
        do_save()
        win.destroy()

    bar = tk.Frame(win); bar.pack(pady=(0,10))
    tk.Button(bar, text="Save", command=do_save).pack(side="left", padx=6)
    tk.Button(bar, text="Save & Close", command=do_save_and_close).pack(side="left", padx=6)

    win.bind("<Control-s>", lambda e: (do_save(), "break"))

    def on_close():
        if status.get() != "Saved":
            if messagebox.askyesno("Unsaved changes", "Save before closing?", parent=win):
                do_save()
        win.destroy()
    win.protocol("WM_DELETE_WINDOW", on_close)

# ---------- Home Screen ----------
# Styling colors
BG = "#23272e"    
FG = "#e0e0e0"     
BTN_BG = "#2c313c"  
BTN_FG = "#e0e0e0"  
ENTRY_BG = "#23272e"
ENTRY_FG = "#e0e0e0"
def build_ui():
    root = tk.Tk()
    root.title("Notepads")
    ico_path = resource_path("notepad.ico")
    root.iconbitmap(ico_path)

    root.configure(bg=BG)

    tk.Label(root, text="Your Notes", font=("Segoe UI", 14, "bold"),
             bg=BG, fg=FG).pack(anchor="w", padx=10, pady=(10,0))

    list_frame = tk.Frame(root, bg=BG); list_frame.pack(fill="both", expand=True, padx=10, pady=10)
    sb = tk.Scrollbar(list_frame, orient="vertical")
    lb = tk.Listbox(list_frame, height=12, activestyle="dotbox", yscrollcommand=sb.set,
                    bg=ENTRY_BG, fg=ENTRY_FG, selectbackground="#444", selectforeground=FG)
    sb.config(command=lb.yview)
    lb.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    bar = tk.Frame(root, bg=BG); bar.pack(pady=(0,10))
    btn_new_folder = tk.Button(bar, text="New Folder", bg=BTN_BG, fg=BTN_FG, activebackground="#444")
    btn_new = tk.Button(bar, text="Create New", bg=BTN_BG, fg=BTN_FG, activebackground="#444")
    btn_open = tk.Button(bar, text="Open", bg=BTN_BG, fg=BTN_FG, activebackground="#444")
    btn_rename = tk.Button(bar, text="Rename", bg=BTN_BG, fg=BTN_FG, activebackground="#444")
    btn_delete = tk.Button(bar, text="Delete", bg=BTN_BG, fg=BTN_FG, activebackground="#444")
    btn_refresh = tk.Button(bar, text="Refresh", bg=BTN_BG, fg=BTN_FG, activebackground="#444")
    for b in (btn_new_folder, btn_new, btn_open, btn_rename, btn_delete, btn_refresh):
        b.pack(side="left", padx=6)

    def refresh_list():
        lb.delete(0, tk.END)
        for folder in list_folders():
            lb.insert(tk.END, f"[Folder] {folder}")
        for title, _path in list_notes():
            lb.insert(tk.END, title)
    refresh_list()

    def selected_path() -> Path | None:
        idxs = lb.curselection()
        if not idxs:
            messagebox.showinfo("Select a note", "Choose a note from the list first.", parent=root)
            return None
        item = lb.get(idxs[0])
        if item.startswith("[Folder] "):
            global current_folder
            current_folder = item.replace("[Folder] ", "")
            refresh_list()
            return None
        title = lb.get(idxs[0])
        filename = slugify(title)
        p = notes_dir() / filename
        if not p.exists():
            for _t, p2 in list_notes():
                if _t.lower() == title.lower():
                    return p2
            messagebox.showerror("Missing file", f"Could not find file for '{title}'.", parent=root)
            return None
        return p
    
    def create_folder():
        name = simpledialog.askstring("New Folder", "Folder name:", parent=root)
        if not name:
            return
        folder = app_dir() / "notes" / name
        if folder.exists():
            messagebox.showerror("Exists", f"Folder '{name}' already exists.", parent=root)
            return
        folder.mkdir()
        refresh_list()
        
    def create_new():
        title = simpledialog.askstring("New note", "Note title:", parent=root)
        if not title:
            return
        path = notes_dir() / slugify(title)
        if path.exists():
            if not messagebox.askyesno("Overwrite?", f"'{title}' already exists. Open it?", parent=root):
                return
            open_editor(root, title, path)
            return
        write_note(path, "")
        refresh_list()
        open_editor(root, title, path)

    def open_selected():
        p = selected_path()
        if not p: return
        title = p.stem.replace("_", " ").title()
        open_editor(root, title, p)
    
    def rename_selected():
        p = selected_path()
        if not p: return
        old_title = p.stem.replace("_", " ").title()
        new_title = simpledialog.askstring("Rename", "New title:", initialvalue=old_title, parent=root)
        if not new_title or new_title == old_title:
            return
        new_path = notes_dir() / slugify(new_title)
        if new_path.exists():
            messagebox.showerror("Exists", f"A note named '{new_title}' already exists.", parent=root)
            return
        try:
            p.rename(new_path)
            refresh_list()
        except Exception as e:
            messagebox.showerror("Rename failed", str(e), parent=root)
        
    def delete_selected():
        p = selected_path()
        if not p: return
        title = p.stem.replace("_", " ").title()
        if messagebox.askyesno("Delete", f"Delete '{title}' permanently?", parent=root):
            try:
                p.unlink()
                refresh_list()
            except Exception as e:
                messagebox.showerror("Delete failed", str(e), parent=root)

    btn_new_folder.config(command=create_folder)
    btn_new.config(command=create_new)
    btn_open.config(command=open_selected)
    btn_rename.config(command=rename_selected)
    btn_delete.config(command=delete_selected)
    btn_refresh.config(command=refresh_list)

    def on_listbox_double_click(event):
        idxs = lb.curselection()
        if not idxs:
            return
        item = lb.get(idxs[0])
        if item.startswith("[Folder] "):
            global current_folder
            current_folder = item.replace("[Folder] ", "")
            refresh_list()
        else:
            # Open the note editor for notes
            title = item
            path = notes_dir() / slugify(title)
            if path.exists():
                open_editor(root, title, path)

    lb.bind("<Double-Button-1>", on_listbox_double_click)

    root.minsize(520, 420)
    return root

if __name__ == "__main__":
    build_ui().mainloop()