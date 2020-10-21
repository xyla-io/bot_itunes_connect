import os

from pathlib import Path
from raspador import Raspador, ScriptManeuver
from typing import Dict
from .itunes_connect_pilot import iTunesConnectPilot

class iTunesConnectBot(Raspador):
  def scrape(self):
    maneuver = ScriptManeuver(script_path=str(Path(__file__).parent / 'itunes_connect_maneuver.py'))
    pilot = iTunesConnectPilot(config=self.configuration, browser=self.browser, user=self.user)
    self.fly(pilot=pilot, maneuver=maneuver)

    super().scrape()