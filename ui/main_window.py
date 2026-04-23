# ui/main_window.py
# Main user interface for the Ubuntu Cleanup Manager.
# Version 2 adds:
# - better styling
# - app icon
# - non-blocking background execution for long-running actions
# - status bar messages

import os
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QTabWidget,
    QListWidget,
    QMessageBox,
    QApplication,
    QFrame,
)

from core.system_info import (
    get_os_info,
    get_disk_usage,
    get_cache_size,
    check_repo_config,
)
from core.apt_actions import (
    run_apt_update,
    get_upgradable_packages,
    run_autoclean,
    run_clean,
    run_autoremove,
)
from ui.worker import ActionWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Ubuntu Cleanup Manager")
        self.resize(980, 700)

        # Load app icon if present
        icon_path = os.path.join(os.getcwd(), "assets", "icon.svg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Worker reference used while an action is running
        self.active_worker = None
        self.worker_success_handler = None

        # Create logs directory if it does not exist
        self.log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, "app.log")

        # Main central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # App title
        self.title_label = QLabel("Ubuntu Package Cleanup and Update Manager")
        self.title_label.setObjectName("TitleLabel")

        self.subtitle_label = QLabel("Version 2 - Styled UI, launcher-ready, threaded actions")
        self.subtitle_label.setObjectName("SubtitleLabel")

        main_layout.addWidget(self.title_label)
        main_layout.addWidget(self.subtitle_label)

        # Optional banner for legacy Ubuntu versions
        self.banner_label = QLabel("")
        self.banner_label.setObjectName("BannerLabel")
        self.banner_label.hide()
        main_layout.addWidget(self.banner_label)

        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.home_tab = QWidget()
        self.updates_tab = QWidget()
        self.cleanup_tab = QWidget()
        self.logs_tab = QWidget()

        self.tabs.addTab(self.home_tab, "Home")
        self.tabs.addTab(self.updates_tab, "Updates")
        self.tabs.addTab(self.cleanup_tab, "Cleanup")
        self.tabs.addTab(self.logs_tab, "Logs")

        self.setup_home_tab()
        self.setup_updates_tab()
        self.setup_cleanup_tab()
        self.setup_logs_tab()

        self.apply_styles()

        # Status bar
        self.statusBar().showMessage("Ready")

        # Load initial data
        self.refresh_home_data(load_upgrade_count=True)

    def apply_styles(self):
        """
        Apply application-wide styling.
        """
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f7fb;
                color: #1f2937;
                font-size: 13px;
            }

            QLabel#TitleLabel {
                font-size: 24px;
                font-weight: 700;
                color: #0f172a;
                margin-bottom: 2px;
            }

            QLabel#SubtitleLabel {
                color: #64748b;
                margin-bottom: 10px;
            }

            QLabel#BannerLabel {
                background: #fff7ed;
                color: #9a3412;
                border: 1px solid #fdba74;
                border-radius: 8px;
                padding: 10px;
                font-weight: 600;
                margin-bottom: 6px;
            }

            QTabWidget::pane {
                border: 1px solid #dbe2ea;
                background: white;
                border-radius: 10px;
                top: -1px;
            }

            QTabBar::tab {
                background: #e2e8f0;
                color: #0f172a;
                padding: 10px 16px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }

            QTabBar::tab:selected {
                background: white;
                font-weight: 600;
            }

            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 14px;
                min-height: 18px;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: #1d4ed8;
            }

            QPushButton:disabled {
                background-color: #94a3b8;
                color: #e2e8f0;
            }

            QListWidget, QTextEdit {
                background: #ffffff;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 6px;
            }

            QStatusBar {
                background: #ffffff;
                border-top: 1px solid #e5e7eb;
            }
        """)

    def make_card_label(self, initial_text):
        """
        Create a metric-style label used on the Home tab.
        """
        label = QLabel(initial_text)
        label.setWordWrap(True)
        label.setStyleSheet("""
            QLabel {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                padding: 14px;
                font-size: 13px;
            }
        """)
        return label

    def setup_home_tab(self):
        """
        Build the Home tab.
        """
        layout = QVBoxLayout()
        self.home_tab.setLayout(layout)

        self.os_label = self.make_card_label("OS: Loading...")
        self.disk_label = self.make_card_label("Disk: Loading...")
        self.cache_label = self.make_card_label("APT Cache: Loading...")
        self.repo_label = self.make_card_label("Repo Status: Loading...")
        self.updates_count_label = self.make_card_label("Upgradable Packages: Loading...")

        layout.addWidget(self.os_label)
        layout.addWidget(self.disk_label)
        layout.addWidget(self.cache_label)
        layout.addWidget(self.repo_label)
        layout.addWidget(self.updates_count_label)

        refresh_button = QPushButton("Refresh Home Data")
        refresh_button.clicked.connect(lambda: self.refresh_home_data(load_upgrade_count=True))
        layout.addWidget(refresh_button)

        layout.addStretch()

    def setup_updates_tab(self):
        """
        Build the Updates tab.
        """
        layout = QVBoxLayout()
        self.updates_tab.setLayout(layout)

        description = QLabel(
            "Use this tab to refresh package metadata and inspect upgradeable packages."
        )
        description.setStyleSheet("color: #475569; margin-bottom: 6px;")
        layout.addWidget(description)

        button_row = QHBoxLayout()

        self.update_button = QPushButton("Run apt update")
        self.update_button.clicked.connect(self.handle_apt_update)

        self.show_updates_button = QPushButton("Show Upgradable Packages")
        self.show_updates_button.clicked.connect(self.handle_show_upgradable)

        button_row.addWidget(self.update_button)
        button_row.addWidget(self.show_updates_button)
        button_row.addStretch()

        layout.addLayout(button_row)

        self.update_status_label = QLabel("Update status: Not run yet")
        self.update_status_label.setStyleSheet("""
            QLabel {
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 8px;
                padding: 10px;
                color: #1d4ed8;
                font-weight: 600;
            }
        """)
        layout.addWidget(self.update_status_label)

        self.upgradable_list = QListWidget()
        layout.addWidget(self.upgradable_list)

    def setup_cleanup_tab(self):
        """
        Build the Cleanup tab.
        """
        layout = QVBoxLayout()
        self.cleanup_tab.setLayout(layout)

        top_box = QFrame()
        top_box.setStyleSheet("""
            QFrame {
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                padding: 8px;
            }
        """)

        top_box_layout = QVBoxLayout()
        top_box.setLayout(top_box_layout)

        info_label = QLabel(
            "Cleanup actions:\n"
            "- Autoclean: removes obsolete package files only\n"
            "- Clean: removes all downloaded package files\n"
            "- Autoremove: removes unused dependencies"
        )
        info_label.setWordWrap(True)
        top_box_layout.addWidget(info_label)

        layout.addWidget(top_box)

        self.autoclean_button = QPushButton("Run apt autoclean")
        self.autoclean_button.clicked.connect(self.handle_autoclean)

        self.clean_button = QPushButton("Run apt clean")
        self.clean_button.clicked.connect(self.handle_clean)

        self.autoremove_button = QPushButton("Run apt autoremove")
        self.autoremove_button.clicked.connect(self.handle_autoremove)

        layout.addWidget(self.autoclean_button)
        layout.addWidget(self.clean_button)
        layout.addWidget(self.autoremove_button)
        layout.addStretch()

    def setup_logs_tab(self):
        """
        Build the Logs tab.
        """
        layout = QVBoxLayout()
        self.logs_tab.setLayout(layout)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        clear_button = QPushButton("Clear Log View")
        clear_button.clicked.connect(self.log_output.clear)

        layout.addWidget(self.log_output)
        layout.addWidget(clear_button)

    def write_log(self, text):
        """
        Write a log entry both on the screen and to logs/app.log.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {text}"

        self.log_output.append(entry)

        with open(self.log_file, "a", encoding="utf-8") as file:
            file.write(entry + "\n")

    def set_busy(self, busy):
        """
        Disable action buttons while a background task is running.
        """
        buttons = [
            self.update_button,
            self.show_updates_button,
            self.autoclean_button,
            self.clean_button,
            self.autoremove_button,
        ]

        for button in buttons:
            button.setEnabled(not busy)

        if busy:
            QApplication.setOverrideCursor(Qt.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()

        QApplication.processEvents()

    def refresh_home_data(self, load_upgrade_count=False):
        """
        Refresh system information shown in the Home tab.

        Args:
            load_upgrade_count (bool):
                If True, also load upgradeable package count.
                This may take a little longer.
        """
        os_info = get_os_info()
        disk_usage = get_disk_usage()
        cache_size = get_cache_size()
        repo_status = check_repo_config()

        self.os_label.setText(
            f"<b>OS</b><br>{os_info['pretty_name']}<br>"
            f"Version: {os_info['version']} | Codename: {os_info['codename']}"
        )

        self.disk_label.setText(
            f"<b>Disk Usage</b><br>Used {disk_usage['used']} / Total {disk_usage['total']}<br>"
            f"Free space: {disk_usage['free']}"
        )

        self.cache_label.setText(f"<b>APT Cache</b><br>Current size: {cache_size}")

        if repo_status["ok"]:
            self.repo_label.setText(f"<b>Repository Status</b><br>OK - {repo_status['message']}")
        else:
            self.repo_label.setText(f"<b>Repository Status</b><br>Warning - {repo_status['message']}")

        # Show a banner for Ubuntu 19.04 / Disco if detected
        if os_info["version"] == "19.04" or os_info["codename"].lower() == "disco":
            self.banner_label.setText(
                "Legacy Ubuntu 19.04 system detected. Repository availability may depend on archived sources."
            )
            self.banner_label.show()
        else:
            self.banner_label.hide()

        if load_upgrade_count:
            upgrades = get_upgradable_packages()
            if upgrades["success"]:
                self.updates_count_label.setText(
                    f"<b>Upgradable Packages</b><br>{upgrades['count']} package(s) currently upgradeable"
                )
            else:
                self.updates_count_label.setText(
                    "<b>Upgradable Packages</b><br>Unable to detect current count"
                )

    def confirm_action(self, title, message):
        """
        Show a confirmation message before running cleanup actions.
        """
        reply = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        return reply == QMessageBox.Yes

    def start_worker(self, action_name, action_function, success_handler=None):
        """
        Start a background worker for a backend action.
        """
        if self.active_worker is not None:
            QMessageBox.information(self, "Busy", "Another action is already running.")
            return

        self.worker_success_handler = success_handler
        self.active_worker = ActionWorker(action_name, action_function, self)

        self.active_worker.result_ready.connect(self.on_worker_result)
        self.active_worker.error_occurred.connect(self.on_worker_error)
        self.active_worker.task_finished.connect(self.on_worker_finished)

        self.set_busy(True)
        self.statusBar().showMessage(f"{action_name} running...")
        self.write_log(f"{action_name} started")

        self.active_worker.start()

    def on_worker_result(self, action_name, result):
        """
        Handle normal worker result.
        """
        if isinstance(result, dict):
            self.write_log(f"{action_name} | Command: {result.get('command', 'N/A')}")
            self.write_log(f"{action_name} | Exit code: {result.get('exit_code', 'N/A')}")

            if result.get("stdout"):
                self.write_log(f"{action_name} | STDOUT:\n{result['stdout']}")

            if result.get("stderr"):
                self.write_log(f"{action_name} | STDERR:\n{result['stderr']}")

        if self.worker_success_handler is not None:
            self.worker_success_handler(result)

    def on_worker_error(self, action_name, error_message):
        """
        Handle worker crash.
        """
        self.write_log(f"{action_name} | Worker error: {error_message}")
        QMessageBox.warning(self, "Worker Error", f"{action_name} failed unexpectedly.\n\n{error_message}")

    def on_worker_finished(self):
        """
        Cleanup after a worker completes.
        """
        self.set_busy(False)
        self.statusBar().showMessage("Ready")

        self.active_worker = None
        self.worker_success_handler = None

    def handle_apt_update(self):
        """
        Handle the 'apt update' button click using a background worker.
        """
        self.start_worker("APT Update", run_apt_update, self.after_apt_update)

    def after_apt_update(self, result):
        """
        Update UI after apt update completes.
        """
        if result["success"]:
            self.update_status_label.setText("Update status: Success")
            self.update_status_label.setStyleSheet("""
                QLabel {
                    background: #ecfdf5;
                    border: 1px solid #86efac;
                    border-radius: 8px;
                    padding: 10px;
                    color: #15803d;
                    font-weight: 600;
                }
            """)
            QMessageBox.information(self, "Success", "APT Update completed successfully.")
        else:
            self.update_status_label.setText("Update status: Failed")
            self.update_status_label.setStyleSheet("""
                QLabel {
                    background: #fef2f2;
                    border: 1px solid #fca5a5;
                    border-radius: 8px;
                    padding: 10px;
                    color: #b91c1c;
                    font-weight: 600;
                }
            """)
            QMessageBox.warning(self, "Error", f"APT Update failed.\n\n{result['stderr']}")

        self.refresh_home_data(load_upgrade_count=True)

    def handle_show_upgradable(self):
        """
        Load the list of upgradable packages using a background worker.
        """
        self.start_worker("Load Upgradable Packages", get_upgradable_packages, self.after_show_upgradable)

    def after_show_upgradable(self, result):
        """
        Update UI after package list loads.
        """
        self.upgradable_list.clear()

        if result["success"]:
            if result["count"] == 0:
                self.upgradable_list.addItem("No upgradeable packages found.")
            else:
                for package in result["packages"]:
                    self.upgradable_list.addItem(package)

            self.updates_count_label.setText(
                f"<b>Upgradable Packages</b><br>{result['count']} package(s) currently upgradeable"
            )
            self.write_log(f"Loaded {result['count']} upgradable package(s).")
        else:
            self.write_log(f"Failed to load upgradeable packages: {result['stderr']}")
            QMessageBox.warning(self, "Error", "Could not load upgradeable packages.")

        self.refresh_home_data(load_upgrade_count=False)

    def handle_autoclean(self):
        """
        Handle 'apt autoclean'.
        """
        confirmed = self.confirm_action(
            "Confirm Autoclean",
            "Run apt autoclean?\n\nThis removes obsolete package files from the cache."
        )
        if confirmed:
            self.start_worker("APT Autoclean", run_autoclean, self.after_cleanup_action)

    def handle_clean(self):
        """
        Handle 'apt clean'.
        """
        confirmed = self.confirm_action(
            "Confirm Clean",
            "Run apt clean?\n\nThis removes all downloaded package files from the cache."
        )
        if confirmed:
            self.start_worker("APT Clean", run_clean, self.after_cleanup_action)

    def handle_autoremove(self):
        """
        Handle 'apt autoremove'.
        """
        confirmed = self.confirm_action(
            "Confirm Autoremove",
            "Run apt autoremove?\n\nThis removes unused packages and dependencies."
        )
        if confirmed:
            self.start_worker("APT Autoremove", run_autoremove, self.after_cleanup_action)

    def after_cleanup_action(self, result):
        """
        Shared UI update after cleanup commands finish.
        """
        if result["success"]:
            QMessageBox.information(self, "Success", "Cleanup action completed successfully.")
        else:
            QMessageBox.warning(self, "Error", f"Cleanup action failed.\n\n{result['stderr']}")

        self.refresh_home_data(load_upgrade_count=False)