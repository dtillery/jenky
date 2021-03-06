from jenky.menus.initial import InitialMenu
from jenky.menus.settings import SettingsMenu, UsernameMenu, APIKeyMenu, HostnameMenu
from jenky.menus.jobs import JobsMenu

settings_menus = (UsernameMenu, APIKeyMenu, HostnameMenu, SettingsMenu)
available_menus = (InitialMenu, JobsMenu)