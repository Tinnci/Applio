import sys
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow  # Assuming main_window.py is in the same directory

def main():
    """Main function to initialize and run the PyQt6 application."""
    app = QApplication(sys.argv)
    
    # TODO: Add internationalization setup if needed
    
    main_window = MainWindow()
    main_window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
