from module_utils.config_utils import get_app_conf

class FilterModule(object):
    ''' Infinito.Nexus application config extraction filters '''
    def filters(self):
        return {
            'get_app_conf': get_app_conf,
        }
