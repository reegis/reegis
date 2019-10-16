"""
This module might be removed in future versions, because it is not an
elementary part of reegis.
"""


import sys
import os
try:
    from PyQt5 import QtWidgets as Widgets
except ImportError:
    Widgets = None


FFILTER = {
    'all': 'All Files (*.*)',
    'esys': 'Result Files (*.esys)',
    'py': 'Python Files (*.py)',
    }


def select_filename(title='Select a file', work_dir=None, extension=None):
    app = Widgets.QApplication(sys.argv)

    if work_dir is None:
        work_dir = os.path.expanduser('~')

    active_filter = FFILTER.get(extension, "All Files (*.*)")

    ffilter = "All Files (*.*);;Result Files (*.esys);;Python Files (*.py);;"

    fullpath, _ = Widgets.QFileDialog.getOpenFileNames(
        None, title, work_dir, ffilter,
        active_filter,
        options=Widgets.QFileDialog.DontUseNativeDialog)
    app.quit()

    if fullpath:
        fullpath = fullpath[0]

    return fullpath


def select_dir(title='Select a file', work_dir=None):
    app = Widgets.QApplication(sys.argv)

    if work_dir is None:
        work_dir = os.path.expanduser('~')

    path = Widgets.QFileDialog.getExistingDirectory(
        None, title, work_dir,
        options=(Widgets.QFileDialog.ShowDirsOnly |
                 Widgets.QFileDialog.DontUseNativeDialog))

    app.quit()

    return path


def get_choice(items, title='Your choice', text=None):
    app = Widgets.QApplication(sys.argv)
    selection, ok_button = Widgets.QInputDialog.getItem(
        None, title, text, items, 0, False)

    if not (ok_button and selection):
        selection = None

    app.quit()
    return selection


if __name__ == "__main__":
    print(get_choice([None, 'a', 'b', 'c']))
    exit(0)
    filename = select_filename()
    if filename:
        print(filename)
