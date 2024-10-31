from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMainWindow, QWidget, QLabel, QLineEdit, QPushButton, QTextEdit, QCheckBox, QVBoxLayout, QHBoxLayout, QScrollArea, QGroupBox
import main 
import sys
import time

# Define a modern stylesheet
modern_style = """
    QMainWindow {
        background-color: #2b2b2b;
        color: #ffffff;
        font-family: Arial, sans-serif;
    }
    QLineEdit, QTextEdit {
        background-color: #3b3b3b;
        color: #ffffff;
        border-radius: 8px;
        padding: 5px;
        border: 1px solid #444;
    }
    QPushButton {
        background-color: #4c8bf5;
        color: #ffffff;
        border-radius: 8px;
        padding: 8px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #3c7be0;
    }
    QGroupBox {
        border: 1px solid #4c4c4c;
        border-radius: 8px;
        margin-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top center;
        padding: 0 5px;
        background-color: #2b2b2b;
        color: #ffffff;
    }
    QLabel {
        color: #ffffff;
    }
    QScrollArea {
        background-color: #3b3b3b;
        border: none;
    }
"""

class DownloadManagerThread(QtCore.QThread):
    download_progress_signal = QtCore.pyqtSignal(str)
    log_message_signal = QtCore.pyqtSignal(str)

    def run(self):
        while True:
            try:
                download_info = main.get_current_downloads()
                self.download_progress_signal.emit("\n".join(download_info))
            except Exception as e:
                self.log_message_signal.emit(f"Error fetching downloads: {str(e)}")
            time.sleep(10)

class OutlookMessagesThread(QtCore.QThread):
    outlook_message_signal = QtCore.pyqtSignal(str)

    def run(self):
        while True:
            try:
                messages = main.get_outlook_messages()
                self.outlook_message_signal.emit("\n".join(messages))
            except Exception as e:
                self.outlook_message_signal.emit(f"Error fetching messages: {str(e)}")
            time.sleep(60)

class PhantomFetchGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PhantomFetch")
        self.setGeometry(200, 100, 1200, 800)
        self.setStyleSheet(modern_style)

        # Main layout for widgets
        main_layout = QVBoxLayout()

        # Entry Section
        self.entry_input = QLineEdit()
        self.entry_input.setPlaceholderText("Enter title to add...")
        self.add_button = QPushButton("Add Request")
        self.add_button.clicked.connect(self.add_request)
        
        entry_layout = QHBoxLayout()
        entry_layout.addWidget(self.entry_input)
        entry_layout.addWidget(self.add_button)
        main_layout.addLayout(entry_layout)

        # Edit and Delete Buttons
        self.edit_button = QPushButton("Edit Selected")
        self.delete_button = QPushButton("Delete Selected")
        self.edit_button.clicked.connect(self.edit_selected)
        self.delete_button.clicked.connect(self.delete_selected)

        edit_delete_layout = QHBoxLayout()
        edit_delete_layout.addWidget(self.edit_button)
        edit_delete_layout.addWidget(self.delete_button)
        main_layout.addLayout(edit_delete_layout)

        # Request Status Textbox
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        main_layout.addWidget(self.status_text)

        # Current Downloads Section
        self.downloads_text = QTextEdit()
        self.downloads_text.setReadOnly(True)
        downloads_group = self.create_group("Current Downloads", self.downloads_text)
        main_layout.addWidget(downloads_group)

        # Messages from Outlook Section
        self.outlook_messages_text = QTextEdit()
        self.outlook_messages_text.setReadOnly(True)
        outlook_group = self.create_group("Messages from Outlook", self.outlook_messages_text)
        main_layout.addWidget(outlook_group)

        # Queue Information Section
        self.next_item_label = QLabel("Next in Queue: None")
        main_layout.addWidget(self.create_group("Next in Queue", self.next_item_label))

        # Request Lists Section
        self.movies_checks = QVBoxLayout()
        self.tv_checks = QVBoxLayout()
        self.music_checks = QVBoxLayout()
        
        # Scroll Areas for Requests
        movies_scroll = self.create_scroll_area("Movies Requests", self.movies_checks)
        tv_scroll = self.create_scroll_area("TV Shows Requests", self.tv_checks)
        music_scroll = self.create_scroll_area("Music Requests", self.music_checks)
        
        requests_layout = QHBoxLayout()
        requests_layout.addWidget(movies_scroll)
        requests_layout.addWidget(tv_scroll)
        requests_layout.addWidget(music_scroll)
        
        main_layout.addLayout(requests_layout)
        
        # Set main layout in the widget
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Set up Threads
        self.download_manager_thread = DownloadManagerThread()
        self.download_manager_thread.download_progress_signal.connect(self.update_download_status)
        self.download_manager_thread.log_message_signal.connect(self.append_log_message)
        self.download_manager_thread.start()

        self.outlook_messages_thread = OutlookMessagesThread()
        self.outlook_messages_thread.outlook_message_signal.connect(self.update_outlook_messages)
        self.outlook_messages_thread.start()

        # Update Request Lists and Queue Info
        self.update_request_lists()
        self.update_next_in_queue()

    def create_group(self, title, widget):
        group_box = QGroupBox(title)
        layout = QVBoxLayout()
        layout.addWidget(widget)
        group_box.setLayout(layout)
        return group_box

    def create_scroll_area(self, title, layout):
        group_box = QGroupBox(title)
        group_box.setLayout(layout)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(group_box)
        return scroll_area

    def add_request(self):
        title = self.entry_input.text().strip()
        if not title:
            QtWidgets.QMessageBox.warning(self, "Input Error", "Please enter a title to add.")
            return

        result_message = main.add_request(title)
        self.status_text.append(result_message)
        self.entry_input.clear()
        self.update_request_lists()

    def edit_selected(self):
        selected_items = []
        
        # Gather selected items and determine their type
        for layout, list_path in [(self.movies_checks, main.FILMS_LIST_PATH),
                                  (self.tv_checks, main.TV_SHOWS_LIST_PATH),
                                  (self.music_checks, main.MUSIC_LIST_PATH)]:
            for i in range(layout.count()):
                checkbox = layout.itemAt(i).widget()
                if checkbox and checkbox.isChecked():
                    selected_items.append((checkbox.text(), list_path))  # Include list_path for each item

        if len(selected_items) != 1:
            QtWidgets.QMessageBox.warning(self, "Edit Error", "Please select a single item to edit.")
            return

        # Get the item title and list path
        title, list_path = selected_items[0]

        # Prompt for new title
        new_title, ok = QtWidgets.QInputDialog.getText(self, "Edit Request", f"Edit '{title}':")
        if ok and new_title.strip():
            main.edit_request(title, new_title.strip(), list_path)
            self.status_text.append(f"Edited: {title} to {new_title.strip()}")
            self.update_request_lists()

    def delete_selected(self):
        selected_items = []
        
        # Gather selected items and determine their type
        for layout, list_path in [(self.movies_checks, main.FILMS_LIST_PATH),
                                  (self.tv_checks, main.TV_SHOWS_LIST_PATH),
                                  (self.music_checks, main.MUSIC_LIST_PATH)]:
            for i in range(layout.count()):
                checkbox = layout.itemAt(i).widget()
                if checkbox and checkbox.isChecked():
                    selected_items.append((checkbox.text(), list_path))  # Include list_path for each item

        if not selected_items:
            QtWidgets.QMessageBox.warning(self, "Delete Error", "Please select one or more items to delete.")
            return

        for title, list_path in selected_items:
            main.delete_request(title, list_path)
            self.status_text.append(f"Deleted: {title}")
        
        self.update_request_lists()

    def get_selected_items(self):
        """
        Helper method to gather selected items from each request type (Movies, TV Shows, Music).
        Returns a list of tuples (title, list_path).
        """
        selected_items = []

        # Check selected items in Movies
        for i in range(self.movies_checks.count()):
            checkbox = self.movies_checks.itemAt(i).widget()
            if checkbox and checkbox.isChecked():
                selected_items.append((checkbox.text(), main.FILMS_LIST_PATH))

        # Check selected items in TV Shows
        for i in range(self.tv_checks.count()):
            checkbox = self.tv_checks.itemAt(i).widget()
            if checkbox and checkbox.isChecked():
                selected_items.append((checkbox.text(), main.TV_SHOWS_LIST_PATH))

        # Check selected items in Music
        for i in range(self.music_checks.count()):
            checkbox = self.music_checks.itemAt(i).widget()
            if checkbox and checkbox.isChecked():
                selected_items.append((checkbox.text(), main.MUSIC_LIST_PATH))

        return selected_items

    def update_request_lists(self):
        movies, tv_shows, music = main.get_request_lists()
        
        for layout in [self.movies_checks, self.tv_checks, self.music_checks]:
            while layout.count():
                widget = layout.takeAt(0).widget()
                if widget:
                    widget.deleteLater()

        self.create_checkboxes(movies, self.movies_checks)
        self.create_checkboxes(tv_shows, self.tv_checks)
        self.create_checkboxes(music, self.music_checks)

    def create_checkboxes(self, items, layout):
        for item in items:
            checkbox = QCheckBox(item)
            layout.addWidget(checkbox)

    def update_next_in_queue(self):
        try:
            movies, tv_shows, music = main.get_request_lists()
            next_item = movies[0] if movies else (tv_shows[0] if tv_shows else (music[0] if music else "None"))
            self.next_item_label.setText(f"Next in Queue: {next_item}")
        except Exception as e:
            self.next_item_label.setText(f"Error: {str(e)}")

    def update_download_status(self, download_info):
        self.downloads_text.setPlainText(f"Current Downloads:\n{download_info}")

    def update_outlook_messages(self, messages):
        self.outlook_messages_text.setPlainText(f"Messages from Outlook:\n{messages}")

    def append_log_message(self, message):
        self.status_text.append(message)

       def edit_selected(self):
        selected_items = self.get_selected_items()
        
        # Check if only one item is selected
        if len(selected_items) != 1:
            QtWidgets.QMessageBox.warning(self, "Edit Error", "Please select a single item to edit.")
            return

        # Get the selected item's title and its list path
        title, list_path = selected_items[0]

        # Prompt for the new title
        new_title, ok = QtWidgets.QInputDialog.getText(self, "Edit Request", f"Edit '{title}':")
        if ok and new_title.strip():
            # Call main.edit_request to make the change in the file
            success = main.edit_request(title, new_title.strip(), list_path)
            if success:
                self.status_text.append(f"Edited '{title}' to '{new_title.strip()}'")
            else:
                self.status_text.append(f"Failed to edit '{title}'")
            self.update_request_lists()  # Refresh list

    def delete_selected(self):
        selected_items = self.get_selected_items()

        # Check if at least one item is selected
        if not selected_items:
            QtWidgets.QMessageBox.warning(self, "Delete Error", "Please select one or more items to delete.")
            return

        # Delete each selected item
        for title, list_path in selected_items:
            success = main.delete_request(title, list_path)
            if success:
                self.status_text.append(f"Deleted '{title}'")
            else:
                self.status_text.append(f"Failed to delete '{title}'")

        self.update_request_lists()  # Refresh list


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    gui = PhantomFetchGUI()
    gui.show()
    sys.exit(app.exec_())
