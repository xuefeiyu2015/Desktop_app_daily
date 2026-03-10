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
        for obj in raw:
            try:
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
        item = TodoItem(
            id=str(uuid.uuid4()),
            title=title,
            completed=False,
            due_iso=due.isoformat(timespec="minutes") if due else None,
            notified=False,
            created_iso=now.isoformat(timespec="seconds"),
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

    # queries -------------------------------------------------------------
    def get(self, item_id: str) -> Optional[TodoItem]:
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def sorted_items(self) -> List[TodoItem]:
        def key(i: TodoItem):
            done = 1 if i.completed else 0
            return (done, i.due_datetime or datetime.max, i.created_at)

        return sorted(self.items, key=key)

