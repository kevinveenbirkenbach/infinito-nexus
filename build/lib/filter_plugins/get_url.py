#!/usr/bin/python
import sys
import os
from module_utils.get_url import get_url

class FilterModule(object):
    ''' Infinito.Nexus application config extraction filters '''
    def filters(self):
        return {
            'get_url': get_url,
        }
