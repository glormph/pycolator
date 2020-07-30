import sys
from math import log
from statistics import median, StatisticsError
from collections import OrderedDict

from app.dataformats import prottable as prottabledata
from app.readers import tsv as reader


ISOQUANTRATIO_FEAT_ACC = '##isoquant_target_acc##'


def get_isobaric_ratios(psmfn, psmheader, channels, denom_channels, sweep,
        report_intensity, summarize_by, min_int, targetfeats, target_acc_field, accessioncol,
        logintensities=False, normalize=False):
    """Main function to calculate ratios for PSMs, peptides, proteins, genes.
    Can do simple ratios, median-of-ratios, median-centering, log2, etc
    """
    outratios = get_psmratios(psmfn, psmheader, channels, denom_channels,
            sweep, report_intensity, summarize_by, min_int, accessioncol, logintensities)
    # at this point, outratios look like:
    # [{ch1: 123, ch2: 456, ISOQUANTRATIO_FEAT_ACC: ENSG1244}, ]
    if accessioncol:
        if normalize:
            outratios = mediancenter_ratios(outratios, channels, logintensities)
        if targetfeats:
            outratios = {x.pop(ISOQUANTRATIO_FEAT_ACC): x for x in outratios}
            return output_to_targetfeats(targetfeats, target_acc_field, outratios, channels)
        else:
            # generate new table with accessions
            return ({(k if not k == ISOQUANTRATIO_FEAT_ACC else accessioncol): v
                     for k, v in ratio.items()} for ratio in outratios)
    else: 
        return paste_to_psmtable(psmfn, psmheader, outratios)


def mediancenter_ratios(ratios, channels, logratios):
    flatratios = [[feat[ch] for ch in channels] for feat in ratios]
    ch_medians = get_medians(channels, flatratios, report=True)
    for quant in ratios:
        if logratios:
            quant.update({ch: str(quant[ch] / ch_medians[ch])
                if quant[ch] != 'NA' else 'NA' for ch in channels})
        else:
            quant.update({ch: str(quant[ch] - ch_medians[ch])
                if quant[ch] != 'NA' else 'NA' for ch in channels})
        yield quant


def get_psmratios(psmfn, header, channels, denom_channels, sweep, report_intensity, 
        summarize_by, min_int, acc_col, logintensities):
    allfeats, feat_order, psmratios = {}, OrderedDict(), []
    for psm in reader.generate_tsv_psms(psmfn, header):
        ratios = calc_psm_ratios_or_int(psm, channels, denom_channels, sweep, 
                report_intensity, min_int, logintensities)
        # remove uninformative psms when adding to features
        if acc_col and (psm[acc_col] == '' or ';' in psm[acc_col] or
                        not {psm[q] for q in channels}.difference(
                            {'NA', None, False, ''})):
            continue
        elif acc_col:
            try:
                allfeats[psm[acc_col]].append(ratios)
            except KeyError:
                allfeats[psm[acc_col]] = [ratios]
            feat_order[psm[acc_col]] = 1
        else:
            psmquant = {ch: str(ratios[ix]) if ratios[ix] != 'NA' else 'NA'
                        for ix, ch in enumerate(channels)}
            psmquant[ISOQUANTRATIO_FEAT_ACC] = False
            psmratios.append(psmquant)
    if not acc_col:
        return psmratios
    else:
        outfeatures = []
        for feat in feat_order.keys():
            quants = allfeats[feat]
            outfeature = {ISOQUANTRATIO_FEAT_ACC: feat}
            if summarize_by == 'median':
                outfeature.update(get_medians(channels, quants))
            elif summarize_by == 'average':
                outfeature.update(summarize_by_averages(channels, quants))
            outfeature.update(get_no_psms(channels, quants))
            outfeatures.append(outfeature)
    return outfeatures


def get_ratios_from_fn(fn, header, channels):
    ratios = []
    for feat in reader.generate_tsv_psms(fn, header):
        ratios.append([float(feat[ch]) if feat[ch] != 'NA' else 'NA'
                       for ch in channels])
    return ratios


def paste_to_psmtable(psmfn, header, ratios):
    # loop psms in psmtable, paste the outratios in memory
    for psm, ratio in zip(reader.generate_tsv_psms(psmfn, header), ratios):
        ratio.pop(ISOQUANTRATIO_FEAT_ACC)
        ratio = {'ratio_{}'.format(ch): val for ch, val in ratio.items()}
        psm.update(ratio)
        yield psm


def output_to_targetfeats(targetfeats, acc_field, featratios, channels):
    #loop prottable, add ratios from dict, acc = key
    for feat in targetfeats:
        try:
            quants = featratios[feat[acc_field]]
        except KeyError:
            quants = {ch: 'NA' for ch in channels}
            quants.update({get_no_psms_field(ch): 'NA' for ch in channels})
        feat.update(quants)
        yield feat


def calc_psm_ratios_or_int(psm, channels, denom_channels, sweep, report_intensity,
        min_intensity, logintensities):
    # set values below min_intensity to NA
    if logintensities:
        psm_intensity = {ch: log(float(psm[ch]), 2)
                         if psm[ch] != 'NA' and float(psm[ch]) > min_intensity
                         else 'NA' for ch in channels}
    else:
        psm_intensity = {ch: float(psm[ch])
                         if psm[ch] != 'NA' and float(psm[ch]) > min_intensity
                         else 'NA' for ch in channels}
    if denom_channels:
        denomvalues = [psm_intensity[ch] for ch in denom_channels
                       if psm_intensity[ch] != 'NA']
    elif sweep:
        try:
            denomvalues = [median([x for x in psm_intensity.values() if x != 'NA'])]
        except StatisticsError:
            # Empty PSM errors on median call
            denomvalues = []
    elif report_intensity:
        # Just report intensity
        return [psm_intensity[ch] if psm_intensity[ch] != 'NA' else 'NA' for ch in channels]
    if sum(denomvalues) == 0 or len(denomvalues) == 0:
        return ['NA'] * len(channels)
    # TODO add median instead of average?
    # TODO can we use means of logged values or is that not correct? DEqMS does use it
    denom = sum(denomvalues) / len(denomvalues)
    if logintensities:
        return [psm_intensity[ch] - denom
                if psm_intensity[ch] != 'NA' else 'NA' for ch in channels]
    else:
        return [psm_intensity[ch] / denom
                if psm_intensity[ch] != 'NA' else 'NA' for ch in channels]


def summarize_by_averages(channels, ratios):
    ch_avgs = {}
    for ix, channel in enumerate(channels):
        vals = [x[ix] for x in ratios if x[ix] != 'NA']
        try:
            ch_avgs[channel] = sum(vals) / len(vals)
        except ZeroDivisionError:
            # channel is empty
            ch_avgs[channel] = 'NA'
    return ch_avgs


def get_medians(channels, ratios, report=False):
    ch_medians = {}
    for ix, channel in enumerate(channels):
        try:
            ch_medians[channel] = median([x[ix] for x in ratios
                                          if x[ix] != 'NA'])
        except StatisticsError:
            # channel is empty, common in protein quant but not in normalizing
            ch_medians[channel] = 'NA'
    if report:
        report = ('Channel intensity medians used for normalization:\n'
                  '{}'.format('\n'.join(['{} - {}'.format(ch, ch_medians[ch])
                                         for ch in channels])))
        sys.stdout.write(report)
    return ch_medians


def get_no_psms_field(quantfield):
    return '{}{}'.format(quantfield, prottabledata.HEADER_NO_PSMS_SUFFIX)


def get_no_psms(channels, ratios):
    ch_nopsms = {}
    for ix, channel in enumerate(channels):
        fieldname = get_no_psms_field(channel)
        ch_nopsms[fieldname] = len([x[ix] for x in ratios if x[ix] != 'NA'])
    return ch_nopsms