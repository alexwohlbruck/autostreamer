import sys
import os
import yaml
import time
import json
from datetime import datetime, timedelta
from dateutil.parser import parse
from apscheduler.schedulers.background import BackgroundScheduler
import pyautogui as ui
import win32gui
from PyQt5 import QtWidgets, QtCore, uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from apiclient import discovery
from apiclient.discovery import build
from dotenv import load_dotenv

CALENDAR_ID = 'mao8fkb7tiinqorlbm6s17fq6s@group.calendar.google.com'
ui.PAUSE = .1 # Auto GUI pause between actions

load_dotenv()

dev_Key = os.getenv('GOOGLE_API_KEY')
calendar = build('calendar', 'v3', developerKey=dev_Key)

sched = BackgroundScheduler()
sched.start()

Ui_MainWindow, QtBaseClass = uic.loadUiType('mainwindow.ui')

class EventModel(QtCore.QAbstractListModel):
    def __init__(self, *args, events=None, **kwargs):
        super(EventModel, self).__init__(*args, **kwargs)
        self.events = events or []
        
    def data(self, index, role):
        if role == Qt.DisplayRole:
            event = self.events[index.row()]
            return event.get('summary') + '  -  ' + event.get('start').get('dateTime')

    def rowCount(self, index):
        return len(self.events)

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)

        self.setupUi(self)
        self.model = EventModel()
        self.scheduler = EventScheduler(self.model)
        self.loadEvents()
        self.eventView.setModel(self.model)
        self.saveButton.pressed.connect(self.save)

    def add(self):
        """
        Add an item to our event list, getting the text from the QLineEdit .calendarIdEdit
        and then clearing it.
        """
        text = self.calendarIdEdit.text()
        if text: # Don't add empty strings.
            # Access the list via the model.
            self.model.events.append((False, text))
            # Trigger refresh.        
            self.model.layoutChanged.emit()
            # Empty the input
            self.calendarIdEdit.setText("")
            self.save()
    
    def loadEvents(self):
        self.scheduler.get_events()

    def save(self):
        self.loadEvents()

class EventScheduler():

    def __init__(self, event_model):
        self.ui_controller = UIController()
        self.event_model = event_model
        self.jobs = {
            #'eventID + timestamp': Job
        }

    def get_events(self):
        now = datetime.utcnow().isoformat() + 'Z'
        eventsResult = calendar.events().list(calendarId=CALENDAR_ID, timeMin=now, maxResults=50, singleEvents=True, orderBy='startTime').execute()
        events = eventsResult.get('items', [])
        
        self.schedule_diff_events(events)
        self.event_model.events = events
        self.event_model.layoutChanged.emit()
        
        return events

    def schedule_diff_events(self, events):

        # If an event has been modified, then remove the job
        for key in list(self.jobs):
            if not any((event.get('id') + event.get('start').get('dateTime', event.get('start').get('date'))) == key for event in events):
                self.jobs.get(key).remove()
                del self.jobs[key]

        # Check for new events in incoming data
        for event in events:
            eid = event.get('id')

            if eid not in self.jobs:
                # New event, create job
                start = event.get('start').get('dateTime', event.get('start').get('date'))
                start_datetime = parse(start)#.replace(tzinfo=None)

                eid = event.get('id')
                description = yaml.safe_load(event.get('description'))
                url = description.get('url')

                job = sched.add_job(self.ui_controller.open_url, 'date', run_date=start_datetime, args=[url])
                self.jobs[eid + event.get('start').get('dateTime', event.get('start').get('date'))] = job

class UIController():
        
    def focus_browser(self):
        if not self.search_chrome_window():
            self.open_chrome()
        time.sleep(.1)

    def windowEnumerationHandler(self, hwnd, top_windows):
        top_windows.append((hwnd, win32gui.GetWindowText(hwnd)))

    def search_chrome_window(self):
        found_window = False
        top_windows = []
        win32gui.EnumWindows(self.windowEnumerationHandler, top_windows)
        
        for i in top_windows:
            if "chrome" in i[1].lower():
                found_window = True
                win32gui.ShowWindow(i[0],5)
                win32gui.SetForegroundWindow(i[0])
                break

        return found_window

    def open_chrome(self):
        ui.press('win')
        ui.typewrite('chrome')
        ui.press('enter')
        time.sleep(1 + 5 * ui.PAUSE)

    def navigate(self, url):
        ui.press('esc')
        time.sleep(3)
        ui.hotkey('ctrl', 'l')
        ui.typewrite(url)
        ui.press('enter')
        time.sleep(5 + 5 * ui.PAUSE)

    def open_url(self, url):
        self.focus_browser()
        self.navigate(url)
        ui.press('f')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())