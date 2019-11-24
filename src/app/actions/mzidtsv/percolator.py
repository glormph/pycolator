import os
from app.readers import mzidplus as readers
from app.readers import tsv as tsvreader
from app.readers import xml
from app.readers import pycolator as percoreader 
from app.dataformats import mzidtsv as psmheaders


def calculate_target_decoy_competition(percofn):
    """From a percolator XML output file, use its svm scores to calculate an FDR
    using TD-competition (not percolator's mixmax method). Output 
    can be used
    to deliver 
    """
    # TODO add option to calculate FDR or not (percolator default one)
    ns = xml.get_namespace_from_top(percofn, None)
    # First calculate PSM FDRs
    psms = {
            p.attrib['{%s}psm_id' % ns['xmlns']]: (
                float(p.find('{%s}svm_score' % ns['xmlns']).text),
                p.attrib['{%s}decoy' % ns['xmlns']] == 'true')
            for p in percoreader.generate_psms(percofn, ns)
            }
    decoys = {True: 0, False: 0}
    for psm in sorted([(pid, score, decoy) for pid, (score, decoy) in psms.items()], reverse=True, key=lambda x:x[1]):
        decoys[psm[2]] += 1
        try:
            psms[psm[0]] = {'decoy': psm[2], 'svm': psm[1], 'qval': decoys[True]/decoys[False]}  # T-TDC
        except ZeroDivisionError:
            psms[psm[0]] = {'decoy': psm[2], 'svm': psm[1], 'qval': 1}  # T-TDC
    # Then calculate peptide FDRs
    decoys = {'true': 0, 'false': 0}
    for svm, decoy, psm_ids in sorted([(float(x.find('{%s}svm_score' % ns['xmlns']).text), x.attrib['{%s}decoy' % ns['xmlns']], x.find('{%s}psm_ids' % ns['xmlns'])) for x in percoreader.generate_peptides(percofn, ns)], reverse=True, key=lambda x:x[0]):
        decoys[decoy] += 1
        for pid in psm_ids:
            try:
                psms[pid.text]['pepqval'] = decoys['true']/decoys['false']
            except ZeroDivisionError:
                psms[pid.text]['pepqval'] = 1
            except KeyError:
                # Edgecase, sometimes filtering percolator data causes this:
                # when there is a peptide with a PSM ID not in percolator PSMs 
                # set all its PSMs pep-q-values to 1
                [psms[x].update({'pepqval': 1}) for x in psm_ids if x in psms]
                break
    return psms


def add_fdr_to_mzidtsv(psms, mzid_specidr, mzns, percodata):
    """Takes PSMs from an mzIdentML and its MSGF+ TSV and a corresponding 
    percolator XML. Calculate FDR from percolator scores and adds these 
    to tsv lines. FDR calculation is done outside of percolator to avoid 
    Mix-max FDR and instead use target-decoy competition.
    """
    # mzId results and PSM lines can be zipped
    for specidr in mzid_specidr:
        for specidi in specidr.findall('{%s}SpectrumIdentificationItem' % mzns['xmlns']):
            psm = next(psms)
            # percolator psm ID is: samplename_SII_scanindex_rank_scannr_charge_rank
            scanindex, rank = specidi.attrib['id'].replace('SII_', '').split('_')
            scan = {x.split('=')[0]: x.split('=')[1] for x in specidr.attrib['spectrumID'].split(' ')}['scan']
            spfile = os.path.splitext(psm[psmheaders.HEADER_SPECFILE])[0]
            try:
                percopsm = percodata['{fn}_SII_{ix}_{rk}_{sc}_{ch}_{rk}'.format(fn=spfile, ix=scanindex, sc=scan, rk=rank, ch=psm['Charge'])]
            except KeyError:
                continue
            outpsm = {k: v for k,v in psm.items()}
            outpsm.update({
                psmheaders.HEADER_SVMSCORE: percopsm['svm'], 
                psmheaders.HEADER_PSMQ: percopsm['qval'], 
                psmheaders.HEADER_PEPTIDE_Q: percopsm['pepqval'], 
                psmheaders.HEADER_TARGETDECOY: 'decoy' if percopsm['decoy'] else 'target', 
               # 'Strip': plates[fnix], 
               # 'Fraction': fractions[fnix], 
               # 'missed_cleavage': count_missed_cleavage(outpsm['Peptide'])
                })
            yield outpsm


def get_header_with_percolator(oldheader):
    ix = oldheader.index(psmheaders.HEADER_EVALUE) + 1
    return oldheader[:ix] + psmheaders.PERCO_HEADER + oldheader[ix:]
