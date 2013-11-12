import sys
from lxml import etree
import filtering

# Deprecate? FIXME
def readPercout(fname):
    doc = None
    try:
        doc = etree.parse(fname)
    except Exception:
        sys.stderr.write('Could not parse XML provided in %s or error reading file. \n' % (fname))
    return doc

def get_namespace(fn):
    ns = {'xmlns':'http://per-colator.com/percolator_out/14',
    'xmlns:p' : 'http://per-colator.com/percolator_out/14',
    'xmlns:xsi':'http://www.w3.org/2001/XMLSchema-instance',
    }
    return ns
    # FIXME lookup from file


def get_percolator_static_xml(fn, ns):
    rootgen = etree.iterparse(fn, tag='{%s}percolator_output' % ns['xmlns'], events=('start',))
    root = rootgen.next()[1]
    for child in root.getchildren():
        root.remove(child)
    process = etree.iterparse(fn, tag='{%s}process_info' % ns['xmlns'], events=('start',))
    root.append(process.next()[1])
    return root


def generate_psms_multiple_fractions(fns, ns):
    for fn in fns:
        for ac,el in etree.iterparse(fn, tag='{%s}psm' % ns['xmlns']):
            yield filtering.stringify_strip_namespace_declaration(el, ns)
    
def generate_peptides_multiple_fractions(input_files, ns):
    for fn in input_files:
        for ac,el in etree.iterparse(fn, tag='{%s}peptide' % ns['xmlns']):
            yield el

def generate_peptides_by_seq_multiple_fractions(input_files, seq, ns):
    for fn in input_files:
        for ac,el in etree.iterparse(fn, tag='{%s}peptide' % ns['xmlns']):
            if el.attrib['{%s}peptide_id' % ns['xmlns']] != seq:
                continue
            yield el
