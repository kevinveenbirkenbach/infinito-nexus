#!/usr/bin/python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from module_utils.get_url import get_url

class FilterModule(object):
    ''' Infinito.Nexus application config extraction filters '''
    def filters(self):
        return {
            'get_url': get_url,
        }
