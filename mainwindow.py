import sys, os
from datetime import datetime, timedelta
from dateutil.parser import parse
from dotenv import load_dotenv

import yaml
from bs4 import BeautifulSoup

from eventmodel import EventModel
from uicontroller import UIController

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler

import pyautogui as ui
from PyQt5 import QtWidgets, QtCore, uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox

from apiclient import discovery
from apiclient.discovery import build
from googleapiclient.errors import HttpError

sched = BackgroundScheduler()
sched.start()

load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')
calendar = build('calendar', 'v3', developerKey=api_key)

def resource_path(relative_path):
	if hasattr(sys, '_MEIPASS'):
		return os.path.join(sys._MEIPASS, relative_path)
	return os.path.join(os.path.abspath('.'), relative_path)
    
def load_config():
    config_filename = resource_path('config.yaml')
    empty_config = {
        'calendar_id': '',
        'pause_time': 0.5,
        'refresh_time': 5
    }
    try:
        with open(config_filename, 'r') as stream:
            try:
                config = yaml.safe_load(stream)
                print(config)
                return config if config else empty_config
            except yaml.YAMLError as exc:
                print(exc)
    except FileNotFoundError:
        open(config_filename, 'w')
        return empty_config

def find(lst, key, value):
    for i, dic in enumerate(lst):
        if dic[key] in value:
            return i
    return -1

Ui_MainWindow, QtBaseClass = uic.loadUiType(resource_path('views/mainwindow.ui'))

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
        self.refreshTimeEdit.setText(str(self.config.get('refresh_time')))
        self.get_events(self.config)

        self.eventView.setModel(self.model)
        self.saveButton.pressed.connect(self.save)
        
        # Refresh data every 5 minutes
        self.refresh_job = None
        self.set_refresh_interval(self.config.get('refresh_time'))


    def show_error(self, title, message):
        QMessageBox.warning(self, title, message)

    def set_refresh_interval(self, minutes=5):
        if (self.refresh_job):
            self.refresh_job.remove()
        self.refresh_job = sched.add_job(self.get_events, 'interval', minutes=minutes, args=[self.config])

    def save(self):
        calendar_id = self.calendarIdEdit.text()
        pause_time = self.pauseTimeEdit.text()
        refresh_time = self.refreshTimeEdit.text()

        try:
            f_pause_time = float(pause_time)
            i_refresh_time = int(refresh_time)

            self.set_refresh_interval(i_refresh_time)

            config = {
                'calendar_id': calendar_id,
                'pause_time': f_pause_time,
                'refresh_time': i_refresh_time
            }

            with open('config.yaml', 'w') as file:
                yaml.dump(config, file, default_flow_style=False)

            self.get_events(config)
            
        except ValueError:
            self.show_error('Value error', 'Enter a number for pause time and refresh time')


    def get_events(self, config):

        print('Fetching events')

        ui.PAUSE = config.get('pause_time') # Auto GUI pause between actions

        now = datetime.utcnow().isoformat() + 'Z'

        try:
            events_result = calendar.events().list(calendarId=config.get('calendar_id'), timeMin=now, maxResults=50, singleEvents=True, orderBy='startTime').execute()
            events = events_result.get('items', [])
            
            self.diff_events(events)
            self.model.layoutChanged.emit()

            return events

        except:
            print("Couldn't fetch events. Check internet connection or calendar ID.")
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
                except JobLookupError:
                    print("Couldn't remove job")

        # Check for new events in incoming data
        for event in events:
            key = self.get_event_key(event)

            if key not in self.jobs.keys():
                # New event, create job
                start = event.get('start').get('dateTime', event.get('start').get('date'))
                start_datetime = parse(start)#.replace(tzinfo=None)

                description = yaml.safe_load(
                    BeautifulSoup(event.get('description'), features='html.parser').get_text()
                )
                url = description.get('url')

                job = sched.add_job(self.ui_controller.open_url, 'date', run_date=start_datetime, args=[url])
                
                self.model.events.append(event)
                self.jobs[self.get_event_key(event)] = job

                print('Job added', len(self.jobs))
        
        self.model.layoutChanged.emit()
