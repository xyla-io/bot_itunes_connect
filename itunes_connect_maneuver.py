import re
import datetime
import importlib
import glob
import shutil

from itunes_connect.itunes_connect_pilot import iTunesConnectPilot
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from raspador import Maneuver, OrdnanceManeuver, NavigationManeuver, SequenceManeuver, UploadReportRaspador, ClickXPathSequenceManeuver, InteractManeuver, OrdnanceParser, XPath, RaspadorNoOrdnanceError, ClickXPathManeuver, SeekParser, SoupElementParser, FindElementManeuver, ClickSoupElementManeuver, Element, ElementManeuver, ClickElementManeuver
from typing import Generator, Optional, Dict, List
from time import sleep
from bs4 import BeautifulSoup, Tag

class SignInManeuver(Maneuver[iTunesConnectPilot]):
  def attempt(self, pilot: iTunesConnectPilot):
    iframe = pilot.browser.driver.find_elements_by_tag_name('iframe')[0]
    pilot.browser.driver.switch_to_frame(iframe)

    email_element = yield ClickElementManeuver(
      instruction='click the email filed',
      seeker=lambda p: p.soup.find('input', {'id': 'account_name_text_field'})
    )
    email_element.ordnance.send_keys(pilot.email)
    sleep(1)
    email_element.ordnance.send_keys(Keys.RETURN)
    sleep(1)

    password_element = yield ClickElementManeuver(
      instruction='click the password field',
      seeker=lambda p: p.soup.find('input', {'id': 'password_text_field'})
    )
    password_element.ordnance.send_keys(pilot.password)
    sleep(1)
    password_element.ordnance.send_keys(Keys.RETURN)
    pilot.browser.driver.switch_to.default_content()
    sleep(pilot.sign_in_wait)

class SelectClientManeuver(Maneuver[iTunesConnectPilot]):
  def attempt(self, pilot: iTunesConnectPilot):
    yield ClickElementManeuver(
      instruction='click the profile menu dropdown',
      seeker=lambda p: p.soup.find('div', {'class': 'itc-user-profile-controls-menu'})
    )
    yield ClickElementManeuver(
      instruction='select client profile',
      seeker=lambda p: p.soup.find('li', title=pilot.client_profile_name)
    )

class UncheckUniqueDevicesManeuver(Maneuver[iTunesConnectPilot]):
  def attempt(self, pilot: iTunesConnectPilot):
    impressions_before_check = int((yield ElementManeuver(
      instruction='find impressions element',
      seeker=lambda p: p.soup.find('div', {'class': 'itemtotal'})
    )).ordnance.soup_element.text.replace(',', ''))

    yield ClickElementManeuver(
      instruction='click the checkbox container',
      seeker=lambda p: p.soup.find('div', {'itc-checkbox': 'isUniqueSel'})
    )
    sleep(3)

    impressions_after_check = int((yield ElementManeuver(
      instruction='find impressions element',
      seeker=lambda p: p.soup.find('div', {'class': 'itemtotal'})
    )).ordnance.soup_element.text.replace(',', ''))

    if impressions_after_check < impressions_before_check:
      yield ClickElementManeuver(
        instruction='click the checkbox container',
        seeker=lambda p: p.soup.find('div', {'itc-checkbox': 'isUniqueSel'})
      )
      sleep(3)

class ViewByManeuver(Maneuver[iTunesConnectPilot]):
  view_by_text: str
  wait_after: int

  def __init__(self, view_by_text: str, wait_after: int):
    super().__init__()
    self.view_by_text = view_by_text
    self.wait_after = wait_after

  def attempt(self, pilot: iTunesConnectPilot):
    yield ClickElementManeuver(
      instruction='click on the view-by dropdown',
      seeker=lambda p: p.soup.find('div', {'class': 'view-by-menu'})
    )
    yield ClickElementManeuver(
      instruction='click the impressions menu item',
      seeker=lambda p: p.soup.find('div', text=self.view_by_text)
    )
    sleep(self.wait_after)

class SelectLastThirtyDaysManeuver(Maneuver[iTunesConnectPilot]):
  def attempt(self, pilot: iTunesConnectPilot):
    yield ClickElementManeuver(
      instruction='select the last 30 days',
      seeker=lambda p: p.soup.find('div', {'class': 'chartdatepicker'})
    )
    yield ClickElementManeuver(
      instruction='select the last 30 days',
      seeker=lambda p: p.soup.find('div', text='Last 30 Days')
    )

class ExportCSVManeuver(Maneuver[iTunesConnectPilot]):
  def attempt(self, pilot: iTunesConnectPilot):
    yield ClickElementManeuver(
      instruction='click the export button',
      seeker=lambda p: p.soup.find('div', {'class': 'cicon-download'})
    )

class ExportSourceTypeManeuver(Maneuver[iTunesConnectPilot]):
  filter_text: str

  def __init__(self, filter_text: Optional[str]=None):
    super().__init__()
    self.filter_text = filter_text
    
  def attempt(self, pilot: iTunesConnectPilot):
    yield ClickElementManeuver(
      instruction='click the add filter button',
      seeker=lambda p: p.soup.find('div', {'class': 'addfilter_button'})
    )

    def find_source_type_element(parser):
      icons = parser.soup.find_all('div', {'class': 'more cicon-right'})
      for sibling in [icon.find_previous_sibling() for icon in icons]:
        if sibling.text == 'Source Type':
          return sibling
      return None

    if self.filter_text:
      source_type_element = (yield ElementManeuver(
        instruction='click the add filter button',
        seeker=find_source_type_element,
      )).ordnance

      action = ActionChains(pilot.browser.driver)
      action.reset_actions()
      source_type_web_element = pilot.browser.driver.find_element_by_xpath(source_type_element.xpath)
      action.move_to_element(source_type_web_element).perform()
      sleep(1)

      popover_xpath = "div[contains(@class, 'children popover-wrap')]"
      yield ClickElementManeuver(
        instruction='click the filter taret button',
        xpath=f"//{popover_xpath}//child::div[contains(text(),'{self.filter_text}')]"
      )
      action.reset_actions()
      
    sleep(5)
    yield ExportCSVManeuver()
    yield ClickElementManeuver(
      instruction='click the close filter button',
      seeker=lambda p: p.soup.find_all('div', {'class': 'killer'})[-1],
    )

class ClickNavigationLinkItem(Maneuver[iTunesConnectPilot]):
  item_text: str
  wait_after: int

  def __init__(self, item_text: str, wait_after: int):
    super().__init__()
    self.item_text = item_text
    self.wait_after = wait_after

  def attempt(self, pilot: iTunesConnectPilot):
    yield ClickElementManeuver(
      instruction='click the metrics nav bar item',
      seeker=lambda p: p.soup.find('a', text=self.item_text)
    )
    sleep(self.wait_after)

class iTunesConnectManeuver(Maneuver[iTunesConnectPilot]):
  def attempt(self, pilot: iTunesConnectPilot):
    yield NavigationManeuver(url='https://appstoreconnect.apple.com/login')
    sleep(5)

    yield SignInManeuver()
    yield SelectClientManeuver()
    sleep(2)

    for url in pilot.urls:
      # 1. View "Metrics"
      yield NavigationManeuver(url=url)
      sleep(6)
      yield ClickNavigationLinkItem(item_text='Metrics', wait_after=5)

      # 2. View by "Impressions"
      yield ClickNavigationLinkItem(item_text='Impressions', wait_after=5)
      yield UncheckUniqueDevicesManeuver()
      yield SelectLastThirtyDaysManeuver()

      # 3. Export Impressions by Source Type
      yield ViewByManeuver('Source Type', wait_after=3)
      yield ExportCSVManeuver()

      source_filters = ['App Store Search', 'App Store Browse', 'App Referrer', 'Web Referrer', 'Unavailable']
      # 4. Export Impressions by Territory
      yield ViewByManeuver('Territory', wait_after=3)
      for filter_text in source_filters:
        yield ExportSourceTypeManeuver(filter_text=filter_text)
      
      # ------------------------------------
      # Repeat above for "Product Page Views"
      # ------------------------------------
      yield ClickNavigationLinkItem(item_text='Product Page Views', wait_after=5)
      yield ViewByManeuver('Source Type', wait_after=3)
      yield ExportCSVManeuver()
      yield ViewByManeuver('Territory', wait_after=3)
      for filter_text in source_filters:
        yield ExportSourceTypeManeuver(filter_text=filter_text)
      
      # ------------------------------------
      # 5. Repeat above for "App Units"
      # ------------------------------------
      yield ClickNavigationLinkItem(item_text='App Units', wait_after=5)
      yield ViewByManeuver('Source Type', wait_after=3)
      yield ExportCSVManeuver()
      yield ViewByManeuver('Territory', wait_after=3)
      for filter_text in source_filters:
        yield ExportSourceTypeManeuver(filter_text=filter_text)

if __name__ == '__main__':
  enqueue_maneuver(iTunesConnectManeuver())
else:
  enqueue_maneuver(ClickLeftBarMenuItem(item_text='App Units', wait_after=5))