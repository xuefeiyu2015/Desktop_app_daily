import json
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional


TODO_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "todo.json")


@dataclass
class TodoItem:
    id: str
    title: str
    completed: bool
    due_iso: Optional[str]
    notified: bool
    created_iso: str
    order: int

    @property
    def due_datetime(self) -> Optional[datetime]:
        if not self.due_iso:
            return None
        try:
            return datetime.fromisoformat(self.due_iso)
        except ValueError:
            return None

    @property
    def created_at(self) -> datetime:
        try:
            return datetime.fromisoformat(self.created_iso)
        except ValueError:
            return datetime.now()


class TodoManager:
    """Handles loading, saving, and mutating todo items."""

    def __init__(self, path: str = TODO_FILE) -> None:
        self.path = path
        self.items: List[TodoItem] = []
        self._load()

    # persistence ---------------------------------------------------------
    def _load(self) -> None:
        if not os.path.exists(self.path):
            self.items = []
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            self.items = []
            return

        self.items = []
        for idx, obj in enumerate(raw):
            try:
                order_val = obj.get("order")
                order = int(order_val) if isinstance(order_val, int) else idx
                item = TodoItem(
                    id=obj.get("id", str(uuid.uuid4())),
                    title=obj.get("title", ""),
                    completed=bool(obj.get("completed", False)),
                    due_iso=obj.get("due_iso"),
                    notified=bool(obj.get("notified", False)),
                    created_iso=obj.get(
                        "created_iso",
                        datetime.now().isoformat(timespec="seconds"),
                    ),
                    order=order,
                )
                self.items.append(item)
            except Exception:
                continue

    def _save(self) -> None:
        data = [asdict(i) for i in self.items]
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    # operations ----------------------------------------------------------
    def add(self, title: str, due: Optional[datetime]) -> TodoItem:
        now = datetime.now()
        next_order = max((i.order for i in self.items), default=-1) + 1
        item = TodoItem(
            id=str(uuid.uuid4()),
            title=title,
            completed=False,
            due_iso=due.isoformat(timespec="minutes") if due else None,
            notified=False,
            created_iso=now.isoformat(timespec="seconds"),
            order=next_order,
        )
        self.items.append(item)
        self._save()
        return item

    def delete(self, item_id: str) -> None:
        self.items = [i for i in self.items if i.id != item_id]
        self._save()

    def toggle_complete(self, item_id: str) -> None:
        for item in self.items:
            if item.id == item_id:
                item.completed = not item.completed
                break
        self._save()

    def set_title(self, item_id: str, title: str) -> None:
        for item in self.items:
            if item.id == item_id:
                item.title = title
                break
        self._save()

    def set_due(self, item_id: str, due: Optional[datetime]) -> None:
        for item in self.items:
            if item.id == item_id:
                item.due_iso = due.isoformat(timespec="minutes") if due else None
                break
        self._save()

    def reorder(self, item_id: str, new_index: int) -> None:
        """Move item with item_id to new_index in items list."""
        current_index = None
        for idx, item in enumerate(self.items):
            if item.id == item_id:
                current_index = idx
                break
        if current_index is None or new_index < 0 or new_index >= len(self.items):
            return
        if current_index == new_index:
            return

        item = self.items.pop(current_index)
        self.items.insert(new_index, item)

        # re-normalise order values
        for idx, it in enumerate(self.items):
            it.order = idx
        self._save()

    # queries -------------------------------------------------------------
    def get(self, item_id: str) -> Optional[TodoItem]:
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def sorted_items(self) -> List[TodoItem]:
        """Return items in explicit order, newest structure first."""
        return sorted(self.items, key=lambda i: i.order)

