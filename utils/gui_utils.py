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
    progress_bar = Sg.Window(
        action,
        layout,
        no_titlebar=not update,
        grab_anywhere=not update,
        modal=not update,
        keep_on_top=True
    )
    # progress_bar.TKroot.bind('<Configure>', configure)
    # progress_bar.TKroot.bind('<FocusIn>', focus_in)
    return progress_bar


# def configure(event):
#     global user_setting
#     global x1, x2, y1, y2
#     if not user_setting:
#         return
#     x, y = win2.current_location()
#     dx, dy = x - x2, y - y2
#     x1, y1 = x1 + dx, y1 + dy
#     win1.move(x1, y1)
#     x2, y2 = x, y

# def focus_in(event):
#     global user_setting
#     win1.bring_to_front()
#     if win2:
#         user_setting = True
#         win2.bring_to_front()
#         user_setting = False
