import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from module_utils.entity_name_utils import get_entity_name

class FilterModule(object):
    def filters(self):
        return {
            'get_entity_name': get_entity_name,
        }
