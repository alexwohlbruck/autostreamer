

import time
import json
import win32gui
import pyautogui as ui

class UIController():
        
    def focus_browser(self):
        if not self.search_chrome_window():
            self.open_chrome()
        time.sleep(.1)

    def window_enumeration_handler(self, hwnd, top_windows):
        top_windows.append((hwnd, win32gui.GetWindowText(hwnd)))

    def search_chrome_window(self):
        print('Searching for chrome window')

        found_window = False
        top_windows = []
        win32gui.EnumWindows(self.window_enumeration_handler, top_windows)
        
        for i in top_windows:
            if "chrome" in i[1].lower():
                try:
                    found_window = True
                    win32gui.ShowWindow(i[0],5)
                    win32gui.SetForegroundWindow(i[0])
                    break
                except:
                    print("Couldn't focus browser")
                    break;

        return found_window

    def open_chrome(self):
        print('Opening chrome')
        ui.press('win')
        ui.typewrite('chrome')
        ui.press('enter')
        time.sleep(1 + 5 * ui.PAUSE)

    def navigate(self, url):
        print('Navigating to ' + url)
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