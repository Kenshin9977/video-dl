import PySimpleGUI as Sg
from lang import GuiField, get_text


def create_progress_bar(action: str, update: bool) -> Sg.Window:
    """
    Create a progress bar.

    Args:
        action (str): Action string displayed on the progress bar
        update (bool): Whether the window is created to track an update or not

    Returns:
        Sg.Window: The GUI object used for the progress bar
    """
    Sg.theme("DarkGrey13")
    layout = [
        [Sg.Text(action)],
        [Sg.ProgressBar(100, orientation="h", size=(20, 20), key="-PROG-")],
        [Sg.Text(get_text(GuiField.ff_starting), key="PROGINFOS1")],
        [Sg.Text("", key="PROGINFOS2")],
        [Sg.Cancel(button_text=get_text(GuiField.cancel_button))],
    ]
    return Sg.Window(
        action,
        layout,
        no_titlebar=not update,
        grab_anywhere=not update,
        modal=not update,
    )
