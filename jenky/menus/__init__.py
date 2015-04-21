from jenky.menus.initial import InitialMenu
from jenky.menus.settings import SettingsMenu, UsernameMenu, APIKeyMenu, HostnameMenu
from jenky.menus.jobs import JobsMenu
from jenky.menus.build import InitialBuildMenu, BuildJobMenu, ParamMenu, BuildHistoryMenu

settings_menus = (UsernameMenu, APIKeyMenu, HostnameMenu, SettingsMenu)
available_menus = (InitialMenu, JobsMenu)
build_menus = (BuildHistoryMenu, ParamMenu, BuildJobMenu, InitialBuildMenu)