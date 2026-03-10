# Desktop_app_daily

Simple Python desktop app for managing a daily to-do list with optional due times, first-priority markers, and macOS notifications.

## Features

- Daily task list with:
  - Title
  - Optional due time (today, HH:MM, 24-hour)
  - Priority number (1 = highest, tasks sorted by priority ascending)
  - Completion status
- Double-click or button to toggle completion.
- Buttons to add, edit, delete tasks, and toggle first priority.
- Tasks are persisted locally in `tasks.json`.
- **Task icons**: Add PNG/JPG/GIF images to the `icons/` folder; each filename (without extension) becomes a selectable icon (e.g. `work.png` → "work").
- macOS notifications when tasks reach their due time (while the app is running).

## Requirements

- Python 3.8+ on macOS
- **CustomTkinter**: `pip install customtkinter` — modern UI framework for the Linear/Apple Reminders aesthetic
- **Pillow** and **cairosvg** (for SVG and image resizing):
  ```bash
  pip install Pillow cairosvg
  ```

## Usage

1. Open a terminal and navigate to the project folder:

   ```bash
   cd /Users/xuefeiyu/Documents/XuefeiFile/WorkRelated/Program_Matlab_Local/Others/Desktop_app_daily
   ```

2. Run the app:

   ```bash
   python main.py
   ```

3. Use the **Add Task** button to create tasks:
   - Enter a task.
   - Optionally enter a due time as `HH:MM` (today, 24-hour format).
   - Set **Priority** (1 = highest, 2 = second, etc.).
   - Choose an **Icon** from the dropdown (options come from images in the `icons/` folder).

4. Keep the app running to receive macOS notifications when tasks become due.

