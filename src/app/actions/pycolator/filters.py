import re
from itertools import product

from app.readers import pycolator as reader
from app.readers import fasta
from app.readers import xmlformatting as formatting


def get_either_seq(seqtype, element, ns):
    get_seq_map = {'psm': reader.get_psm_seq,
                   'pep': reader.get_peptide_seq,
                   }
    return get_seq_map[seqtype](element, ns)


def filter_peptide_length(features, elementtype, ns, minlen=0, maxlen=None):
    minlen = int(minlen)
    if maxlen is None:
        maxlen = float('inf')
    else:
        maxlen = int(maxlen)
    for feat in features:
        seq = get_either_seq(elementtype, feat, ns)
        seq = strip_modifications(seq)
        if len(seq) > minlen and len(seq) < maxlen:
            yield formatting.string_and_clear(feat, ns)
        else:
            formatting.clear_el(feat)


def strip_modifications(seq):
    return re.sub('\[UNIMOD:\d*\]', '', seq)


def filter_whole_proteins(elements, protein_fasta, lookup, seqtype, ns,
                          deamidation, minpeplen):
    whole_proteins = {prot.id: prot.seq for prot in
                      fasta.get_proteins_sequence(protein_fasta)}
    for element in elements:
        seq_matches_protein = False
        element_seqs = get_seqs_from_element(element, seqtype, ns, deamidation)
        element_prots = {protid[0]: seq for seq in element_seqs for protid in
                         lookup.get_protein_from_pep(seq[:minpeplen])}
        for prot_id, pepseq in element_prots.items():
            if pepseq in whole_proteins[prot_id]:
                seq_matches_protein = True
                break
        if seq_matches_protein:
            formatting.clear_el(element)
        else:
            yield formatting.string_and_clear(element, ns)


def filter_known_searchspace(elements, seqtype, lookup, ns, ntermwildcards,
                             deamidation):
    """Yields peptides from generator as long as their sequence is not found in
    known search space dict. Useful for excluding peptides that are found in
    e.g. ENSEMBL or similar"""
    for element in elements:
        seq_is_known = False
        for seq in get_seqs_from_element(element, seqtype, ns, deamidation):
            if lookup.check_seq_exists(seq, ntermwildcards):
                seq_is_known = True
                break
        if seq_is_known:
            formatting.clear_el(element)
        else:
            yield formatting.string_and_clear(element, ns)


def get_seqs_from_element(element, seqtype, ns, deamidation):
        seq = get_either_seq(seqtype, element, ns)
        seq = strip_modifications(seq)
        # Exchange leucines for isoleucines since MS can't differ and we
        # don't want to find 'novel' peptides which only have a difference
        # in this amino acid
        seq = seq.replace('L', 'I')
        if deamidation:
            return combination_replace(seq, 'D', 'N')
        else:
            return [seq]


def combination_replace(seq, from_aa, to_aa):
    options = [(c,) if c != from_aa else (from_aa, to_aa) for c in seq]
    return list(''.join(o) for o in product(*options))


def filter_unique_peptides(peptides, score, ns):
    """ Filters unique peptides from multiple Percolator output XML files.
        Takes a dir with a set of XMLs, a score to filter on and a namespace.
        Outputs an ElementTree.
    """
    scores = {'q': 'q_value',
              'pep': 'pep',
              'p': 'p_value',
              'svm': 'svm_score'}
    highest = {}
    for el in peptides:
        featscore = float(el.xpath('xmlns:%s' % scores[score],
                                   namespaces=ns)[0].text)
        seq = reader.get_peptide_seq(el, ns)

        if seq not in highest:
            highest[seq] = {
                'pep_el': formatting.stringify_strip_namespace_declaration(
                    el, ns), 'score': featscore}
        if score == 'svm':  # greater than score is accepted
            if featscore > highest[seq]['score']:
                highest[seq] = {
                    'pep_el':
                    formatting.stringify_strip_namespace_declaration(el, ns),
                    'score': featscore}
        else:  # lower than score is accepted
            if featscore < highest[seq]['score']:
                highest[seq] = {
                    'pep_el':
                    formatting.stringify_strip_namespace_declaration(el, ns),
                    'score': featscore}
        formatting.clear_el(el)

    for pep in list(highest.values()):
        yield pep['pep_el']
