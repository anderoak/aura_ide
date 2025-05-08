import sys
from PySide6.QtWidgets import QApplication
from aura_ide.ui.main_window import MainWindow # Importa nossa classe MainWindow

def run_app():
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    run_app()