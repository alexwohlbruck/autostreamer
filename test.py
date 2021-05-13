from bs4 import BeautifulSoup

print(BeautifulSoup('url: <a href="https://google.com">https://google.com</a>', features='html.parser').get_text())