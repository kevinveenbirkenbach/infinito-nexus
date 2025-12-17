from ansible.plugins.lookup import LookupBase
from colorscheme_generator import generate_full_palette

class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        base_color = terms[0]
        count = kwargs.get('count')
        shades = kwargs.get('shades')
        invert_lightness = kwargs.get('invert_lightness', False)
        return [generate_full_palette(base_color, count=count, shades=shades, invert_lightness=invert_lightness)]
