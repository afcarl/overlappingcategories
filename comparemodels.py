# comparemodels.py  version 1.1

# This script compares two models in order to determine
# how much more or less accurately they classify the
# works that are shared between them.

# It's only interested in works in the positive class,
# not works present for contrast.

# This version differs from the version in fiction
# in that the comparemodels function returns values

import csv, os

# For each model, we need a dictionary that links
# positive-class docids to their logistic predictions

def get_positives(apath):
    positives = dict()

    with open(apath, encoding = 'utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            docid = row['volid']
            if int(row['realclass']) > 0:
                positives[docid] = (int(row['realclass']), float(row['logistic']))

    return positives

def get_untrained(apath):
    untrained = dict()

    with open(apath, encoding = 'utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            docid = row['volid']
            if int(row['trainflag']) < 1:
                untrained[docid] = (int(row['realclass']), float(row['logistic']))

    return untrained

def get_allvols(apath):
    allvols = dict()

    with open(apath, encoding = 'utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            docid = row['volid']
            allvols[docid] = (int(row['realclass']), float(row['logistic']))

    return allvols

def compare_dicts(a, b):

    total = 0
    acorrect = 0
    bcorrect = 0
    diffs = []

    for key, avalue in a.items():
        if key in b:
            bvalue = b[key]

            reala, predicta = avalue
            realb, predictb = bvalue

            if reala != realb:
                print('Error condition that should not happen.')
                print('Disagreement about class of ' + key)

            total += 1

            if reala > 0.5 and predicta >= 0.5:
                acorrect += 1
            elif reala < 0.5 and predicta <= 0.5:
                acorrect += 1

            if realb > 0.5 and predictb >= 0.5:
                bcorrect += 1
            elif realb < 0.5 and predictb <= 0.5:
                bcorrect += 1

            if reala > 0.5:
                diffs.append(predicta - predictb)
            else:
                diffs.append(predictb - predicta)
            # If this was a positive volume we record the amount the original
            # prediction exceeded the deviation. If it's really negative, we
            # record the amount it undershot it. Either way, it's a list of
            # how much the original predictions were "righter than" the
            # deviations.
        else:
            print('MISSING: ' + key)

    if total > 0:
        apct = acorrect / total
        bpct = bcorrect / total
        meandiff = sum(diffs) / len(diffs)
    else:
        apct = 0
        bpct = 0
        meandiff = 0

    return total, apct, bpct, meandiff

def compare_positives():
    '''
    Compares two models using only the positive volumes they have in
    common.
    '''

    orig = input('Name of original model? ' )
    devi = input('Name of deviation model? ')

    origpath = '../results/' + orig
    devipath = '../results/' + devi

    origdict = get_positives(origpath)
    devidict = get_positives(devipath)

    total, apct, bpct, meandiff = compare_dicts(origdict, devidict)
    print('\nRESULTS\n-------')
    print('There were a total of ' + str(total) + ' volumes that overlap.')
    print('The original model got ' + str(apct) + ' correct.')
    print('The deviation got ' + str(bpct) + ' correct.')
    print('And the original prediction differed on avg by ' + str(meandiff))

def compare_untrained(orig, devi):
    '''
    Compares two models using only the volumes excluded from training
    in one of them. The tacit assumption is that they include all the
    same volumes.
    '''

    if len(orig) < 1:
        orig = input('Name of full model? ' )
    if len(devi) < 1:
        devi = input('Name of model with an untrained subset? ')

    origdict = get_allvols(orig)
    devidict = get_untrained(devi)
    print(len(devidict))

    total, apct, bpct, meandiff = compare_dicts(origdict, devidict)
    print('\nRESULTS\n-------')
    print('There were a total of ' + str(total) + ' volumes that overlap,')
    print('out of a possible ' + str(len(devidict)) + ' in the untrained subset.')
    print('The original model got ' + str(apct) + ' correct.')
    print('The deviation got ' + str(bpct) + ' correct.')
    print('And the original prediction differed on avg by ' + str(meandiff))

    return total, len(devidict), apct, bpct

if __name__ == '__main__':
    compare_untrained()


