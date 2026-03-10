"""Entry point for the Desktop To-Do Widget."""

import customtkinter as ctk

from ui.widget_ui import GlassTodoWidget


def main() -> None:
    """Start the glassmorphism todo widget."""
    ctk.set_appearance_mode("light")
    app = GlassTodoWidget()
    app.mainloop()


if __name__ == "__main__":
    main()
