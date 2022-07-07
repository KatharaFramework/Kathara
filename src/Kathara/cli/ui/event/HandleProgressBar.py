from typing import Any
from typing import List

import progressbar


class HandleProgressBar(object):
    """Generic listener for handling a progress bar."""
    __slots__ = ['message', 'progress_bar']

    def __init__(self, message: str) -> None:
        self.message = message
        self.progress_bar = None

    def init(self, items: List[Any]) -> None:
        """Initialize a progress bar on the items.

        Args:
            items (List[Any]): List of items on which init the progress bar.

        Returns:
            None
        """
        self.progress_bar = progressbar.ProgressBar(
            widgets=[self.message, progressbar.Bar(), ' ', progressbar.Counter(format='%(value)d/%(max_value)d')],
            redirect_stdout=True,
            max_value=len(items)
        )

    def update(self, item: Any) -> None:
        """Update the progress bar with the item.

        Args:
            item (Any): Item that triggered the progress bar update.

        Returns:
            None
        """
        if self.progress_bar:
            self.progress_bar += 1

    def finish(self) -> None:
        """Closes a progress bar.

        Returns:
            None
        """
        if self.progress_bar:
            self.progress_bar.finish()
