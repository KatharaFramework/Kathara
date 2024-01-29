from typing import Optional, Dict

from rich.progress import Progress, TextColumn, BarColumn, TaskID, TaskProgressColumn, TimeRemainingColumn, \
    SpinnerColumn


class HandleDockerImagePull(object):
    """Listener for handling a Docker pull progress bar."""
    __slots__ = ['progress_bar', 'tasks']

    def __init__(self) -> None:
        self.progress_bar: Optional[Progress] = None
        self.tasks: Dict[str, TaskID] = {}

    def init(self) -> None:
        """Initialize a progress bar to track Docker image pull.

        Returns:
            None
        """
        self.progress_bar = Progress(
            TextColumn("[progress.description]{task.description}", justify='left'),
            SpinnerColumn(),
            BarColumn(bar_width=None, complete_style="default", finished_style="green"),
            TaskProgressColumn(justify='right'),
            TimeRemainingColumn(),
            expand=True,
        )

        self.progress_bar.start()

    def update(self, progress: Dict) -> None:
        """Update with a new progress coming from the Docker APIs.

        Args:
            progress (Dict): Progress coming from the pull API.

        Returns:
            None
        """
        if self.progress_bar:
            completed = False
            if progress['status'] == 'Download complete':
                description = f'[Download Complete {progress["id"]}]'
                completed = True
            elif progress['status'] == 'Downloading':
                description = f'[bold][Downloading {progress["id"]}]'
            else:
                return

            task_id = progress["id"]
            if task_id not in self.tasks.keys():
                if completed:
                    self.tasks[task_id] = self.progress_bar.add_task(description, total=100, completed=100)
                else:
                    self.tasks[task_id] = self.progress_bar.add_task(
                        description, total=progress['progressDetail']['total']
                    )
            else:
                if completed:
                    self.progress_bar.update(self.tasks[task_id], description=description, total=100, completed=100)
                else:
                    self.progress_bar.update(self.tasks[task_id], completed=progress['progressDetail']['current'])

    def finish(self) -> None:
        """Closes the Docker pull progress bar.

        Returns:
            None
        """
        if self.progress_bar:
            for task in self.tasks.values():
                self.progress_bar.stop_task(task)
            self.progress_bar.stop()

            self.tasks = {}
            self.progress_bar = None

    def unregister(self) -> None:
        """Method called when the event is unregistered

        Returns:
            None
        """
        self.finish()
