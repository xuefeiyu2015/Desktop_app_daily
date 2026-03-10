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
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.item = item
        self.on_toggle = on_toggle
        self.on_delete = on_delete
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

    def _refresh(self) -> None:
        for w in self.scroll.winfo_children():
            w.destroy()

        for item in self.manager.sorted_items():
            row = TodoRow(
                self.scroll,
                item,
                on_toggle=self._on_toggle,
                on_delete=self._on_delete,
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

