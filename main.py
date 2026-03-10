"""
Daily To-Do — Modern, clean UI with Linear/Apple Reminders aesthetic.
"""
import json
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, date, time
from typing import List, Optional
from io import BytesIO

import customtkinter as ctk
from tkinter import messagebox

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore

try:
    import cairosvg
except ImportError:
    cairosvg = None  # type: ignore


TASKS_FILE = os.path.join(os.path.dirname(__file__), "tasks.json")
ICONS_DIR = os.path.join(os.path.dirname(__file__), "icons")

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".svg")
ICON_SIZE = (24, 24)

# Design tokens — Linear/Apple Reminders style
COLORS = {
    "bg": "#FAFAFA",
    "card": "#FFFFFF",
    "card_hover": "#F5F5F5",
    "card_done": "#F0F0F0",
    "text": "#1A1A1A",
    "text_muted": "#8E8E93",
    "accent": "#007AFF",  # System Blue
    "priority_1": "#FF3B30",  # Red
    "priority_2": "#FF9500",  # Orange
    "priority_3": "#8E8E93",  # Gray
    "border": "#E5E5EA",
}
FONT_FAMILY = "SF Pro Display" if sys.platform == "darwin" else "Segoe UI"
FONT_SIZE = 14
FONT_SIZE_SM = 12
CARD_RADIUS = 12
CARD_PADDING = 16
BTN_RADIUS = 10


def _load_and_resize_icon(path: str) -> Optional[ctk.CTkImage]:
    """Load icon (PNG/JPG/GIF/SVG) and return CTkImage scaled to ICON_SIZE.

    - Raster formats use Pillow when available, otherwise CTkImage from path.
    - SVG requires both Pillow and cairosvg; if missing, SVG is skipped (returns None).
    """
    ext = os.path.splitext(path)[1].lower()
    try:
        # SVG handling via cairosvg -> PNG bytes -> Pillow image
        if ext == ".svg":
            if cairosvg is None or Image is None:
                return None
            png_bytes = cairosvg.svg2png(
                url=path,
                output_width=ICON_SIZE[0],
                output_height=ICON_SIZE[1],
            )
            img = Image.open(BytesIO(png_bytes)).convert("RGBA")
            return ctk.CTkImage(light_image=img, dark_image=img, size=ICON_SIZE)

        # Raster formats
        if Image is not None:
            img = Image.open(path).convert("RGBA")
            img = img.resize(ICON_SIZE)
            return ctk.CTkImage(light_image=img, dark_image=img, size=ICON_SIZE)

        # Fallback: let CTkImage load from file path (non-SVG only)
        if ext != ".svg":
            return ctk.CTkImage(light_image=path, dark_image=path, size=ICON_SIZE)
    except Exception:
        return None
    return None


def load_icons_from_folder() -> tuple[list[str], dict[str, Optional[ctk.CTkImage]]]:
    """Scan icons folder for images. Returns (icon_names, name_to_image)."""
    icon_names = [""]
    icon_images: dict[str, Optional[ctk.CTkImage]] = {"": None}

    if not os.path.isdir(ICONS_DIR):
        return icon_names, icon_images

    for name in sorted(os.listdir(ICONS_DIR)):
        if name.startswith("."):
            continue
        base, ext = os.path.splitext(name)
        if ext.lower() not in IMAGE_EXTENSIONS:
            continue
        path = os.path.join(ICONS_DIR, name)
        if not os.path.isfile(path):
            continue
        try:
            img = _load_and_resize_icon(path)
            if img is not None:
                icon_names.append(base)
                icon_images[base] = img
        except Exception:
            continue

    return icon_names, icon_images


DEFAULT_PRIORITY = 2


@dataclass
class Task:
    id: str
    title: str
    due_iso: Optional[str]
    priority: int
    completed: bool
    notified: bool
    created_iso: str
    icon: str

    @property
    def due_datetime(self) -> Optional[datetime]:
        if self.due_iso:
            try:
                return datetime.fromisoformat(self.due_iso)
            except ValueError:
                return None
        return None

    @property
    def created_at(self) -> datetime:
        try:
            return datetime.fromisoformat(self.created_iso)
        except ValueError:
            return datetime.now()


class TaskManager:
    def __init__(self, path: str = TASKS_FILE) -> None:
        self.path = path
        self.tasks: List[Task] = []
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            self.tasks = []
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            self.tasks = []
            return
        self.tasks = []
        for item in data:
            try:
                if "priority" in item:
                    priority = int(item["priority"])
                elif "is_first_priority" in item:
                    priority = 1 if item["is_first_priority"] else 2
                else:
                    priority = DEFAULT_PRIORITY
                priority = max(1, priority)

                task = Task(
                    id=item.get("id", str(uuid.uuid4())),
                    title=item.get("title", ""),
                    due_iso=item.get("due_iso"),
                    priority=priority,
                    completed=bool(item.get("completed", False)),
                    notified=bool(item.get("notified", False)),
                    created_iso=item.get(
                        "created_iso",
                        datetime.now().isoformat(timespec="seconds"),
                    ),
                    icon=item.get("icon", ""),
                )
                self.tasks.append(task)
            except Exception:
                continue

    def _save(self) -> None:
        data = [asdict(t) for t in self.tasks]
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def add_task(
        self,
        title: str,
        due_dt: Optional[datetime],
        priority: int,
        icon: str,
    ) -> Task:
        now = datetime.now()
        task = Task(
            id=str(uuid.uuid4()),
            title=title,
            due_iso=due_dt.isoformat(timespec="minutes") if due_dt else None,
            priority=max(1, priority),
            completed=False,
            notified=False,
            created_iso=now.isoformat(timespec="seconds"),
            icon=icon,
        )
        self.tasks.append(task)
        self._save()
        return task

    def update_task(
        self,
        task_id: str,
        *,
        title: Optional[str] = None,
        due_dt: Optional[datetime] = None,
        clear_due: bool = False,
        priority: Optional[int] = None,
        icon: Optional[str] = None,
    ) -> None:
        task = self.get_task(task_id)
        if not task:
            return
        if title is not None:
            task.title = title
        if clear_due:
            task.due_iso = None
        elif due_dt is not None:
            task.due_iso = due_dt.isoformat(timespec="minutes")
        if priority is not None:
            task.priority = max(1, priority)
        if icon is not None:
            task.icon = icon
        self._save()

    def delete_task(self, task_id: str) -> None:
        self.tasks = [t for t in self.tasks if t.id != task_id]
        self._save()

    def get_task(self, task_id: str) -> Optional[Task]:
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None

    def toggle_complete(self, task_id: str) -> None:
        task = self.get_task(task_id)
        if not task:
            return
        task.completed = not task.completed
        self._save()

    def set_priority(self, task_id: str, priority: int) -> None:
        task = self.get_task(task_id)
        if not task:
            return
        task.priority = max(1, priority)
        self._save()

    def sorted_tasks(self) -> List[Task]:
        def sort_key(task: Task):
            completed_flag = 1 if task.completed else 0
            return (completed_flag, task.priority, task.due_datetime or datetime.max, task.created_at)

        return sorted(self.tasks, key=sort_key)


def show_notification(title: str, message: str) -> None:
    if sys.platform != "darwin":
        return
    safe_title = title.replace('"', "'")
    safe_message = message.replace('"', "'")
    script = f'display notification "{safe_message}" with title "{safe_title}"'
    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def _priority_color(priority: int) -> str:
    if priority == 1:
        return COLORS["priority_1"]
    if priority == 2:
        return COLORS["priority_2"]
    return COLORS["priority_3"]


class AddEditDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        *,
        title: str,
        icon_options: list[str],
        initial_title: str = "",
        initial_due: str = "",
        initial_priority: int = DEFAULT_PRIORITY,
        initial_icon: str = "",
        on_submit=None,
    ) -> None:
        super().__init__(master)
        self.transient(master)
        self.title(title)
        self.resizable(False, False)

        self.on_submit = on_submit
        self.icon_options = icon_options

        self.geometry("420x380")
        self._build_ui()
        self._set_initial(initial_title, initial_due, initial_priority, initial_icon)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.bind("<Return>", lambda e: self._on_ok())
        self.bind("<Escape>", lambda e: self._on_cancel())

        self.entry_title.focus()

    def _build_ui(self) -> None:
        pad = 16
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Task", font=(FONT_FAMILY, FONT_SIZE_SM, "bold")).grid(
            row=0, column=0, sticky="w", padx=pad, pady=(pad, 4)
        )
        self.entry_title = ctk.CTkEntry(
            self, placeholder_text="What needs to be done?", height=40, corner_radius=10
        )
        self.entry_title.grid(row=1, column=0, columnspan=2, sticky="ew", padx=pad, pady=(0, pad))

        ctk.CTkLabel(self, text="Due time (HH:MM)", font=(FONT_FAMILY, FONT_SIZE_SM, "bold")).grid(
            row=2, column=0, sticky="w", padx=pad, pady=(0, 4)
        )
        self.entry_due = ctk.CTkEntry(self, placeholder_text="14:30", height=40, corner_radius=10, width=120)
        self.entry_due.grid(row=3, column=0, sticky="w", padx=pad, pady=(0, pad))

        ctk.CTkLabel(self, text="Priority (1=highest)", font=(FONT_FAMILY, FONT_SIZE_SM, "bold")).grid(
            row=4, column=0, sticky="w", padx=pad, pady=(0, 4)
        )
        self.entry_priority = ctk.CTkEntry(self, height=40, corner_radius=10, width=80)
        self.entry_priority.grid(row=5, column=0, sticky="w", padx=pad, pady=(0, pad))

        ctk.CTkLabel(self, text="Icon", font=(FONT_FAMILY, FONT_SIZE_SM, "bold")).grid(
            row=6, column=0, sticky="w", padx=pad, pady=(0, 4)
        )
        self.combo_icon = ctk.CTkComboBox(
            self, values=self.icon_options, width=160, height=40, corner_radius=10
        )
        self.combo_icon.grid(row=7, column=0, sticky="w", padx=pad, pady=(0, pad))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=8, column=0, columnspan=2, sticky="e", padx=pad, pady=pad)
        ctk.CTkButton(
            btn_frame, text="Cancel", width=100, height=40, corner_radius=BTN_RADIUS,
            fg_color=COLORS["border"], text_color=COLORS["text"], command=self._on_cancel
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            btn_frame, text="Save", width=100, height=40, corner_radius=BTN_RADIUS,
            fg_color=COLORS["accent"], command=self._on_ok
        ).pack(side="right")

    def _set_initial(self, title: str, due: str, priority: int, icon: str) -> None:
        self.entry_title.delete(0, "end")
        self.entry_title.insert(0, title)
        self.entry_due.delete(0, "end")
        self.entry_due.insert(0, due)
        self.entry_priority.delete(0, "end")
        self.entry_priority.insert(0, str(priority))
        if icon in self.icon_options:
            self.combo_icon.set(icon)
        else:
            self.combo_icon.set(self.icon_options[0] if self.icon_options else "")

    def _on_ok(self) -> None:
        title = self.entry_title.get().strip()
        due_str = self.entry_due.get().strip()
        priority_str = self.entry_priority.get().strip()
        icon = self.combo_icon.get().strip()

        if not title:
            messagebox.showwarning("Missing task", "Please enter a task.")
            return

        try:
            priority = int(priority_str) if priority_str else DEFAULT_PRIORITY
            priority = max(1, priority)
        except ValueError:
            messagebox.showwarning("Invalid priority", "Please enter a number (1 = highest).")
            return

        due_dt: Optional[datetime] = None
        if due_str:
            try:
                hh, mm = due_str.split(":")
                hh_i, mm_i = int(hh), int(mm)
                today = date.today()
                due_dt = datetime.combine(today, time(hour=hh_i, minute=mm_i))
            except Exception:
                messagebox.showwarning("Invalid time", "Use HH:MM (24-hour) or leave empty.")
                return

        if self.on_submit:
            self.on_submit(title, due_dt, priority, icon)
        self.destroy()

    def _on_cancel(self) -> None:
        self.destroy()


class TaskCard(ctk.CTkFrame):
    """Single task card with modern styling."""

    def __init__(self, master, task: Task, icon_images: dict, selected: bool = False, on_click=None, on_toggle=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.task = task
        self.icon_images = icon_images
        self.selected = selected
        self.on_click = on_click
        self.on_toggle = on_toggle
        self._card = None
        self._build()

    def _build(self) -> None:
        border_color = COLORS["accent"] if self.selected else COLORS["border"]
        border_width = 2 if self.selected else 1
        self._card = ctk.CTkFrame(
            self,
            fg_color=COLORS["card_done"] if self.task.completed else COLORS["card"],
            corner_radius=CARD_RADIUS,
            border_width=border_width,
            border_color=border_color,
            cursor="hand2",
        )
        self._card.pack(fill="x", pady=4)
        self._card.bind("<Button-1>", lambda e: self._on_card_click())
        self._card.bind("<Enter>", lambda e: self._card.configure(fg_color=COLORS["card_hover"]) if not self.task.completed else None)
        self._card.bind("<Leave>", lambda e: self._card.configure(fg_color=COLORS["card_done"] if self.task.completed else COLORS["card"]))

        inner = ctk.CTkFrame(self._card, fg_color="transparent")
        inner.pack(fill="x", padx=CARD_PADDING, pady=CARD_PADDING)

        # Checkbox
        check_text = "✓" if self.task.completed else "○"
        check_btn = ctk.CTkLabel(
            inner,
            text=check_text,
            font=(FONT_FAMILY, 18),
            text_color=COLORS["accent"] if self.task.completed else COLORS["text_muted"],
            cursor="hand2",
            width=32,
        )
        check_btn.pack(side="left", padx=(0, 12))
        check_btn.bind("<Button-1>", lambda e: self._on_toggle_click())

        # Content
        content = ctk.CTkFrame(inner, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True)
        content.bind("<Button-1>", lambda e: self._on_card_click())
        content.bind("<Enter>", lambda e: self._card.configure(fg_color=COLORS["card_hover"]) if not self.task.completed else None)
        content.bind("<Leave>", lambda e: self._card.configure(fg_color=COLORS["card_done"] if self.task.completed else COLORS["card"]))

        # Task name — bold, strikethrough if done
        name_font = ctk.CTkFont(
            family=FONT_FAMILY, size=FONT_SIZE, weight="bold",
            overstrike=True if self.task.completed else False,
        )
        text_color = COLORS["text_muted"] if self.task.completed else COLORS["text"]
        name_label = ctk.CTkLabel(
            content,
            text=self.task.title,
            font=name_font,
            text_color=text_color,
            anchor="w",
        )
        name_label.pack(fill="x")
        name_label.bind("<Button-1>", lambda e: self._on_card_click())

        # Meta row: icon, due, priority
        meta = ctk.CTkFrame(content, fg_color="transparent")
        meta.pack(fill="x", pady=(6, 0))

        icon_img = self.icon_images.get(self.task.icon) if self.task.icon else None
        if icon_img:
            ctk.CTkLabel(meta, text="", image=icon_img, width=20, height=20).pack(side="left", padx=(0, 8))

        due_text = ""
        if self.task.due_datetime:
            due_text = self.task.due_datetime.strftime("%H:%M")
        if due_text:
            ctk.CTkLabel(
                meta, text=f"🕐 {due_text}", font=(FONT_FAMILY, FONT_SIZE_SM),
                text_color=COLORS["text_muted"]
            ).pack(side="left", padx=(0, 12))

        priority_color = _priority_color(self.task.priority)
        ctk.CTkLabel(
            meta, text=f"P{self.task.priority}", font=(FONT_FAMILY, FONT_SIZE_SM, "bold"),
            text_color=priority_color
        ).pack(side="left")

    def _on_card_click(self) -> None:
        if self.on_click:
            self.on_click(self.task.id)

    def _on_toggle_click(self) -> None:
        if self.on_toggle:
            self.on_toggle(self.task.id)


class TodoApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Daily To-Do")
        self.geometry("560x680")
        self.minsize(400, 500)

        ctk.set_appearance_mode("light")
        self.configure(fg_color=COLORS["bg"])

        self.manager = TaskManager()
        self.icon_options, self.icon_images = load_icons_from_folder()
        self._selected_id: Optional[str] = None

        self._build_ui()
        self.refresh_tasks()
        self._schedule_reminder_check()

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(24, 16))

        today_str = date.today().strftime("%A, %B %d, %Y")
        ctk.CTkLabel(
            header,
            text=f"Today — {today_str}",
            font=(FONT_FAMILY, 22, "bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w")

        # Floating Add button
        add_btn = ctk.CTkButton(
            self,
            text="+ Add Task",
            font=(FONT_FAMILY, FONT_SIZE, "bold"),
            fg_color=COLORS["accent"],
            hover_color="#0056B3",
            height=48,
            corner_radius=BTN_RADIUS,
            command=self._on_add_task,
        )
        add_btn.pack(fill="x", padx=24, pady=(0, 20))

        # Scrollable task list
        self.scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["text_muted"],
        )
        self.scroll.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        # Bottom toolbar
        toolbar = ctk.CTkFrame(self, fg_color=COLORS["card"], height=64, corner_radius=0)
        toolbar.pack(fill="x", side="bottom")
        toolbar.pack_propagate(False)

        btn_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_frame.pack(expand=True, pady=12)

        for label, cmd in [
            ("Edit", self._on_edit_task),
            ("Delete", self._on_delete_task),
            ("Toggle Done", self._on_toggle_done),
            ("Set Priority", self._on_set_priority),
        ]:
            btn = ctk.CTkButton(
                btn_frame,
                text=label,
                font=(FONT_FAMILY, FONT_SIZE_SM),
                fg_color=COLORS["border"],
                hover_color=COLORS["card_hover"],
                text_color=COLORS["text"],
                height=36,
                corner_radius=BTN_RADIUS,
                width=100,
                command=cmd,
            )
            btn.pack(side="left", padx=6)

    def refresh_tasks(self) -> None:
        for w in self.scroll.winfo_children():
            w.destroy()

        for task in self.manager.sorted_tasks():
            card = TaskCard(
                self.scroll,
                task,
                self.icon_images,
                selected=(task.id == self._selected_id),
                on_click=self._on_task_selected,
                on_toggle=self._on_task_toggle,
            )
            card.pack(fill="x")

    def _on_task_selected(self, task_id: str) -> None:
        self._selected_id = task_id
        self.refresh_tasks()

    def _on_task_toggle(self, task_id: str) -> None:
        self.manager.toggle_complete(task_id)
        self.refresh_tasks()

    def _get_selected_task_id(self) -> Optional[str]:
        return self._selected_id

    def _on_add_task(self) -> None:
        def on_submit(title: str, due_dt, priority: int, icon: str):
            self.manager.add_task(title, due_dt, priority, icon)
            self.refresh_tasks()

        AddEditDialog(
            self,
            title="Add Task",
            icon_options=self.icon_options,
            initial_title="",
            initial_due="",
            initial_priority=DEFAULT_PRIORITY,
            initial_icon="",
            on_submit=on_submit,
        )

    def _on_edit_task(self) -> None:
        task_id = self._get_selected_task_id()
        if not task_id:
            messagebox.showinfo("Edit Task", "Select a task first (click on it).")
            return
        task = self.manager.get_task(task_id)
        if not task:
            return

        initial_due = task.due_datetime.strftime("%H:%M") if task.due_datetime else ""

        def on_submit(title: str, due_dt, priority: int, icon: str):
            clear_due = due_dt is None and not initial_due
            self.manager.update_task(
                task_id, title=title, due_dt=due_dt, clear_due=clear_due, priority=priority, icon=icon
            )
            self.refresh_tasks()

        AddEditDialog(
            self,
            title="Edit Task",
            icon_options=self.icon_options,
            initial_title=task.title,
            initial_due=initial_due,
            initial_priority=task.priority,
            initial_icon=task.icon,
            on_submit=on_submit,
        )

    def _on_delete_task(self) -> None:
        task_id = self._get_selected_task_id()
        if not task_id:
            messagebox.showinfo("Delete Task", "Select a task first.")
            return
        task = self.manager.get_task(task_id)
        if not task:
            return
        if not messagebox.askyesno("Delete Task", f"Delete:\n\n{task.title}?"):
            return
        self.manager.delete_task(task_id)
        self.refresh_tasks()

    def _on_toggle_done(self) -> None:
        task_id = self._get_selected_task_id()
        if not task_id:
            messagebox.showinfo("Toggle Done", "Select a task first.")
            return
        self.manager.toggle_complete(task_id)
        self.refresh_tasks()

    def _on_set_priority(self) -> None:
        task_id = self._get_selected_task_id()
        if not task_id:
            messagebox.showinfo("Set Priority", "Select a task first.")
            return
        task = self.manager.get_task(task_id)
        if not task:
            return

        d = ctk.CTkToplevel(self)
        d.title("Set Priority")
        d.geometry("320x160")
        d.transient(self)
        d.resizable(False, False)

        ctk.CTkLabel(d, text="Priority (1=highest)", font=(FONT_FAMILY, FONT_SIZE_SM, "bold")).pack(pady=(20, 8))
        entry = ctk.CTkEntry(d, width=80, height=40, corner_radius=10)
        entry.pack(pady=8)
        entry.insert(0, str(task.priority))

        def on_ok():
            try:
                p = max(1, int(entry.get()))
                self.manager.set_priority(task_id, p)
                self.refresh_tasks()
                d.destroy()
            except ValueError:
                messagebox.showwarning("Invalid priority", "Enter a number (1 = highest).")

        btn_f = ctk.CTkFrame(d, fg_color="transparent")
        btn_f.pack(pady=16)
        ctk.CTkButton(btn_f, text="Cancel", width=80, command=d.destroy).pack(side="left", padx=4)
        ctk.CTkButton(btn_f, text="OK", width=80, fg_color=COLORS["accent"], command=on_ok).pack(side="left")

    def _schedule_reminder_check(self) -> None:
        self.after(60_000, self._check_due_tasks)

    def _check_due_tasks(self) -> None:
        now = datetime.now()
        changed = False
        for task in self.manager.tasks:
            if task.completed or task.notified or not task.due_datetime:
                continue
            if now >= task.due_datetime:
                show_notification("Daily To-Do", f'"{task.title}" is due.')
                task.notified = True
                changed = True
        if changed:
            self.manager._save()
            self.refresh_tasks()
        self._schedule_reminder_check()


def main() -> None:
    app = TodoApp()
    app.mainloop()


if __name__ == "__main__":
    main()
