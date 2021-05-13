import sys, os
import faulthandler

from mainwindow import MainWindow
from PyQt5.QtWidgets import QApplication

# necessary to disable first or else new threads may not be handled.
faulthandler.disable()
faulthandler.enable(all_threads=True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())