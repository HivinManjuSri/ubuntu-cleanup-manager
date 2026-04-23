# ui/worker.py
# Background worker thread so long-running commands do not freeze the UI.

from PyQt5.QtCore import QThread, pyqtSignal


class ActionWorker(QThread):
    """
    Runs one backend action in a separate thread.

    Signals:
        result_ready(action_name, result_object)
        error_occurred(action_name, error_message)
        task_finished()
    """
    result_ready = pyqtSignal(str, object)
    error_occurred = pyqtSignal(str, str)
    task_finished = pyqtSignal()

    def __init__(self, action_name, action_function, parent=None):
        super().__init__(parent)
        self.action_name = action_name
        self.action_function = action_function

    def run(self):
        """
        Run the function in the background thread and emit the result.
        """
        try:
            result = self.action_function()
            self.result_ready.emit(self.action_name, result)
        except Exception as error:
            self.error_occurred.emit(self.action_name, str(error))
        finally:
            self.task_finished.emit()