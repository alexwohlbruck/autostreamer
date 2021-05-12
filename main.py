import sys
import os
from apscheduler.jobstores.base import JobLookupError
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
from PyQt5.QtWidgets import QApplication, QMessageBox
from apiclient import discovery
from apiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

import faulthandler
# necessary to disable first or else new threads may not be handled.
faulthandler.disable()
faulthandler.enable(all_threads=True)

load_dotenv()

dev_Key = os.getenv('GOOGLE_API_KEY')
calendar = build('calendar', 'v3', developerKey=dev_Key)

sched = BackgroundScheduler()
sched.start()

Ui_MainWindow, QtBaseClass = uic.loadUiType('mainwindow.ui')

def load_config():
    config_filename = 'config.yaml'
    empty_config = {
        'calendar_id': '',
        'pause_time': 0.5
    }
    try:
        with open(config_filename, 'r') as stream:
            try:
                config = yaml.safe_load(stream)
                print(config)
                return config if config else empty_config
            except yaml.YAMLError as exc:
                print(exc)
    except FileNotFoundError as error:
        open(config_filename, 'w')
        return empty_config

def find(lst, key, value):
    for i, dic in enumerate(lst):
        if dic[key] in value:
            return i
    return -1

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

        self.ui_controller = UIController()
        self.jobs = {
            #'eventID + timestamp': Job
        }

        self.config = load_config()

        self.calendarIdEdit.setText(self.config.get('calendar_id'))
        self.pauseTimeEdit.setText(str(self.config.get('pause_time')))
        self.get_events(self.config)

        self.eventView.setModel(self.model)
        self.saveButton.pressed.connect(self.save)
        
        # Refresh data every 5 minutes
        sched.add_job(self.get_events, 'interval', seconds=5, args=[self.config])



    def show_error(self, title, message):
        QMessageBox.warning(self, title, message)

    def save(self):
        calendar_id = self.calendarIdEdit.text()
        pause_time = self.pauseTimeEdit.text()

        try:
            f_pause_time = float(pause_time)

            config = {
                'calendar_id': calendar_id,
                'pause_time': f_pause_time
            }

            with open('config.yaml', 'w') as file:
                yaml.dump(config, file, default_flow_style=False)

            self.get_events(config)
            
        except ValueError:
            self.show_error('Value error', 'Enter a number in seconds for time between actions (ex. 0.5)')


    def get_events(self, config):

        ui.PAUSE = config.get('pause_time') # Auto GUI pause between actions

        now = datetime.utcnow().isoformat() + 'Z'

        try:
            eventsResult = calendar.events().list(calendarId=config.get('calendar_id'), timeMin=now, maxResults=50, singleEvents=True, orderBy='startTime').execute()
            events = eventsResult.get('items', [])
            
            self.diff_events(events)

            return events

        except:
            return []


    def get_event_key(self, event):
        return event.get('id') + event.get('start').get('dateTime', event.get('start').get('date'))

    def diff_events(self, events):

        # If an event has been modified, then remove the event
        for key in list(self.jobs):
            if not any(self.get_event_key(event) == key for event in events):
                try:
                    self.jobs.get(key).remove()
                    del self.model.events[find(self.model.events, 'id', key)]
                    del self.jobs[key]

                    print('Job removed')
                except JobLookupError as error:
                    print("Couldn't remove job")

        # Check for new events in incoming data
        for event in events:
            key = self.get_event_key(event)

            if key not in self.jobs.keys():
                # New event, create job
                start = event.get('start').get('dateTime', event.get('start').get('date'))
                start_datetime = parse(start)#.replace(tzinfo=None)

                description = yaml.safe_load(event.get('description'))
                url = description.get('url')

                job = sched.add_job(self.ui_controller.open_url, 'date', run_date=start_datetime, args=[url])
                
                self.model.events.append(event)
                self.jobs[self.get_event_key(event)] = job

                print('Job added', len(self.jobs))
        
        self.model.layoutChanged.emit()

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