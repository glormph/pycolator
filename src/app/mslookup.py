#!/usr/bin/python3

import sys
from app.drivers.mslookup import (spectra, quant, proteinquant, pepquant, psms, seqspace)
from app.drivers import startup


def main():
    drivers = [spectra.SpectraLookupDriver(),
               psms.PSMLookupDriver(),
               quant.IsobaricQuantLookupDriver(),
               quant.PrecursorQuantLookupDriver(),
               pepquant.PeptideQuantLookupDriver(),
               proteinquant.ProteinQuantLookupDriver(),
               seqspace.SeqspaceLookupDriver(),
               seqspace.WholeProteinSeqspaceLookupDriver(),
               seqspace.DecoySeqDriver(),
               seqspace.TrypsinizeDriver(),
               ]
    startup.start_msstitch(drivers, sys.argv)
