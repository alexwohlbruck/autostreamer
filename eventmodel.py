from PyQt5 import QtCore
from PyQt5.QtCore import Qt

class EventModel(QtCore.QAbstractListModel):
    def __init__(self, *args, events=None, **kwargs):
        super(EventModel, self).__init__(*args, **kwargs)
        self.events = events or []
        
    def data(self, index, role):
        if role == Qt.DisplayRole:
            event = self.events[index.row()]
            return event.get('start').get('dateTime') + '  -  ' + event.get('summary')

    def rowCount(self, index):
        return len(self.events)