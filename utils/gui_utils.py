import PySimpleGUI as Sg

from lang import GuiField, get_text


def create_progress_bar(action: str) -> Sg.Window:
    """
    Create a progress bar.

    Args:
        action (str): Action string displayed on the progress bar

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
        action, layout, no_titlebar=True, grab_anywhere=True, modal=True
    )
