from typing import Any, Optional
from typing import List

from rich.progress import Progress, TextColumn, BarColumn, TaskID, MofNCompleteColumn, SpinnerColumn


class HandleProgressBar(object):
    """Generic listener for handling a progress bar."""
    __slots__ = ['message', 'progress_bar', 'task']

    def __init__(self, message: str) -> None:
        self.message: str = message
        self.progress_bar: Optional[Progress] = None
        self.task: Optional[TaskID] = None

    def init(self, items: List[Any]) -> None:
        """Initialize a progress bar on the items.

        Args:
            items (List[Any]): List of items on which init the progress bar.

        Returns:
            None
        """
        self.progress_bar = Progress(
            TextColumn("[progress.description]{task.description}", justify='left'),
            SpinnerColumn(),
            BarColumn(bar_width=None, complete_style="default", finished_style="green"),
            MofNCompleteColumn(),
            expand=True,
        )

        self.progress_bar.start()

        self.task = self.progress_bar.add_task(f"[bold][{self.message}]", total=len(items))

    def update(self, item: Any) -> None:
        """Update the progress bar with the item.

        Args:
            item (Any): Item that triggered the progress bar update.

        Returns:
            None
        """
        if self.progress_bar:
            self.progress_bar.update(self.task, advance=1, update=True)

    def finish(self) -> None:
        """Closes a progress bar.

        Returns:
            None
        """
        if self.progress_bar:
            self.progress_bar.stop_task(self.task)
            self.progress_bar.stop()

            self.task = None
            self.progress_bar = None

    def unregister(self) -> None:
        """Method called when the event is unregistered

        Returns:
            None
        """
        self.finish()
