"""Reader methods for mzIdentML, tsv as generated by MSGF+"""

import itertools

from . import basereader
from . import ml

P_SVM = ('percolator:score', 'percolator svm-score')
P_PSMP = ('percolator:psm_p_value', 'PSM p-value')
P_PSMQ = ('percolator:psm_q_value', 'PSM q-value')
P_PSMPEP = ('percolator:psm_psep', 'PSM-PEP')
P_PEPTIDEQ = ('percolator:peptide_q_value', 'peptide q-value')
P_PEPTIDEPEP = ('percolator:peptide_pep', 'peptide PEP')

PERCO_ORDER = [P_SVM, P_PSMP, P_PSMQ, P_PSMPEP, P_PEPTIDEQ, P_PEPTIDEPEP]
PERCO_HEADER = [x[1] for x in PERCO_ORDER]
PERCO_HEADERMAP = {x[0]: x[1] for x in PERCO_ORDER}

def get_mzid_namespace(mzidfile):
    return basereader.get_namespace_from_top(mzidfile, None)


def mzid_spec_result_generator(mzidfile, namespace):
    return basereader.generate_tags_multiple_files(
        [mzidfile],
        'SpectrumIdentificationResult',
        ['cvList',
         'AnalysisSoftwareList',
         'SequenceCollection',
         'AnalysisProtocolCollection',
         'AnalysisCollection',
         ],
        namespace)


def mzid_specdata_generator(mzidfile, namespace):
    return basereader.generate_tags_multiple_files(
        [mzidfile],
        'SpectraData',
        ['cvList',
         'AnalysisSoftwareList',
         'SequenceCollection',
         'AnalysisProtocolCollection',
         'AnalysisCollection',
         'AnalysisData',
         ],
        namespace)


def get_mzid_specfile_ids(mzidfn, namespace):
    """Returns mzid spectra data filenames and their IDs used in the
    mzIdentML file as a dict. Keys == IDs, values == fns"""
    sid_fn = {}
    for specdata in mzid_specdata_generator(mzidfn, namespace):
        sid_fn[specdata.attrib['id']] = specdata.attrib['name']
    return sid_fn


def get_specresult_scan_nr(result):
    """Returns scan nr of an mzIdentML PSM as a str. The PSM is given
    as a SpectrumIdentificationResult element."""
    return ml.get_scan_nr(result, 'spectrumID')


def get_specresult_mzml_id(specresult):
    return specresult.attrib['spectraData_ref']


def get_specidentitem_percolator_data(item, namespace):
    """Loop through SpecIdentificationItem children. Find
    percolator data by matching to a dict lookup. Return a
    dict containing percolator data"""
    xmlns = '{%s}' % namespace['xmlns']
    percomap = {'{0}userParam'.format(xmlns): PERCO_HEADERMAP, }
    percodata = {}
    for child in item:
        try:
            percoscore = percomap[child.tag][child.attrib['name']]
        except KeyError:
            continue
        else:
            percodata[percoscore] = child.attrib['value']
    outkeys = [y for x in list(percomap.values()) for y in list(x.values())]
    for key in outkeys:
        try:
            percodata[key]
        except KeyError:
            percodata[key] = 'NA'
    return percodata


def generate_tsv_lines_multifile(fns, header):
    return itertools.chain.from_iterable([generate_tsv_psms(fn, header)
                                          for fn in fns])


def generate_tsv_psms(fn, header):
    """Returns dicts with header-keys and psm statistic values"""
    with open(fn) as fp:
        next(fp) # skip header
        for line in fp:
            yield {x: y for (x,y) in zip(header, line.strip().split('\t'))}
