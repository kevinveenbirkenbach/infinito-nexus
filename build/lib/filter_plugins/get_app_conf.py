import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from module_utils.config_utils import get_app_conf, AppConfigKeyError,ConfigEntryNotSetError

class FilterModule(object):
    ''' Infinito.Nexus application config extraction filters '''
    def filters(self):
        return {
            'get_app_conf': get_app_conf,
        }
