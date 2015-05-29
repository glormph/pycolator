from app.drivers.mslookup import base
from app.readers import tsv as tsvreader 
from app.actions.mslookup import psms as lookup


class PSMLookupDriver(base.LookupDriver):
    lookuptype = 'psm'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spectracol = kwargs.get('speccol', None)

    def create_lookup(self):
        header = tsvreader.get_tsv_header(self.fn[0])
        specfncol = header[int(self.spectracol) - 1]
        lookup.create_psm_lookup(self.fn, header, self.lookup, self.unroll, specfncol)