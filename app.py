# app.py
# Entry point of the Ubuntu Cleanup Manager application.

import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    """
    Create the Qt application, open the main window,
    and start the event loop.
    """
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()