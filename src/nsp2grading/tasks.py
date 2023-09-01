import time

from textual import work
from textual.app import log

from nsp2grading.tui import Task


class DownloadTask(Task):
    run_msg = "Downloading submission..."
    success_msg = "Download successful"
    error_msg = "Download failed"

    @work(thread=True, exit_on_error=False)
    def run_task(self):
        for _ in range(3):
            log("WORK")
            time.sleep(1)


class UnpackTask(Task):
    ...


class CreateEnvTask(Task):
    ...


class OpenCodeTask(Task):
    ...
