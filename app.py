import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

if __name__ == "__main__":
    application = QApplication(sys.argv)
    window = MainWindow(); window.show()
    raise SystemExit(application.exec())
