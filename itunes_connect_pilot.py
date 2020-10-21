from raspador import Pilot, UserInteractor, BrowserInteractor
from typing import Dict, List

class iTunesConnectPilot(Pilot):
  config: Dict[str, any]
  sign_in_wait = 3.0

  def __init__(self, config: Dict[str, any], user: UserInteractor, browser: BrowserInteractor):
    self.config = config
    super().__init__(user=user, browser=browser)
  
  @property
  def email(self) -> str:
    return self.config['email']

  @property
  def password(self) -> str:
    return self.config['password']
  
  @property
  def base_url(self) -> str:
    return self.config['base_url']

  @property
  def client_profile_name(self) -> str:
    return self.config['client_profile_name']

  @property
  def app_ids(self) -> List[str]:
    return self.config['app_ids']

  @property
  def urls(self) -> List[str]:
    return [f'{self.base_url}?app={app_id}' for app_id in self.app_ids]