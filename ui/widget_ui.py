from __future__ import annotations

from datetime import datetime, date, time
from typing import Optional

import customtkinter as ctk
from tkinter import messagebox

from core.todo_manager import TodoManager, TodoItem


GLASS_BG = "#1C1C1F"  # dark slate
GLASS_CARD = "#26262A"
GLASS_CARD_DONE = "#202024"
TEXT_PRIMARY = "#F9F9FB"
TEXT_MUTED = "#A3A3B0"
ACCENT = "#5E9BFF"

FONT_FAMILY = "SF Pro Display"


class TodoRow(ctk.CTkFrame):
    def __init__(
        self,
        master,
        item: TodoItem,
        *,
        on_toggle,
        on_delete,
        on_update,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.item = item
        self.on_toggle = on_toggle
        self.on_delete = on_delete
        self.on_update = on_update
        self._editing = False
        self._build()

    def _build(self) -> None:
        card = ctk.CTkFrame(
            self,
            fg_color=GLASS_CARD_DONE if self.item.completed else GLASS_CARD,
            corner_radius=14,
        )
        card.pack(fill="x", pady=4)

        card.bind(
            "<Enter>",
            lambda e: card.configure(
                fg_color="#2F2F35" if not self.item.completed else "#25252A"
            ),
        )
        card.bind(
            "<Leave>",
            lambda e: card.configure(
                fg_color=GLASS_CARD_DONE if self.item.completed else GLASS_CARD
            ),
        )

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)

        # checkbox
        check_text = "●" if self.item.completed else "○"
        check = ctk.CTkLabel(
            inner,
            text=check_text,
            font=(FONT_FAMILY, 16),
            text_color=ACCENT if self.item.completed else TEXT_MUTED,
            cursor="hand2",
            width=24,
        )
        check.pack(side="left", padx=(0, 8))
        check.bind("<Button-1>", lambda e: self.on_toggle(self.item.id))

        # text
        text_frame = ctk.CTkFrame(inner, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True)
        self._text_frame = text_frame

        name_font = ctk.CTkFont(
            family=FONT_FAMILY,
            size=13,
            weight="bold",
            overstrike=self.item.completed,
        )
        name = ctk.CTkLabel(
            text_frame,
            text=self.item.title,
            font=name_font,
            text_color=TEXT_MUTED if self.item.completed else TEXT_PRIMARY,
            anchor="w",
        )
        name.pack(fill="x")
        name.bind("<Double-Button-1>", lambda e: self._enter_edit_mode())

        # meta row (due time)
        if self.item.due_datetime:
            due = ctk.CTkLabel(
                text_frame,
                text=self.item.due_datetime.strftime("%H:%M"),
                font=(FONT_FAMILY, 11),
                text_color=TEXT_MUTED,
                anchor="w",
            )
            due.pack(fill="x", pady=(2, 0))
            self._due_label = due
        else:
            self._due_label = None

        # delete button
        delete = ctk.CTkButton(
            inner,
            text="×",
            width=24,
            height=24,
            fg_color="transparent",
            hover_color="#3A3A42",
            text_color=TEXT_MUTED,
            font=(FONT_FAMILY, 16),
            corner_radius=12,
            command=lambda: self.on_delete(self.item.id),
        )
        delete.pack(side="right")

        # edit on double click anywhere on the row
        card.bind("<Double-Button-1>", lambda e: self._enter_edit_mode())
        inner.bind("<Double-Button-1>", lambda e: self._enter_edit_mode())

    def _enter_edit_mode(self) -> None:
        if self._editing:
            return
        self._editing = True

        for child in self._text_frame.winfo_children():
            child.destroy()

        title_entry = ctk.CTkEntry(
            self._text_frame,
            height=28,
            corner_radius=10,
            fg_color="#202025",
            border_color="#2E2E36",
            text_color=TEXT_PRIMARY,
        )
        title_entry.pack(fill="x")
        title_entry.insert(0, self.item.title)

        time_entry = ctk.CTkEntry(
            self._text_frame,
            height=26,
            corner_radius=10,
            fg_color="#202025",
            border_color="#2E2E36",
            text_color=TEXT_PRIMARY,
        )
        time_entry.pack(fill="x", pady=(4, 0))
        if self.item.due_datetime:
            time_entry.insert(0, self.item.due_datetime.strftime("%H:%M"))

        def commit() -> None:
            title = title_entry.get().strip()
            time_str = time_entry.get().strip()
            self.on_update(self.item.id, title, time_str)
            self._editing = False

        def cancel() -> None:
            # revert by reusing current values; outer will refresh UI anyway
            self.on_update(
                self.item.id,
                self.item.title,
                self.item.due_datetime.strftime("%H:%M") if self.item.due_datetime else "",
            )
            self._editing = False

        title_entry.bind("<Return>", lambda e: commit())
        time_entry.bind("<Return>", lambda e: commit())
        title_entry.bind("<Escape>", lambda e: cancel())
        time_entry.bind("<Escape>", lambda e: cancel())

        title_entry.focus()


class GlassTodoWidget(ctk.CTk):
    """Semi-transparent, always-on-top desktop todo widget."""

    def __init__(self) -> None:
        super().__init__()

        self.title("Daily Widget")
        self.geometry("320x420")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.9)

        self.configure(fg_color=GLASS_BG)

        self.manager = TodoManager()
        self._dragging_id: Optional[str] = None
        self._drag_last_index: Optional[int] = None
        self._drag_ghost = None
        self._drag_offset_y = 0
        self._drag_start_y: Optional[int] = None
        self._drag_start_row: Optional[TodoRow] = None

        self._build_ui()
        self._refresh()
        self._schedule_reminders()

    # UI ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # rounded container to fake drop shadow
        container = ctk.CTkFrame(
            self,
            fg_color="#151517",
            corner_radius=18,
        )
        container.pack(fill="both", expand=True, padx=8, pady=8)
        container.pack_propagate(False)

        root = ctk.CTkFrame(
            container,
            fg_color=GLASS_BG,
            corner_radius=18,
        )
        root.pack(fill="both", expand=True, padx=2, pady=2)

        # header
        header = ctk.CTkFrame(root, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 4))

        day = date.today().strftime("%a %d")
        title = ctk.CTkLabel(
            header,
            text=f"Today · {day}",
            font=(FONT_FAMILY, 16, "bold"),
            text_color=TEXT_PRIMARY,
        )
        title.pack(side="left")

        # todo list
        self.scroll = ctk.CTkScrollableFrame(
            root,
            fg_color="transparent",
        )
        self.scroll.pack(fill="both", expand=True, padx=10, pady=(4, 6))

        # input row
        input_row = ctk.CTkFrame(root, fg_color="transparent")
        input_row.pack(fill="x", padx=10, pady=(0, 10))

        self.entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Quick todo…",
            height=32,
            corner_radius=12,
            fg_color="#202025",
            border_color="#2E2E36",
            text_color=TEXT_PRIMARY,
        )
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e: self._on_add())

        self.due_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="HH:MM",
            width=70,
            height=32,
            corner_radius=12,
            fg_color="#202025",
            border_color="#2E2E36",
            text_color=TEXT_PRIMARY,
        )
        self.due_entry.pack(side="left", padx=(8, 0))

        add_btn = ctk.CTkButton(
            input_row,
            text="+",
            width=32,
            height=32,
            corner_radius=16,
            fg_color=ACCENT,
            hover_color="#4C82E0",
            command=self._on_add,
        )
        add_btn.pack(side="left", padx=(8, 0))

        # global shortcuts
        self.bind_all("<Return>", lambda e: self._on_add())
        self.bind_all("<Command-d>", self._fill_current_time)
        self.bind_all("<Command-D>", self._fill_current_time)

        # global drag bindings (work with mouse or trackpad)
        self.bind_all("<Button-1>", self._drag_handle_press)
        self.bind_all("<B1-Motion>", self._drag_handle_motion)
        self.bind_all("<ButtonRelease-1>", self._drag_handle_release)

    def _refresh(self) -> None:
        for w in self.scroll.winfo_children():
            w.destroy()

        for item in self.manager.sorted_items():
            row = TodoRow(
                self.scroll,
                item,
                on_toggle=self._on_toggle,
                on_delete=self._on_delete,
                on_update=self._on_update,
            )
            row.pack(fill="x")

    # interactions --------------------------------------------------------
    def _parse_due(self, s: str) -> Optional[datetime]:
        s = s.strip()
        if not s:
            return None
        try:
            hh, mm = s.split(":")
            hh_i, mm_i = int(hh), int(mm)
            today = date.today()
            return datetime.combine(today, time(hour=hh_i, minute=mm_i))
        except Exception:
            messagebox.showwarning("Invalid time", "Use HH:MM (24‑hour) or leave empty.")
            return None

    def _on_add(self) -> None:
        title = self.entry.get().strip()
        if not title:
            return

        due_raw = self.due_entry.get().strip()
        due = self._parse_due(due_raw) if due_raw else None
        if due_raw and due is None:
            return

        self.manager.add(title, due)
        self.entry.delete(0, "end")
        self.due_entry.delete(0, "end")
        self._refresh()

    def _on_toggle(self, item_id: str) -> None:
        self.manager.toggle_complete(item_id)
        self._refresh()

    def _on_delete(self, item_id: str) -> None:
        self.manager.delete(item_id)
        self._refresh()

    def _on_update(self, item_id: str, title: str, time_str: str) -> None:
        item = self.manager.get(item_id)
        if not item:
            return

        new_title = title.strip() or item.title

        if time_str.strip():
            due = self._parse_due(time_str)
            if due is None:
                return
        else:
            due = None

        self.manager.set_title(item_id, new_title)
        self.manager.set_due(item_id, due)
        self._refresh()

    # drag & drop reordering with ghost -----------------------------------
    def _all_rows(self) -> list[TodoRow]:
        """Return all TodoRow instances inside the scroll area."""
        result: list[TodoRow] = []

        def walk(widget):
            for child in widget.winfo_children():
                if isinstance(child, TodoRow):
                    result.append(child)  # type: ignore[arg-type]
                walk(child)

        walk(self.scroll)
        return result

    def _drag_find_row(self, event) -> Optional[TodoRow]:
        """Return the TodoRow under the cursor within the scroll area."""
        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget is not None and widget is not self.scroll:
            if isinstance(widget, TodoRow):
                return widget  # type: ignore[return-value]
            widget = widget.master
        return None

    def _drag_handle_press(self, event) -> None:
        # only start drag if inside the scrollable list region
        sx = self.scroll.winfo_rootx()
        sy = self.scroll.winfo_rooty()
        sw = self.scroll.winfo_width()
        sh = self.scroll.winfo_height()
        if not (sx <= event.x_root <= sx + sw and sy <= event.y_root <= sy + sh):
            return

        row = self._drag_find_row(event)
        if row is None:
            return
        # record potential drag start; actual drag will begin on motion
        self._drag_start_y = event.y_root
        self._drag_start_row = row
        self._dragging_id = None
        self._drag_last_index = None
        if self._drag_ghost is not None:
            self._drag_ghost.destroy()
            self._drag_ghost = None

    def _drag_handle_motion(self, event) -> None:
        # if we haven't started a drag yet, check movement threshold first
        if self._dragging_id is None:
            if self._drag_start_row is None or self._drag_start_y is None:
                return
            if abs(event.y_root - self._drag_start_y) < 6:
                # small movement: treat as click, not drag
                return

            # begin drag now
            row = self._drag_start_row
            self._dragging_id = row.item.id
            rows = self._all_rows()
            try:
                self._drag_last_index = rows.index(row)
            except ValueError:
                self._drag_last_index = None

            # create ghost overlay at row position
            x = row.winfo_x()
            y = row.winfo_y()
            w = row.winfo_width() or self.scroll.winfo_width() - 4
            h = row.winfo_height() or 36

            self._drag_offset_y = event.y_root - row.winfo_rooty()

            ghost = ctk.CTkFrame(
                self.scroll,
                fg_color="#3A3A42",
                corner_radius=14,
                border_width=1,
                border_color=ACCENT,
                width=w,
                height=h,
            )
            label = ctk.CTkLabel(
                ghost,
                text=row.item.title,
                font=(FONT_FAMILY, 13, "bold"),
                text_color=TEXT_PRIMARY,
                anchor="w",
            )
            label.pack(fill="both", padx=10, pady=8)
            ghost.place(x=x, y=y)
            self._drag_ghost = ghost

        if not self._dragging_id or not self._drag_ghost:
            return

        # move ghost with cursor
        base_y = self.scroll.winfo_rooty()
        new_y = event.y_root - base_y - self._drag_offset_y
        self._drag_ghost.place_configure(y=new_y)

    def _drag_handle_release(self, event) -> None:
        # if no drag in progress, just reset and exit (it's a click)
        if not self._dragging_id:
            self._drag_start_y = None
            self._drag_start_row = None
            return

        # determine new index from cursor position
        rows = self._all_rows()
        if rows:
            y = event.y_root
            new_index = len(rows) - 1
            for idx, child in enumerate(rows):
                cy = child.winfo_rooty()
                ch = child.winfo_height() or 1
                midpoint = cy + ch / 2
                if y < midpoint:
                    new_index = idx
                    break

            if self._drag_last_index is not None and new_index != self._drag_last_index:
                self.manager.reorder(self._dragging_id, new_index)
                self._refresh()

        if self._drag_ghost is not None:
            self._drag_ghost.destroy()
            self._drag_ghost = None

        self._dragging_id = None
        self._drag_last_index = None
        self._drag_start_y = None
        self._drag_start_row = None

    # shortcuts -----------------------------------------------------------
    def _fill_current_time(self, event=None) -> None:
        now = datetime.now()
        self.due_entry.delete(0, "end")
        self.due_entry.insert(0, now.strftime("%H:%M"))
        self.due_entry.focus()

    # reminders -----------------------------------------------------------
    def _schedule_reminders(self) -> None:
        self.after(60_000, self._check_due)

    def _check_due(self) -> None:
        now = datetime.now()
        changed = False

        for item in self.manager.items:
            if item.completed or item.notified or not item.due_datetime:
                continue
            if now >= item.due_datetime:
                messagebox.showinfo("Todo due", f'"{item.title}" is due now.')
                item.notified = True
                changed = True

        if changed:
            self.manager._save()
            self._refresh()

        self._schedule_reminders()

