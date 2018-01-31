#!/usr/bin/env python3

# main_experiment.py

import sys, os, csv, random
import numpy as np
import pandas as pd
import versatiletrainer2
import metaselector

import matplotlib.pyplot as plt

from scipy import stats

def add2dict(category, key, value):
    if key not in category:
        category[key] = []
    category[key].append(value)

def foldintodict(d1, d2):
    for k, v in d1.items():
        add2dict(d2, k, v)

def divide_authdict(authdict, auths, ceiling, sizecap):
    random.shuffle(auths)
    part1 = []
    part2 = []

    for a in auths:
        lastauth = a
        if len(part1) > len(part2):
            part2.extend(authdict[a])
        else:
            part1.extend(authdict[a])

    if len(part1) >= sizecap and len(part2) >= sizecap:
        return part1, part2
    else:
        with open('errorlog.txt', mode = 'a', encoding = 'utf-8') as f:
            f.write('Error: imbalanced classes\n')
            f.write(str(ceiling) + '\t' + str(len(part1)) + '\t' + str(len(part2)) + '\t' + lastauth + '\n')

        if len(part1) > sizecap:
            part2.extend(part1[sizecap: ])
        elif len(part2) > sizecap:
            part1.extend(part2[sizecap: ])
        return part1, part2

def split_metadata(master, floor, ceiling, sizecap):
    '''
    This function serves quixotic_dead_end() and should
    probably be moved closer to it. It selects a chronological
    slice of master metadata and then divides that slice
    randomly into two partitions. Each partition is turned into
    two files: one that can be used for a model of SF vs
    mainstream lit, and one that can be used for a model of
    fantasy vs mainstream lit.
    '''

    dateslice = master[(master.firstpub >= floor) & (master.firstpub <= ceiling)]

    mainstream = dict()
    sf = dict()
    fant = dict()

    for idx in dateslice.index:
        tags = set(dateslice.loc[idx, 'tags'].split('|'))
        auth = dateslice.loc[idx, 'author']

        if 'juv' in tags:
            continue
            # no juvenile fiction included

        if 'random' in tags or 'randomB' in tags:
            add2dict(mainstream, auth, idx)
            continue

        if 'sf_loc' in tags or 'sf_oclc' in tags or 'sf_bailey' in tags:
            issf = True
        else:
            issf = False

        if 'fantasy_loc' in tags or 'fantasy_oclc' in tags or 'supernat' in tags:
            isfant = True
        else:
            isfant = False

        if issf and isfant:
            whim = random.choice([True, False])
            if whim:
                add2dict(sf, auth, idx)
            else:
                add2dict(fant, auth, idx)

        elif issf:
            add2dict(sf, auth, idx)

        elif isfant:
            add2dict(fant, auth, idx)

        else:
            pass
            # do precisely nothing

    sfauths = list(sf.keys())
    fantasyauths = list(fant.keys())
    mainstreamauths = list(mainstream.keys())

    maindocs1, maindocs2 = divide_authdict(mainstream, mainstreamauths, ceiling, sizecap)
    fantdocs1, fantdocs2 = divide_authdict(fant, fantasyauths, ceiling, sizecap)
    sfdocs1, sfdocs2 = divide_authdict(sf, sfauths, ceiling, sizecap)

    sf1 = master.loc[sfdocs1 + maindocs1]
    sf2 = master.loc[sfdocs2 + maindocs2]

    fant1 = master.loc[fantdocs1 + maindocs1]
    fant2 = master.loc[fantdocs2 + maindocs2]

    sf1.to_csv('../temp/sf1.csv')
    sf2.to_csv('../temp/sf2.csv')
    fant1.to_csv('../temp/fant1.csv')
    fant2.to_csv('../temp/fant2.csv')

def split_one_genre(master, floor, ceiling, positive_tags, genrename, sizecap):
    '''
    This function serves reliable_change_comparisons().
    '''

    dateslice = master[(master.firstpub >= floor) & (master.firstpub <= ceiling)]

    mainstream = dict()
    genre = dict()

    for idx in dateslice.index:
        tags = set(dateslice.loc[idx, 'tags'].split('|'))
        auth = dateslice.loc[idx, 'author']

        if 'juv' in tags:
            continue
            # no juvenile fiction included

        if 'random' in tags or 'randomB' in tags:
            add2dict(mainstream, auth, idx)
            continue

        for t in positive_tags:
            if t in tags:
                add2dict(genre, auth, idx)
                break

    genreauths = list(genre.keys())
    mainstreamauths = list(mainstream.keys())

    maindocs1, maindocs2 = divide_authdict(mainstream, mainstreamauths, ceiling, sizecap)
    genredocs1, genredocs2 = divide_authdict(genre, genreauths, ceiling, sizecap)

    partition1 = master.loc[genredocs1 + maindocs1]
    partition2 = master.loc[genredocs2 + maindocs2]

    partition1.to_csv('../temp/' + genrename + '1.csv')
    partition2.to_csv('../temp/' + genrename + '2.csv')

def fantasy_periods():
    print('fantasy periods:')

    if not os.path.isfile('../results/fantasy_nojuv_periods.tsv'):
        with open('../results/fantasy_nojuv_periods.tsv', mode = 'w', encoding = 'utf-8') as f:
            outline = 'name\tsize\tfloor\tceiling\tmeandate\taccuracy\tfeatures\tregularization\ti\n'
            f.write(outline)

    sourcefolder = '../data/'
    metadatapath = '../metadata/mastermetadata.csv'
    tags4positive = {'fantasy_loc', 'fantasy_oclc'}
    tags4negative = {'random'}
    sizecap = 75

    periods = [(1800, 1899), (1900, 1919), (1920, 1949), (1950, 1969), (1970, 1979), (1980, 1989), (1990, 1999), (2000, 2010)]

    for excludebelow, excludeabove in periods:
        for i in range (5):

            name = 'fantasynojuv' + str(excludebelow) + 'to' + str(excludeabove) + 'v' + str(i)

            vocabpath = '../lexica/' + name + '.txt'
            metadatapath = ''

            metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist = versatiletrainer2.get_simple_data(sourcefolder, metadatapath, vocabpath, tags4positive, tags4negative, sizecap, excludebelow = excludebelow, excludeabove = excludeabove, forbid4positive = {'juv'}, forbid4negative = {'juv'}, force_even_distribution = False)

            c_range = [.0003, .001, .006, .02, 0.1, 0.7, 3, 12]
            featurestart = 1000
            featureend = 6100
            featurestep = 200
            modelparams = 'logistic', 16, featurestart, featureend, featurestep, c_range

            matrix, maxaccuracy, metadata, coefficientuples, features4max, best_regularization_coef = versatiletrainer2.tune_a_model(metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist, tags4positive, tags4negative, modelparams, name, '../modeloutput/' + name + '.csv')

            meandate = int(round(np.sum(metadata.firstpub) / len(metadata.firstpub)))

            with open('../results/fantasy_nojuv_periods.tsv', mode = 'a', encoding = 'utf-8') as f:
                outline = name + '\t' + str(sizecap) + '\t' + str(excludebelow) + '\t' + str(excludeabove) + '\t' + str(meandate) + '\t' + str(maxaccuracy) + '\t' + str(features4max) + '\t' + str(best_regularization_coef) + '\t' + str(i) + '\n'
                f.write(outline)

def sf_periods():
    if not os.path.isfile('../results/sf_nojuv_periods.tsv'):
        with open('../results/sf_nojuv_periods.tsv', mode = 'w', encoding = 'utf-8') as f:
            outline = 'name\tsize\tfloor\tceiling\tmeandate\taccuracy\tfeatures\tregularization\ti\n'
            f.write(outline)

    sourcefolder = '../data/'
    metadatapath = '../metadata/mastermetadata.csv'
    tags4positive = {'sf_loc', 'sf_oclc'}
    tags4negative = {'random'}
    sizecap = 75

    periods = [(1800, 1899), (1900, 1919), (1920, 1949), (1950, 1969), (1970, 1979), (1980, 1989), (1990, 1999), (2000, 2010)]

    for excludebelow, excludeabove in periods:
        for i in range (5):

            name = 'sfnojuv' + str(excludebelow) + 'to' + str(excludeabove) + 'v' + str(i)

            vocabpath = '../lexica/' + name + '.txt'

            metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist = versatiletrainer2.get_simple_data(sourcefolder, metadatapath, vocabpath, tags4positive, tags4negative, sizecap, excludebelow = excludebelow, excludeabove = excludeabove, forbid4positive = {'juv'}, forbid4negative = {'juv'})

            c_range = [.0003, .001, .006, .02, 0.1, 0.7, 3, 12]
            featurestart = 1000
            featureend = 6100
            featurestep = 200
            modelparams = 'logistic', 16, featurestart, featureend, featurestep, c_range

            matrix, maxaccuracy, metadata, coefficientuples, features4max, best_regularization_coef = versatiletrainer2.tune_a_model(metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist, tags4positive, tags4negative, modelparams, name, '../modeloutput/' + name + '.csv')

            meandate = int(round(np.sum(metadata.firstpub) / len(metadata.firstpub)))

            with open('../results/sf_nojuv_periods.tsv', mode = 'a', encoding = 'utf-8') as f:
                outline = name + '\t' + str(sizecap) + '\t' + str(excludebelow) + '\t' + str(excludeabove) + '\t' + str(meandate) + '\t' + str(maxaccuracy) + '\t' + str(features4max) + '\t' + str(best_regularization_coef) + '\t' + str(i) + '\n'
                f.write(outline)

def accuracy(df, column):
    totalcount = len(df.realclass)
    tp = sum((df.realclass > 0.5) & (df[column] > 0.5))
    tn = sum((df.realclass <= 0.5) & (df[column] <= 0.5))
    fp = sum((df.realclass <= 0.5) & (df[column] > 0.5))
    fn = sum((df.realclass > 0.5) & (df[column] <= 0.5))
    assert totalcount == (tp + fp + tn + fn)

    return (tp + tn) / totalcount

def accuracy_loss(df):

    return accuracy(df, 'probability') - accuracy(df, 'alien_model')

def averagecorr(r1, r2):
    z1 = np.arctanh(r1)
    z2 = np.arctanh(r2)
    themean = (z1 + z2) / 2
    return np.tanh(themean)

def write_a_row(r, outfile, columns):
    with open(outfile, mode = 'a', encoding = 'utf-8') as f:
        scribe = csv.DictWriter(f, fieldnames = columns, delimiter = '\t')
        scribe.writerow(r)

def sf2fantasy_divergence():

    columns = ['testype', 'name1', 'name2', 'acc1', 'acc2', 'spearman', 'spear1on2', 'spear2on1', 'loss', 'loss1on2', 'loss2on1', 'meandate', 'ceiling', 'floor']

    outfile = '../results/sf2fantasynojuv.tsv'

    if not os.path.isfile(outfile):
        with open(outfile, mode = 'a', encoding = 'utf-8') as f:
            scribe = csv.DictWriter(f, delimiter = '\t', fieldnames = columns)
            scribe.writeheader()

    fantasymodels = pd.read_csv('../results/fantasy_nojuv_periods.tsv', sep = '\t')
    sfmodels = pd.read_csv('../results/sf_nojuv_periods.tsv', sep = '\t')

    # We group both sets by the "ceiling" columns, which is just a way of grouping models
    # that cover the same period. ("Meandate" is a better representation of central
    # tendency, but it can vary from one model to the next.)

    fantasy_grouped = fantasymodels.groupby('ceiling')
    sf_grouped = sfmodels.groupby('ceiling')

    fangroups = dict()
    sfgroups = dict()

    for ceiling, group in fantasy_grouped:
        fangroups[ceiling] = group

    for ceiling, group in sf_grouped:
        sfgroups[ceiling] = group

    for ceiling, fangroup in fangroups.items():
        for i1 in fangroup.index:

            # For each fantasy model in this ceiling group,
            # first, we test it against other fantasy models
            # in the same group.

            for i2 in fangroup.index:
                if i1 == i2:
                    continue
                    # we don't test a model against itself

                r = dict()
                r['testype'] = 'fantasyself'
                r['ceiling'] = ceiling
                r['floor'] = fangroup.loc[i1, 'floor']
                r['name1'] = fangroup.loc[i1, 'name']
                r['name2'] = fangroup.loc[i2, 'name']
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'] = get_divergence(r['name1'], r['name2'])
                r['acc1'] = fangroup.loc[i1, 'accuracy']
                r['acc2'] = fangroup.loc[i2, 'accuracy']
                r['meandate'] = (fangroup.loc[i1, 'meandate'] + fangroup.loc[i2, 'meandate']) / 2

                write_a_row(r, outfile, columns)

            sfgroup = sfgroups[ceiling]
            for idx in sfgroup.index:

                r = dict()
                r['testype'] = 'cross'
                r['ceiling'] = ceiling
                r['floor'] = fangroup.loc[i1, 'floor']
                r['name1'] = fangroup.loc[i1, 'name']
                r['name2'] = sfgroup.loc[idx, 'name']
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'] = get_divergence(r['name1'], r['name2'])
                r['acc1'] = fangroup.loc[i1, 'accuracy']
                r['acc2'] = sfgroup.loc[idx, 'accuracy']
                r['meandate'] = (fangroup.loc[i1, 'meandate'] + sfgroup.loc[idx, 'meandate']) / 2

                write_a_row(r, outfile, columns)

    # Now sf versus itself

    for ceiling, sfgroup in sfgroups.items():
        for i1 in sfgroup.index:

            # For each sf model in this ceiling group,
            # we test it against other sf models
            # in the same group.

            for i2 in sfgroup.index:
                if i1 == i2:
                    continue
                    # we don't test a model against itself

                r = dict()
                r['testype'] = 'sfself'
                r['ceiling'] = ceiling
                r['floor'] = sfgroup.loc[i1, 'floor']
                r['name1'] = sfgroup.loc[i1, 'name']
                r['name2'] = sfgroup.loc[i2, 'name']
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'] = get_divergence(r['name1'], r['name2'])
                r['acc1'] = sfgroup.loc[i1, 'accuracy']
                r['acc2'] = sfgroup.loc[i2, 'accuracy']
                r['meandate'] = (sfgroup.loc[i1, 'meandate'] + sfgroup.loc[i2, 'meandate']) / 2

                write_a_row(r, outfile, columns)

def sf_vs_fantasy():
    sourcefolder = '../data/'
    metadatapath = '../metadata/mastermetadata.csv'
    tags4positive = {'fantasy_loc', 'fantasy_oclc', 'supernat'}
    tags4negative = {'sf_loc', 'sf_oclc', 'sf_bailey'}
    sizecap = 400

    excludebelow = 1800
    excludeabove = 3000


    name = 'fantasyvsSF3'

    vocabpath = '../lexica/' + name + '.txt'

    metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist = versatiletrainer2.get_simple_data(sourcefolder, metadatapath, vocabpath, tags4positive, tags4negative, sizecap, excludebelow = excludebelow, excludeabove = excludeabove, forbid4positive = {'juv'}, forbid4negative = {'juv'}, numfeatures = 7000, force_even_distribution = True)

    # notice that I'm forbidding juvenile fiction on this run

    c_range = [.00005, .0001, .0003, .001]
    featurestart = 4000
    featureend = 5800
    featurestep = 200
    modelparams = 'logistic', 16, featurestart, featureend, featurestep, c_range

    matrix, maxaccuracy, metadata, coefficientuples, features4max, best_regularization_coef = versatiletrainer2.tune_a_model(metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist, tags4positive, tags4negative, modelparams, name, '../modeloutput/' + name + '.csv')

def sf_vs_fantasy_periods():

    outresults = '../results/sf_vs_fantasy_periods2.tsv'

    if not os.path.isfile(outresults):
        with open(outresults, mode = 'w', encoding = 'utf-8') as f:
            outline = 'name\tsize\tfloor\tceiling\tmeandate\taccuracy\tfeatures\tregularization\ti\n'
            f.write(outline)

    sourcefolder = '../data/'
    metadatapath = '../metadata/mastermetadata.csv'
    tags4positive = {'fantasy_loc', 'fantasy_oclc'}
    tags4negative = {'sf_loc', 'sf_oclc'}
    sizecap = 70

    periods = [(1800, 1899), (1900, 1919), (1920, 1949), (1950, 1969), (1970, 1979), (1980, 1989), (1990, 1999), (2000, 2010)]

    for i in range (5):
        for excludebelow, excludeabove in periods:

            name = 'sf_vs_fantasy_periods2' + str(excludebelow) + 'to' + str(excludeabove) + 'v' + str(i)

            vocabpath = '../lexica/' + name + '.txt'

            metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist = versatiletrainer2.get_simple_data(sourcefolder, metadatapath, vocabpath, tags4positive, tags4negative, sizecap, excludebelow = excludebelow, excludeabove = excludeabove, forbid4positive = {'juv'}, forbid4negative = {'juv'}, overlap_strategy = 'random')

            c_range = [.00001, .0001, .001, .01, 0.1, 1, 10, 100]
            featurestart = 1800
            featureend = 5500
            featurestep = 300
            modelparams = 'logistic', 16, featurestart, featureend, featurestep, c_range

            matrix, maxaccuracy, metadata, coefficientuples, features4max, best_regularization_coef = versatiletrainer2.tune_a_model(metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist, tags4positive, tags4negative, modelparams, name, '../modeloutput/' + name + '.csv')

            meandate = int(round(np.sum(metadata.firstpub) / len(metadata.firstpub)))

            with open(outresults, mode = 'a', encoding = 'utf-8') as f:
                outline = name + '\t' + str(sizecap) + '\t' + str(excludebelow) + '\t' + str(excludeabove) + '\t' + str(meandate) + '\t' + str(maxaccuracy) + '\t' + str(features4max) + '\t' + str(best_regularization_coef) + '\t' + str(i) + '\n'
                f.write(outline)

def reliable_genre_comparisons():
    '''
    Trying to get around contamination of my spearman comparisons
    by comparing only models *with no shared instances*.

    Edit Jan 1: To be even more careful about leakage, make that
    *no shared authors.*
    '''

    outmodels = '../results/supplement_models.tsv'
    outcomparisons = '../results/supplement_comparisons.tsv'
    columns = ['testype', 'name1', 'name2', 'ceiling', 'floor', 'meandate1', 'meandate2', 'acc1', 'acc2', 'alienacc1', 'alienacc2', 'spearman', 'spear1on2', 'spear2on1', 'loss', 'loss1on2', 'loss2on1']

    if not os.path.isfile(outcomparisons):
        with open(outcomparisons, mode = 'a', encoding = 'utf-8') as f:
            scribe = csv.DictWriter(f, delimiter = '\t', fieldnames = columns)
            scribe.writeheader()

    if not os.path.isfile(outmodels):
        with open(outmodels, mode = 'a', encoding = 'utf-8') as f:
            outline = 'name\tsize\tfloor\tceiling\tmeandate\taccuracy\tfeatures\tregularization\ti\n'
            f.write(outline)

    sourcefolder = '../data/'
    sizecap = 72

    c_range = [.00001, .0001, .001, .01, 0.1, 1, 10, 100]
    featurestart = 1500
    featureend = 6500
    featurestep = 300
    modelparams = 'logistic', 15, featurestart, featureend, featurestep, c_range

    master = pd.read_csv('../metadata/mastermetadata.csv', index_col = 'docid')
    periods = [(1800, 1909), (1880, 1924), (1900, 1949), (1910, 1959), (1930, 1969), (1950, 1979), (1970, 1989), (1980, 1999), (1990, 2010)]
    forbiddenwords = {'fantasy', 'fiction', 'science', 'horror'}

    # endpoints both inclusive

    for i in range(15):
        for floor, ceiling in periods:

            split_metadata(master, floor, ceiling, sizecap)

            metaoptions = ['sf1', 'sf2', 'fant1', 'fant2']

            for m in metaoptions:
                metadatapath = '../temp/' + m + '.csv'
                vocabpath = '../lexica/' + m + '.txt'
                name = 'temp_' + m + str(ceiling) + '_' + str(i)

                if m == 'sf1' or m == 'sf2':
                    tags4positive = {'sf_loc', 'sf_oclc', 'sf_bailey'}
                else:
                    tags4positive = {'fantasy_loc', 'fantasy_oclc', 'supernat'}

                tags4negative = {'random', 'randomB'}

                metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist = versatiletrainer2.get_simple_data(sourcefolder, metadatapath, vocabpath, tags4positive, tags4negative, sizecap, excludebelow = floor, excludeabove = ceiling, forbid4positive = {'juv'}, forbid4negative = {'juv'}, force_even_distribution = False, numfeatures = 6500, forbiddenwords = forbiddenwords)

                matrix, maxaccuracy, metadata, coefficientuples, features4max, best_regularization_coef = versatiletrainer2.tune_a_model(metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist, tags4positive, tags4negative, modelparams, name, '../modeloutput/' + name + '.csv')

                meandate = int(round(np.sum(metadata.firstpub) / len(metadata.firstpub)))

                with open(outmodels, mode = 'a', encoding = 'utf-8') as f:
                    outline = name + '\t' + str(sizecap) + '\t' + str(floor) + '\t' + str(ceiling) + '\t' + str(meandate) + '\t' + str(maxaccuracy) + '\t' + str(features4max) + '\t' + str(best_regularization_coef) + '\t' + str(i) + '\n'
                    f.write(outline)

                os.remove(vocabpath)

            r = dict()
            r['testype'] = 'sfself'
            r['ceiling'] = ceiling
            r['floor'] = floor
            r['name1'] = 'temp_sf1' + str(ceiling) + '_' + str(i)
            r['name2'] = 'temp_sf2' + str(ceiling) + '_' + str(i)
            r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])
            write_a_row(r, outcomparisons, columns)

            r = dict()
            r['testype'] = 'fantasyself'
            r['ceiling'] = ceiling
            r['floor'] = floor
            r['name1'] = 'temp_fant1' + str(ceiling) + '_' + str(i)
            r['name2'] = 'temp_fant2' + str(ceiling) + '_' + str(i)
            r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])
            write_a_row(r, outcomparisons, columns)

            r = dict()
            r['testype'] = 'cross'
            r['ceiling'] = ceiling
            r['floor'] = floor
            r['name1'] = 'temp_sf1' + str(ceiling) + '_' + str(i)
            r['name2'] = 'temp_fant2' + str(ceiling) + '_' + str(i)
            r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])
            write_a_row(r, outcomparisons, columns)

            r = dict()
            r['testype'] = 'cross'
            r['ceiling'] = ceiling
            r['floor'] = floor
            r['name1'] = 'temp_sf2' + str(ceiling) + '_' + str(i)
            r['name2'] = 'temp_fant1' + str(ceiling) + '_' + str(i)
            r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])
            write_a_row(r, outcomparisons, columns)

def reliable_change_comparisons():
    '''
    Using the same method in the previous function, but to assess
    change in SF.
    '''

    outmodels = '../results/change_models.tsv'
    outcomparisons = '../results/change_comparisons.tsv'
    columns = ['testype', 'name1', 'name2', 'ceiling1', 'floor1', 'ceiling2', 'floor2', 'meandate1', 'meandate2', 'acc1', 'acc2', 'alienacc1', 'alienacc2', 'spearman', 'spear1on2', 'spear2on1', 'loss', 'loss1on2', 'loss2on1']

    if not os.path.isfile(outcomparisons):
        with open(outcomparisons, mode = 'a', encoding = 'utf-8') as f:
            scribe = csv.DictWriter(f, delimiter = '\t', fieldnames = columns)
            scribe.writeheader()

    if not os.path.isfile(outmodels):
        with open(outmodels, mode = 'a', encoding = 'utf-8') as f:
            outline = 'name\tsize\tfloor\tceiling\tmeandate\taccuracy\tfeatures\tregularization\ti\n'
            f.write(outline)

    sourcefolder = '../data/'
    sizecap = 50

    c_range = [.00001, .0001, .001, .01, 0.1, 1, 10, 100]
    featurestart = 1500
    featureend = 6500
    featurestep = 300
    modelparams = 'logistic', 15, featurestart, featureend, featurestep, c_range

    master = pd.read_csv('../metadata/mastermetadata.csv', index_col = 'docid')
    periods = [(1870, 1899), (1900, 1929), (1930, 1959), (1960, 1989), (1990, 2010), (1880, 1909), (1910, 1939), (1940, 1969), (1970, 1999), (1890, 1919), (1920, 1949), (1950, 1979), (1980, 2009)]
    forbiddenwords = {'fantasy', 'fiction', 'science', 'horror'}

    # endpoints both inclusive

    for i in range(5):
        for floor, ceiling in periods:

            namestart = 'rccsf'+ str(floor) + '_' + str(ceiling) + '_' + str(i) + '_'

            split_one_genre(master, floor, ceiling, {'sf_loc', 'sf_oclc', 'sf_bailey'}, namestart, sizecap)

            names = []

            for partition in ['1', '2']:
                name = namestart + partition
                names.append(name)

                metadatapath = '../temp/' + name + '.csv'
                vocabpath = '../lexica/' + name + '.txt'

                tags4positive = {'sf_loc', 'sf_oclc', 'sf_bailey'}
                tags4negative = {'random', 'randomB'}

                metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist = versatiletrainer2.get_simple_data(sourcefolder, metadatapath, vocabpath, tags4positive, tags4negative, sizecap, excludebelow = floor, excludeabove = ceiling, forbid4positive = {'juv'}, forbid4negative = {'juv'}, force_even_distribution = False, numfeatures = 6500, forbiddenwords = forbiddenwords)

                matrix, maxaccuracy, metadata, coefficientuples, features4max, best_regularization_coef = versatiletrainer2.tune_a_model(metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist, tags4positive, tags4negative, modelparams, name, '../modeloutput/' + name + '.csv')

                meandate = int(round(np.sum(metadata.firstpub) / len(metadata.firstpub)))

                with open(outmodels, mode = 'a', encoding = 'utf-8') as f:
                    outline = name + '\t' + str(sizecap) + '\t' + str(floor) + '\t' + str(ceiling) + '\t' + str(meandate) + '\t' + str(maxaccuracy) + '\t' + str(features4max) + '\t' + str(best_regularization_coef) + '\t' + str(i) + '\n'
                    f.write(outline)

                os.remove(vocabpath)

def cross_reliable_change():

    periodsets = []

    periodsets.append([(1870, 1899), (1900, 1929), (1930, 1959), (1960, 1989), (1990, 2010)])
    periodsets.append([(1880, 1909), (1910, 1939), (1940, 1969), (1970, 1999)])
    periodsets.append([(1890, 1919), (1920, 1949), (1950, 1979), (1980, 2009)])

    outcomparisons = '../results/change_comparisons.tsv'
    columns = ['testype', 'name1', 'name2', 'ceiling1', 'floor1', 'ceiling2', 'floor2', 'meandate1', 'meandate2', 'acc1', 'acc2', 'alienacc1', 'alienacc2', 'spearman', 'spear1on2', 'spear2on1', 'loss', 'loss1on2', 'loss2on1']

    if not os.path.isfile(outcomparisons):
        with open(outcomparisons, mode = 'a', encoding = 'utf-8') as f:
            scribe = csv.DictWriter(f, delimiter = '\t', fieldnames = columns)
            scribe.writeheader()

    for pset in range(3):
        periods = periodsets[pset]

        for i in range(5):
            for idx, floorandceiling in enumerate(periods):
                f1, c1 = floorandceiling

                # first, self-comparison between partitions for a particular
                # period and iteration.

                name1 = 'rccsf'+ str(f1) + '_' + str(c1) + '_' + str(i) + '_1'
                name2 = 'rccsf'+ str(f1) + '_' + str(c1) + '_' + str(i) + '_2'

                r = dict()
                r['testype'] = 'self'
                r['ceiling1'] = c1
                r['floor1'] = f1
                r['ceiling2'] = c1
                r['floor2'] = f1
                r['name1'] = name1
                r['name2'] = name2
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

                # Now let's do cross comparisons between this period and the next
                # But only if there is a next!

                if idx + 1 >= len(periods):
                    continue
                else:
                    f2, c2 = periods[idx + 1]
                    print(f1, c1, f2, c2)

                for j in range(5):

                    partition = random.choice(['1', '2'])
                    # we're randomizing that only to cut the total
                    # number of comparisons in half; we have enough!

                    name1 = 'rccsf'+ str(f1) + '_' + str(c1) + '_' + str(i) + '_' + partition
                    name2 = 'rccsf'+ str(f2) + '_' + str(c2) + '_' + str(j) + '_' + partition

                    r = dict()
                    r['testype'] = 'cross'
                    r['ceiling1'] = c1
                    r['floor1'] = f1
                    r['ceiling2'] = c2
                    r['floor2'] = f2
                    r['name1'] = name1
                    r['name2'] = name2
                    r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                    write_a_row(r, outcomparisons, columns)

def get_surprising_books(sampleA, sampleB):

    '''
    This function applies model a to b, and vice versa, and returns
    two dictionaries pairing volumes with differences in
    z-scores. Not yet complete.
    '''

    # We start by constructing the paths to the sampleA
    # standard model criteria (.pkl) and
    # model output (.csv) on the examples
    # originally used to train it.

    # We're going to try applying the sampleA standard
    # criteria to another model's output, and vice-
    # versa.

    model1 = '../modeloutput/' + sampleA + '.pkl'
    meta1 = '../modeloutput/' + sampleA + '.csv'

    # Now we construct paths to the test model
    # criteria (.pkl) and output (.csv).

    model2 = '../modeloutput/' + sampleB + '.pkl'
    meta2 = '../modeloutput/' + sampleB + '.csv'

    model1on2 = versatiletrainer2.apply_pickled_model(model1, '../data/', '.tsv', meta2)
    model2on1 = versatiletrainer2.apply_pickled_model(model2, '../data/', '.tsv', meta1)

    diff = stats.zscore(model1on2.probability) - stats.zscore(model1on2.alien_model)
    diff1to2 = {k:v for k, v in zip(model1on2.index, diff)}

    diff = stats.zscore(model2on1.probability) - stats.zscore(model2on1.alien_model)
    diff2to1 = {k:v for k, v in zip(model2on1.index, diff)}

    probs1 = {k:v for k, v in zip(model1on2.index, model1on2.probability)}
    alien1 = {k:v for k, v in zip(model1on2.index, model1on2.alien_model)}
    probs2 = {k:v for k, v in zip(model2on1.index, model2on1.probability)}
    alien2 = {k:v for k, v in zip(model2on1.index, model2on1.alien_model)}

    return diff1to2, diff2to1, probs1, alien1, probs2, alien2

def get_rcc_surprise(date):
    periods = [(1870, 1899), (1900, 1929), (1930, 1959), (1960, 1989), (1990, 2010), (1880, 1909), (1910, 1939), (1940, 1969), (1970, 1999), (1890, 1919), (1920, 1949), (1950, 1979), (1980, 2009)]

    # identify the periods at issue

    for floor, ceiling in periods:
        if ceiling+ 1 == date:
            f1, c1 = floor, ceiling
        if floor == date:
            f2, c2 = floor, ceiling

    surprisingly_new = dict()
    surprisingly_old = dict()
    original_new = dict()
    alien_new = dict()
    original_old = dict()
    alien_old = dict()

    for i in range(5):
        for j in range(5):
            for part in [1, 2]:

                name1 = 'rccsf'+ str(f1) + '_' + str(c1) + '_' + str(i) + '_' + str(part)
                name2 = 'rccsf'+ str(f2) + '_' + str(c2) + '_' + str(j) + '_' + str(part)

                diff1to2, diff2to1, probs1, alien1, probs2, alien2 = get_surprising_books(name1, name2)

                foldintodict(diff1to2, surprisingly_new)
                foldintodict(diff2to1, surprisingly_old)
                foldintodict(probs1, original_new)
                foldintodict(alien1, alien_new)
                foldintodict(probs2, original_old)
                foldintodict(alien2, alien_old)

    meta = pd.read_csv('../metadata/mastermetadata.csv', index_col = 'docid')

    outfile = '../results/sf' + str(date) + 'newsurprises.tsv'
    with open(outfile, mode = 'w', encoding = 'utf-8') as f:
        scribe = csv.DictWriter(f, delimiter = '\t', fieldnames = ['docid', 'diff', 'original', 'alien', 'firstpub', 'author', 'tags', 'title'])
        scribe.writeheader()
        for k, v in surprisingly_new.items():
            o = dict()
            o['docid'] = k
            o['diff'] = sum(v) / len(v)
            o['author'] = meta.loc[k, 'author']
            o['title'] = meta.loc[k, 'title']
            o['firstpub'] = meta.loc[k, 'firstpub']
            o['tags'] = meta.loc[k, 'tags']
            o['original'] = sum(original_new[k]) / len(original_new[k])
            o['alien'] = sum(alien_new[k]) / len(alien_new[k])
            scribe.writerow(o)

    outfile = '../results/sf' + str(date) + 'oldsurprises.tsv'
    with open(outfile, mode = 'w', encoding = 'utf-8') as f:
        scribe = csv.DictWriter(f, delimiter = '\t', fieldnames = ['docid', 'diff', 'original', 'alien', 'firstpub', 'author', 'tags', 'title'])
        scribe.writeheader()
        for k, v in surprisingly_old.items():
            o = dict()
            o['docid'] = k
            o['diff'] = sum(v) / len(v)
            o['author'] = meta.loc[k, 'author']
            o['title'] = meta.loc[k, 'title']
            o['firstpub'] = meta.loc[k, 'firstpub']
            o['tags'] = meta.loc[k, 'tags']
            o['original'] = sum(original_old[k]) / len(original_old[k])
            o['alien'] = sum(alien_old[k]) / len(alien_old[k])
            scribe.writerow(o)

def get_fantasy_surprise(date):
    periods = [(1800, 1899), (1900, 1919), (1920, 1949), (1950, 1969), (1970, 1979), (1980, 1989), (1990, 1999), (2000, 2009)]

    # identify the periods at issue

    for floor, ceiling in periods:
        if ceiling+ 1 == date:
            f1, c1 = floor, ceiling
        if floor == date:
            f2, c2 = floor, ceiling

    surprisingly_new = dict()
    surprisingly_old = dict()
    original_new = dict()
    alien_new = dict()
    original_old = dict()
    alien_old = dict()

    for i in range(5):
        for j in range(5):

            name1 = 'fantasynojuv'+ str(f1) + 'to' + str(c1) + 'v' + str(i)
            name2 = 'fantasynojuv'+ str(f2) + 'to' + str(c2) + 'v' + str(j)

            diff1to2, diff2to1, probs1, alien1, probs2, alien2 = get_surprising_books(name1, name2)

            foldintodict(diff1to2, surprisingly_new)
            foldintodict(diff2to1, surprisingly_old)
            foldintodict(probs1, original_new)
            foldintodict(alien1, alien_new)
            foldintodict(probs2, original_old)
            foldintodict(alien2, alien_old)

    meta = pd.read_csv('../metadata/mastermetadata.csv', index_col = 'docid')

    outfile = '../results/fantasy' + str(date) + 'newsurprises.tsv'
    with open(outfile, mode = 'w', encoding = 'utf-8') as f:
        scribe = csv.DictWriter(f, delimiter = '\t', fieldnames = ['docid', 'diff', 'original', 'alien', 'firstpub', 'author', 'tags', 'title'])
        scribe.writeheader()
        for k, v in surprisingly_new.items():
            o = dict()
            o['docid'] = k
            o['diff'] = sum(v) / len(v)
            o['author'] = meta.loc[k, 'author']
            o['title'] = meta.loc[k, 'title']
            o['firstpub'] = meta.loc[k, 'firstpub']
            o['tags'] = meta.loc[k, 'tags']
            o['original'] = sum(original_new[k]) / len(original_new[k])
            o['alien'] = sum(alien_new[k]) / len(alien_new[k])
            scribe.writerow(o)

    outfile = '../results/fantasy' + str(date) + 'oldsurprises.tsv'
    with open(outfile, mode = 'w', encoding = 'utf-8') as f:
        scribe = csv.DictWriter(f, delimiter = '\t', fieldnames = ['docid', 'diff', 'original', 'alien', 'firstpub', 'author', 'tags', 'title'])
        scribe.writeheader()
        for k, v in surprisingly_old.items():
            o = dict()
            o['docid'] = k
            o['diff'] = sum(v) / len(v)
            o['author'] = meta.loc[k, 'author']
            o['title'] = meta.loc[k, 'title']
            o['firstpub'] = meta.loc[k, 'firstpub']
            o['tags'] = meta.loc[k, 'tags']
            o['original'] = sum(original_old[k]) / len(original_old[k])
            o['alien'] = sum(alien_old[k]) / len(alien_old[k])
            scribe.writerow(o)

def bailey_to_postwar():
    outmodels = '../results/bailey_to_postwar_models.tsv'
    outcomparisons = '../results/bailey_to_postwar_comparisons.tsv'
    columns = ['testype', 'name1', 'name2', 'spearman', 'spear1on2', 'spear2on1', 'loss', 'loss1on2', 'loss2on1']

    if not os.path.isfile(outcomparisons):
        with open(outcomparisons, mode = 'a', encoding = 'utf-8') as f:
            scribe = csv.DictWriter(f, delimiter = '\t', fieldnames = columns)
            scribe.writeheader()

    if not os.path.isfile(outmodels):
        with open(outmodels, mode = 'a', encoding = 'utf-8') as f:
            outline = 'name\tsize\tfloor\tceiling\tmeandate\taccuracy\tfeatures\tregularization\ti\n'
            f.write(outline)

    sourcefolder = '../data/'
    sizecap = 74

    c_range = [.00001, .0001, .001, .01, 0.1, 1, 10, 100]
    featurestart = 1500
    featureend = 5500
    featurestep = 300
    modelparams = 'logistic', 15, featurestart, featureend, featurestep, c_range
    metadatapath = '../metadata/mastermetadata.csv'

    accuracies = dict()
    meandates = dict()

    for i in range(3):

        name = 'bailey' + str(i)
        vocabpath = '../lexica/' + name + '.txt'
        tags4positive = {'sf_bailey'}
        tags4negative = {'random'}
        floor = 1800
        ceiling = 1920

        metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist = versatiletrainer2.get_simple_data(sourcefolder, metadatapath, vocabpath, tags4positive, tags4negative, sizecap, excludebelow = floor, excludeabove = ceiling, forbid4positive = {'juv'}, forbid4negative = {'juv'}, force_even_distribution = False, negative_strategy = 'closely match')

        matrix, maxaccuracy, metadata, coefficientuples, features4max, best_regularization_coef = versatiletrainer2.tune_a_model(metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist, tags4positive, tags4negative, modelparams, name, '../modeloutput/' + name + '.csv')

        meandate = int(round(np.sum(metadata.firstpub) / len(metadata.firstpub)))
        accuracies[name] = maxaccuracy
        meandates[name] = meandate

        with open(outmodels, mode = 'a', encoding = 'utf-8') as f:
            outline = name + '\t' + str(sizecap) + '\t' + str(floor) + '\t' + str(ceiling) + '\t' + str(meandate) + '\t' + str(maxaccuracy) + '\t' + str(features4max) + '\t' + str(best_regularization_coef) + '\t' + str(i) + '\n'
            f.write(outline)

        os.remove(vocabpath)

        name = 'postwarSF' + str(i)
        vocabpath = '../lexica/' + name + '.txt'
        tags4positive = {'sf_loc', 'sf_oclc'}
        tags4negative = {'random'}
        floor = 1945
        ceiling = 2010

        metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist = versatiletrainer2.get_simple_data(sourcefolder, metadatapath, vocabpath, tags4positive, tags4negative, sizecap, excludebelow = floor, excludeabove = ceiling, forbid4positive = {'juv'}, forbid4negative = {'juv'}, force_even_distribution = False, negative_strategy = 'closely match')

        matrix, maxaccuracy, metadata, coefficientuples, features4max, best_regularization_coef = versatiletrainer2.tune_a_model(metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist, tags4positive, tags4negative, modelparams, name, '../modeloutput/' + name + '.csv')

        meandate = int(round(np.sum(metadata.firstpub) / len(metadata.firstpub)))
        accuracies[name] = maxaccuracy
        meandates[name] = meandate

        with open(outmodels, mode = 'a', encoding = 'utf-8') as f:
            outline = name + '\t' + str(sizecap) + '\t' + str(floor) + '\t' + str(ceiling) + '\t' + str(meandate) + '\t' + str(maxaccuracy) + '\t' + str(features4max) + '\t' + str(best_regularization_coef) + '\t' + str(i) + '\n'
            f.write(outline)

        os.remove(vocabpath)

    for i in range(3):
        for j in range(3):

            r = dict()
            r['testype'] = 'bailey-postwar'
            r['name1'] = 'bailey' + str(i)
            r['name2'] = 'postwarSF' + str(j)
            r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], altloss = get_divergence(r['name1'], r['name2'])

            write_a_row(r, outcomparisons, columns)

def bailey_to_detective():
    outmodels = '../results/bailey_to_detective_models.tsv'
    outcomparisons = '../results/bailey_to_detective_comparisons.tsv'
    columns = ['testype', 'name1', 'name2', 'spearman', 'spear1on2', 'spear2on1', 'loss', 'loss1on2', 'loss2on1']

    if not os.path.isfile(outcomparisons):
        with open(outcomparisons, mode = 'a', encoding = 'utf-8') as f:
            scribe = csv.DictWriter(f, delimiter = '\t', fieldnames = columns)
            scribe.writeheader()

    if not os.path.isfile(outmodels):
        with open(outmodels, mode = 'a', encoding = 'utf-8') as f:
            outline = 'name\tsize\tfloor\tceiling\tmeandate\taccuracy\tfeatures\tregularization\ti\n'
            f.write(outline)

    sourcefolder = '../data/'
    sizecap = 74

    c_range = [.00001, .0001, .001, .01, 0.1, 1, 10, 100]
    featurestart = 1500
    featureend = 5000
    featurestep = 300
    modelparams = 'logistic', 15, featurestart, featureend, featurestep, c_range
    metadatapath = '../metadata/mastermetadata.csv'

    for i in range(3):

        name = 'detective' + str(i)
        vocabpath = '../lexica/' + name + '.txt'
        tags4positive = {'detective'}
        tags4negative = {'random'}
        floor = 1800
        ceiling = 1920

        metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist = versatiletrainer2.get_simple_data(sourcefolder, metadatapath, vocabpath, tags4positive, tags4negative, sizecap, excludebelow = floor, excludeabove = ceiling, forbid4positive = {'juv'}, forbid4negative = {'juv'}, force_even_distribution = False, negative_strategy = 'closely match')

        matrix, maxaccuracy, metadata, coefficientuples, features4max, best_regularization_coef = versatiletrainer2.tune_a_model(metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist, tags4positive, tags4negative, modelparams, name, '../modeloutput/' + name + '.csv')

        meandate = int(round(np.sum(metadata.firstpub) / len(metadata.firstpub)))

        with open(outmodels, mode = 'a', encoding = 'utf-8') as f:
            outline = name + '\t' + str(sizecap) + '\t' + str(floor) + '\t' + str(ceiling) + '\t' + str(meandate) + '\t' + str(maxaccuracy) + '\t' + str(features4max) + '\t' + str(best_regularization_coef) + '\t' + str(i) + '\n'
            f.write(outline)

        os.remove(vocabpath)

    for i in range(3):
        for j in range(3):

            r = dict()
            r['testype'] = 'bailey-detective'
            r['name1'] = 'bailey' + str(i)
            r['name2'] = 'detective' + str(j)
            r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], altloss = get_divergence(r['name1'], r['name2'])

            write_a_row(r, outcomparisons, columns)

def bailey_to_19cSF():
    '''
    Compares works from the JO Bailey bibliography (1934) to works from the same period
    tagged as SF by contemporary librarians.
    '''

    outmodels = '../results/bailey_to_19cSF_models.tsv'
    outcomparisons = '../results/bailey_to_19cSF_comparisons.tsv'
    columns = ['testype', 'name1', 'name2', 'ceiling1', 'floor1', 'ceiling2', 'floor2', 'meandate1', 'meandate2', 'acc1', 'acc2', 'alienacc1', 'alienacc2', 'spearman', 'spear1on2', 'spear2on1', 'loss', 'loss1on2', 'loss2on1']

    if not os.path.isfile(outcomparisons):
        with open(outcomparisons, mode = 'a', encoding = 'utf-8') as f:
            scribe = csv.DictWriter(f, delimiter = '\t', fieldnames = columns)
            scribe.writeheader()

    if not os.path.isfile(outmodels):
        with open(outmodels, mode = 'a', encoding = 'utf-8') as f:
            outline = 'name\tsize\tfloor\tceiling\tmeandate\taccuracy\tfeatures\tregularization\ti\n'
            f.write(outline)

    sourcefolder = '../data/'
    sizecap = 70

    c_range = [.00001, .0001, .001, .01, 0.1, 1, 10, 100]
    featurestart = 1500
    featureend = 6000
    featurestep = 300
    modelparams = 'logistic', 15, featurestart, featureend, featurestep, c_range
    metadatapath = '../metadata/mastermetadata.csv'

    for contrast in ['random', 'randomB']:
        for i in range(3):

            name = '19cSF_' + contrast + '_' + str(i)
            vocabpath = '../lexica/' + name + '.txt'
            tags4positive = {'sf_loc', 'sf_oclc'}
            tags4negative = {contrast}
            floor = 1800
            ceiling = 1920

            metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist = versatiletrainer2.get_simple_data(sourcefolder, metadatapath, vocabpath, tags4positive, tags4negative, sizecap, excludebelow = floor, excludeabove = ceiling, forbid4positive = {'juv'}, forbid4negative = {'juv'}, force_even_distribution = False, negative_strategy = 'closely match', numfeatures = 6000)

            matrix, maxaccuracy, metadata, coefficientuples, features4max, best_regularization_coef = versatiletrainer2.tune_a_model(metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist, tags4positive, tags4negative, modelparams, name, '../modeloutput/' + name + '.csv')

            meandate = int(round(np.sum(metadata.firstpub) / len(metadata.firstpub)))

            with open(outmodels, mode = 'a', encoding = 'utf-8') as f:
                outline = name + '\t' + str(sizecap) + '\t' + str(floor) + '\t' + str(ceiling) + '\t' + str(meandate) + '\t' + str(maxaccuracy) + '\t' + str(features4max) + '\t' + str(best_regularization_coef) + '\t' + str(i) + '\n'
                f.write(outline)

            os.remove(vocabpath)

            name = 'bailey_' + contrast + '_' + str(i)
            vocabpath = '../lexica/' + name + '.txt'
            tags4positive = {'sf_bailey'}
            tags4negative = {contrast}
            floor = 1800
            ceiling = 1920

            metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist = versatiletrainer2.get_simple_data(sourcefolder, metadatapath, vocabpath, tags4positive, tags4negative, sizecap, excludebelow = floor, excludeabove = ceiling, forbid4positive = {'juv'}, forbid4negative = {'juv'}, force_even_distribution = False, negative_strategy = 'closely match', numfeatures = 6000)

            matrix, maxaccuracy, metadata, coefficientuples, features4max, best_regularization_coef = versatiletrainer2.tune_a_model(metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist, tags4positive, tags4negative, modelparams, name, '../modeloutput/' + name + '.csv')

            meandate = int(round(np.sum(metadata.firstpub) / len(metadata.firstpub)))

            with open(outmodels, mode = 'a', encoding = 'utf-8') as f:
                outline = name + '\t' + str(sizecap) + '\t' + str(floor) + '\t' + str(ceiling) + '\t' + str(meandate) + '\t' + str(maxaccuracy) + '\t' + str(features4max) + '\t' + str(best_regularization_coef) + '\t' + str(i) + '\n'
                f.write(outline)

            os.remove(vocabpath)

    for contrast in ['random', 'randomB']:
        if contrast == 'random':
            othercontrast = 'randomB'
        else:
            othercontrast = 'random'

        for i in range(3):
            for j in range(3):

                r = dict()
                r['testype'] = 'bailey-19cSF'
                r['name1'] = 'bailey_' + contrast + '_' + str(i)
                r['name2'] = '19cSF_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

                r = dict()
                r['testype'] = 'bailey-self'
                r['name1'] = 'bailey_' + contrast + '_' + str(i)
                r['name2'] = 'bailey_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

                r = dict()
                r['testype'] = '19cSF-self'
                r['name1'] = '19cSF_' + contrast + '_' + str(i)
                r['name2'] = '19cSF_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

def scarborough_to_19c_fantasy():
    '''
    Trains several models of Dorothy Scarborough's "supernatural fiction" (1917),
    and several models of "fantasy fiction" in the same period (1800-1922),
    as defined by recent librarians. Compares these models using the method of
    mutual recognition to assess the similarity of the categories.

    Notice that this version of the function improves on earlier versions by making
    comparisons only between models with disjoint contrast sets. I.e., 'random'
    and 'randomB' are kept distinct here.

    In this run I am excluding juvenile fiction.
    '''

    outmodels = '../results/scarboroughto19c_models.tsv'
    outcomparisons = '../results/scarboroughto19c_comparisons.tsv'
    columns = ['testype', 'name1', 'name2', 'ceiling1', 'floor1', 'ceiling2', 'floor2', 'meandate1', 'meandate2', 'acc1', 'acc2', 'alienacc1', 'alienacc2', 'spearman', 'spear1on2', 'spear2on1', 'loss', 'loss1on2', 'loss2on1']

    if not os.path.isfile(outcomparisons):
        with open(outcomparisons, mode = 'a', encoding = 'utf-8') as f:
            scribe = csv.DictWriter(f, delimiter = '\t', fieldnames = columns)
            scribe.writeheader()

    if not os.path.isfile(outmodels):
        with open(outmodels, mode = 'a', encoding = 'utf-8') as f:
            outline = 'name\tsize\tfloor\tceiling\tmeandate\taccuracy\tfeatures\tregularization\ti\n'
            f.write(outline)

    sourcefolder = '../data/'
    sizecap = 70

    c_range = [.00001, .0001, .001, .01, 0.1, 1, 10, 100]
    featurestart = 1500
    featureend = 6500
    featurestep = 300
    modelparams = 'logistic', 15, featurestart, featureend, featurestep, c_range
    metadatapath = '../metadata/mastermetadata.csv'

    for contrast in ['random', 'randomB']:
        for i in range(3):

            name = 'scarborough_' + contrast + '_' + str(i)
            vocabpath = '../lexica/' + name + '.txt'
            tags4positive = {'supernat'}
            tags4negative = {contrast}
            floor = 1800
            ceiling = 1922

            metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist = versatiletrainer2.get_simple_data(sourcefolder, metadatapath, vocabpath, tags4positive, tags4negative, sizecap, excludebelow = floor, excludeabove = ceiling, force_even_distribution = False, negative_strategy = 'closely match', numfeatures = 6500, forbid4positive = {'juv'}, forbid4negative = {'juv'})

            # notice that I am excluding children's lit this time!

            matrix, maxaccuracy, metadata, coefficientuples, features4max, best_regularization_coef = versatiletrainer2.tune_a_model(metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist, tags4positive, tags4negative, modelparams, name, '../modeloutput/' + name + '.csv')

            meandate = int(round(np.sum(metadata.firstpub) / len(metadata.firstpub)))

            with open(outmodels, mode = 'a', encoding = 'utf-8') as f:
                outline = name + '\t' + str(sizecap) + '\t' + str(floor) + '\t' + str(ceiling) + '\t' + str(meandate) + '\t' + str(maxaccuracy) + '\t' + str(features4max) + '\t' + str(best_regularization_coef) + '\t' + str(i) + '\n'
                f.write(outline)

            os.remove(vocabpath)

            name = '19c_fantasy_' + contrast + '_' + str(i)
            vocabpath = '../lexica/' + name + '.txt'
            tags4positive = {'fantasy_oclc', 'fantasy_loc'}
            tags4negative = {contrast}
            floor = 1800
            ceiling = 1922

            metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist = versatiletrainer2.get_simple_data(sourcefolder, metadatapath, vocabpath, tags4positive, tags4negative, sizecap, excludebelow = floor, excludeabove = ceiling, force_even_distribution = False, negative_strategy = 'closely match', numfeatures = 6500, forbid4positive = {'juv'}, forbid4negative = {'juv'})

            # notice, not excluding children's lit

            matrix, maxaccuracy, metadata, coefficientuples, features4max, best_regularization_coef = versatiletrainer2.tune_a_model(metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist, tags4positive, tags4negative, modelparams, name, '../modeloutput/' + name + '.csv')

            meandate = int(round(np.sum(metadata.firstpub) / len(metadata.firstpub)))

            with open(outmodels, mode = 'a', encoding = 'utf-8') as f:
                outline = name + '\t' + str(sizecap) + '\t' + str(floor) + '\t' + str(ceiling) + '\t' + str(meandate) + '\t' + str(maxaccuracy) + '\t' + str(features4max) + '\t' + str(best_regularization_coef) + '\t' + str(i) + '\n'
                f.write(outline)

            os.remove(vocabpath)

    for contrast in ['random', 'randomB']:
        if contrast == 'random':
            othercontrast = 'randomB'
        else:
            othercontrast = 'random'

        for i in range(3):
            for j in range(3):

                r = dict()
                r['testype'] = 'scarborough-19cfantasy'
                r['name1'] = 'scarborough_' + contrast + '_' + str(i)
                r['name2'] = '19c_fantasy_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

                r = dict()
                r['testype'] = 'scarborough-self'
                r['name1'] = 'scarborough_' + contrast + '_' + str(i)
                r['name2'] = 'scarborough_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

                r = dict()
                r['testype'] = '19cfantasy-self'
                r['name1'] = '19c_fantasy_' + contrast + '_' + str(i)
                r['name2'] = '19c_fantasy_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

def scarborough_to_bailey():
    '''
    This function assumes that you've already trained the models of scarborough
    and bailey using different random contrast sets, and now just need to compare them.
    '''

    outcomparisons = '../results/scarborough2bailey_comparisons.tsv'
    columns = ['testype', 'name1', 'name2', 'ceiling1', 'floor1', 'ceiling2', 'floor2', 'meandate1', 'meandate2', 'acc1', 'acc2', 'alienacc1', 'alienacc2', 'spearman', 'spear1on2', 'spear2on1', 'loss', 'loss1on2', 'loss2on1']

    if not os.path.isfile(outcomparisons):
        with open(outcomparisons, mode = 'a', encoding = 'utf-8') as f:
            scribe = csv.DictWriter(f, delimiter = '\t', fieldnames = columns)
            scribe.writeheader()

    for contrast in ['random', 'randomB']:
        if contrast == 'random':
            othercontrast = 'randomB'
        else:
            othercontrast = 'random'

        for i in range(3):
            for j in range(3):

                r = dict()
                r['testype'] = 'scarborough-bailey'
                r['name1'] = 'scarborough_' + contrast + '_' + str(i)
                r['name2'] = 'bailey_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

                r = dict()
                r['testype'] = 'scarborough-self'
                r['name1'] = 'scarborough_' + contrast + '_' + str(i)
                r['name2'] = 'scarborough_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

                r = dict()
                r['testype'] = 'bailey-self'
                r['name1'] = 'bailey_' + contrast + '_' + str(i)
                r['name2'] = 'bailey_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

def sf19ctofantasy19c():
    '''
    This function assumes that you've already trained the models of scarborough
    and bailey using different random contrast sets, and now just need to compare them.
    '''

    outcomparisons = '../results/sf19ctofantasy19c_comparisons.tsv'
    columns = ['testype', 'name1', 'name2', 'ceiling1', 'floor1', 'ceiling2', 'floor2', 'meandate1', 'meandate2', 'acc1', 'acc2', 'alienacc1', 'alienacc2', 'spearman', 'spear1on2', 'spear2on1', 'loss', 'loss1on2', 'loss2on1']

    if not os.path.isfile(outcomparisons):
        with open(outcomparisons, mode = 'a', encoding = 'utf-8') as f:
            scribe = csv.DictWriter(f, delimiter = '\t', fieldnames = columns)
            scribe.writeheader()

    for contrast in ['random', 'randomB']:
        if contrast == 'random':
            othercontrast = 'randomB'
        else:
            othercontrast = 'random'

        for i in range(3):
            for j in range(3):

                r = dict()
                r['testype'] = 'sf-fantasy'
                r['name1'] = '19cSF_' + contrast + '_' + str(i)
                r['name2'] = '19c_fantasy_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

                r = dict()
                r['testype'] = 'fantasy-self'
                r['name1'] = '19c_fantasy_' + contrast + '_' + str(i)
                r['name2'] = '19c_fantasy_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

                r = dict()
                r['testype'] = 'sf-self'
                r['name1'] = '19cSF_' + contrast + '_' + str(i)
                r['name2'] = '19cSF_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

def baileytofantasy19c():
    '''
    This function assumes that you've already trained the models of scarborough
    and bailey using different random contrast sets, and now just need to compare them.
    '''

    outcomparisons = '../results/baileytofantasy19c_comparisons.tsv'
    columns = ['testype', 'name1', 'name2', 'ceiling1', 'floor1', 'ceiling2', 'floor2', 'meandate1', 'meandate2', 'acc1', 'acc2', 'alienacc1', 'alienacc2', 'spearman', 'spear1on2', 'spear2on1', 'loss', 'loss1on2', 'loss2on1']

    if not os.path.isfile(outcomparisons):
        with open(outcomparisons, mode = 'a', encoding = 'utf-8') as f:
            scribe = csv.DictWriter(f, delimiter = '\t', fieldnames = columns)
            scribe.writeheader()

    for contrast in ['random', 'randomB']:
        if contrast == 'random':
            othercontrast = 'randomB'
        else:
            othercontrast = 'random'

        for i in range(3):
            for j in range(3):

                r = dict()
                r['testype'] = 'bailey-fantasy'
                r['name1'] = 'bailey_' + contrast + '_' + str(i)
                r['name2'] = '19c_fantasy_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

                r = dict()
                r['testype'] = 'fantasy-self'
                r['name1'] = '19c_fantasy_' + contrast + '_' + str(i)
                r['name2'] = '19c_fantasy_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

                r = dict()
                r['testype'] = 'bailey-self'
                r['name1'] = 'bailey_' + contrast + '_' + str(i)
                r['name2'] = 'bailey_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

def scarborough_to_19cSF():
    '''
    This function assumes that you've already trained the models of scarborough
    and bailey using different random contrast sets, and now just need to compare them.
    '''

    outcomparisons = '../results/scarborough2sf_comparisons.tsv'
    columns = ['testype', 'name1', 'name2', 'ceiling1', 'floor1', 'ceiling2', 'floor2', 'meandate1', 'meandate2', 'acc1', 'acc2', 'alienacc1', 'alienacc2', 'spearman', 'spear1on2', 'spear2on1', 'loss', 'loss1on2', 'loss2on1']

    if not os.path.isfile(outcomparisons):
        with open(outcomparisons, mode = 'a', encoding = 'utf-8') as f:
            scribe = csv.DictWriter(f, delimiter = '\t', fieldnames = columns)
            scribe.writeheader()

    for contrast in ['random', 'randomB']:
        if contrast == 'random':
            othercontrast = 'randomB'
        else:
            othercontrast = 'random'

        for i in range(3):
            for j in range(3):

                r = dict()
                r['testype'] = 'scarborough-19cSF'
                r['name1'] = 'scarborough_' + contrast + '_' + str(i)
                r['name2'] = '19cSF_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

                r = dict()
                r['testype'] = 'scarborough-self'
                r['name1'] = 'scarborough_' + contrast + '_' + str(i)
                r['name2'] = 'scarborough_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

                r = dict()
                r['testype'] = 'sf-self'
                r['name1'] = '19cSF_' + contrast + '_' + str(i)
                r['name2'] = '19cSF_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

def just_maximize_SF():

    sourcefolder = '../data/'
    sizecap = 700

    c_range = [.00001, .0001, .001, .005, .01, 0.1, 1, 10, 100]
    featurestart = 1500
    featureend = 7000
    featurestep = 200
    modelparams = 'logistic', 20, featurestart, featureend, featurestep, c_range
    metadatapath = '../metadata/mastermetadata.csv'

    name = 'maxaccuracySF'
    vocabpath = '../lexica/' + name + '.txt'
    tags4positive = {'sf_loc', 'sf_oclc'}
    tags4negative = {'random'}
    floor = 1800
    ceiling = 2011

    metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist = versatiletrainer2.get_simple_data(sourcefolder, metadatapath, vocabpath, tags4positive, tags4negative, sizecap, excludebelow = floor, excludeabove = ceiling, forbid4positive = {'juv'}, forbid4negative = {'juv'}, force_even_distribution = False, negative_strategy = 'closely match', numfeatures = 7000)

    matrix, maxaccuracy, metadata, coefficientuples, features4max, best_regularization_coef = versatiletrainer2.tune_a_model(metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist, tags4positive, tags4negative, modelparams, name, '../modeloutput/' + name + '.csv')

def just_maximize_fantasy():

    sourcefolder = '../data/'
    sizecap = 700

    c_range = [.00001, .0001, .001, .01, 0.1, 1, 10, 100]
    featurestart = 1500
    featureend = 7500
    featurestep = 300
    modelparams = 'logistic', 20, featurestart, featureend, featurestep, c_range
    metadatapath = '../metadata/mastermetadata.csv'

    name = 'maxaccuracy_fantasy'
    vocabpath = '../lexica/' + name + '.txt'
    tags4positive = {'fantasy_loc', 'fantasy_oclc'}
    tags4negative = {'random'}
    floor = 1800
    ceiling = 2011

    metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist = versatiletrainer2.get_simple_data(sourcefolder, metadatapath, vocabpath, tags4positive, tags4negative, sizecap, excludebelow = floor, excludeabove = ceiling, forbid4positive = {'juv'}, forbid4negative = {'juv'}, force_even_distribution = False, negative_strategy = 'closely match', numfeatures = 7500)

    matrix, maxaccuracy, metadata, coefficientuples, features4max, best_regularization_coef = versatiletrainer2.tune_a_model(metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist, tags4positive, tags4negative, modelparams, name, '../modeloutput/' + name + '.csv')

def get_divergence(sampleA, sampleB):
    '''
    This function applies model a to b, and vice versa, and returns
    a couple of measures of divergence: notably lost accuracy and
    z-tranformed spearman correlation.
    '''

    # We start by constructing the paths to the sampleA
    # standard model criteria (.pkl) and
    # model output (.csv) on the examples
    # originally used to train it.

    # We're going to try applying the sampleA standard
    # criteria to another model's output, and vice-
    # versa.

    model1 = '../modeloutput/' + sampleA + '.pkl'
    meta1 = '../modeloutput/' + sampleA + '.csv'

    # Now we construct paths to the test model
    # criteria (.pkl) and output (.csv).

    model2 = '../modeloutput/' + sampleB + '.pkl'
    meta2 = '../modeloutput/' + sampleB + '.csv'

    model1on2 = versatiletrainer2.apply_pickled_model(model1, '../data/', '.tsv', meta2)
    model2on1 = versatiletrainer2.apply_pickled_model(model2, '../data/', '.tsv', meta1)

    spearman1on2 = np.arctanh(stats.spearmanr(model1on2.probability, model1on2.alien_model)[0])
    spearman2on1 = np.arctanh(stats.spearmanr(model2on1.probability, model2on1.alien_model)[0])
    spearman = (spearman1on2 + spearman2on1) / 2

    loss1on2 = accuracy_loss(model1on2)
    loss2on1 = accuracy_loss(model2on1)
    loss = (loss1on2 + loss2on1) / 2

    alienacc2 = accuracy(model1on2, 'alien_model')
    alienacc1 = accuracy(model2on1, 'alien_model')

    acc2 = accuracy(model1on2, 'probability')
    acc1 = accuracy(model2on1, 'probability')

    meandate2 = np.mean(model1on2.std_date)
    meandate1 = np.mean(model2on1.std_date)

    return spearman, loss, spearman1on2, spearman2on1, loss1on2, loss2on1, acc1, acc2, alienacc1, alienacc2, meandate1, meandate2

def scarborough_to_detective():
    outmodels = '../results/scarborough2detective_models.tsv'
    outcomparisons = '../results/scarborough2detective_comparisons.tsv'
    columns = ['testype', 'name1', 'name2', 'ceiling1', 'floor1', 'ceiling2', 'floor2', 'meandate1', 'meandate2', 'acc1', 'acc2', 'alienacc1', 'alienacc2', 'spearman', 'spear1on2', 'spear2on1', 'loss', 'loss1on2', 'loss2on1']

    if not os.path.isfile(outcomparisons):
        with open(outcomparisons, mode = 'a', encoding = 'utf-8') as f:
            scribe = csv.DictWriter(f, delimiter = '\t', fieldnames = columns)
            scribe.writeheader()

    if not os.path.isfile(outmodels):
        with open(outmodels, mode = 'a', encoding = 'utf-8') as f:
            outline = 'name\tsize\tfloor\tceiling\tmeandate\taccuracy\tfeatures\tregularization\ti\n'
            f.write(outline)

    sourcefolder = '../data/'
    sizecap = 70

    c_range = [.00001, .0001, .001, .01, 0.1, 1, 10, 100]
    featurestart = 1500
    featureend = 6500
    featurestep = 300
    modelparams = 'logistic', 15, featurestart, featureend, featurestep, c_range
    metadatapath = '../metadata/mastermetadata.csv'

    for contrast in ['random', 'randomB']:
        for i in range(3):

            name = 'scarborough_' + contrast + '_' + str(i)
            vocabpath = '../lexica/' + name + '.txt'
            tags4positive = {'supernat'}
            tags4negative = {contrast}
            floor = 1800
            ceiling = 1922

            checkpath = '../modeloutput/' + name + '.csv'
            if not os.path.isfile(checkpath):

                metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist = versatiletrainer2.get_simple_data(sourcefolder, metadatapath, vocabpath, tags4positive, tags4negative, sizecap, excludebelow = floor, excludeabove = ceiling, force_even_distribution = False, negative_strategy = 'closely match', numfeatures = 6500, forbid4positive = {'juv'}, forbid4negative = {'juv'})

                # notice that I am excluding children's lit this time!

                matrix, maxaccuracy, metadata, coefficientuples, features4max, best_regularization_coef = versatiletrainer2.tune_a_model(metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist, tags4positive, tags4negative, modelparams, name, '../modeloutput/' + name + '.csv')

                meandate = int(round(np.sum(metadata.firstpub) / len(metadata.firstpub)))

                with open(outmodels, mode = 'a', encoding = 'utf-8') as f:
                    outline = name + '\t' + str(sizecap) + '\t' + str(floor) + '\t' + str(ceiling) + '\t' + str(meandate) + '\t' + str(maxaccuracy) + '\t' + str(features4max) + '\t' + str(best_regularization_coef) + '\t' + str(i) + '\n'
                    f.write(outline)

                os.remove(vocabpath)

            name = 'detective_' + contrast + '_' + str(i)
            vocabpath = '../lexica/' + name + '.txt'
            tags4positive = {'detective'}
            tags4negative = {contrast}
            floor = 1800
            ceiling = 1922

            metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist = versatiletrainer2.get_simple_data(sourcefolder, metadatapath, vocabpath, tags4positive, tags4negative, sizecap, excludebelow = floor, excludeabove = ceiling, force_even_distribution = False, negative_strategy = 'closely match', numfeatures = 6500, forbid4positive = {'juv'}, forbid4negative = {'juv'})

            # notice, not excluding children's lit

            matrix, maxaccuracy, metadata, coefficientuples, features4max, best_regularization_coef = versatiletrainer2.tune_a_model(metadata, masterdata, classvector, classdictionary, orderedIDs, authormatches, vocablist, tags4positive, tags4negative, modelparams, name, '../modeloutput/' + name + '.csv')

            meandate = int(round(np.sum(metadata.firstpub) / len(metadata.firstpub)))

            with open(outmodels, mode = 'a', encoding = 'utf-8') as f:
                outline = name + '\t' + str(sizecap) + '\t' + str(floor) + '\t' + str(ceiling) + '\t' + str(meandate) + '\t' + str(maxaccuracy) + '\t' + str(features4max) + '\t' + str(best_regularization_coef) + '\t' + str(i) + '\n'
                f.write(outline)

            os.remove(vocabpath)

    for contrast in ['random', 'randomB']:
        if contrast == 'random':
            othercontrast = 'randomB'
        else:
            othercontrast = 'random'

        for i in range(3):
            for j in range(3):

                r = dict()
                r['testype'] = 'scarborough-detective'
                r['name1'] = 'scarborough_' + contrast + '_' + str(i)
                r['name2'] = 'detective_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

                r = dict()
                r['testype'] = 'scarborough-self'
                r['name1'] = 'scarborough_' + contrast + '_' + str(i)
                r['name2'] = 'scarborough_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

                r = dict()
                r['testype'] = 'detective-self'
                r['name1'] = 'detective_' + contrast + '_' + str(i)
                r['name2'] = 'detective_' + othercontrast + '_' + str(j)
                r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                write_a_row(r, outcomparisons, columns)

def genrespace():

    outcomparisons = '../results/genrespace.tsv'
    columns = ['testype', 'name1', 'name2', 'meandate1', 'meandate2', 'acc1', 'acc2', 'alienacc1', 'alienacc2', 'spearman', 'spear1on2', 'spear2on1', 'loss', 'loss1on2', 'loss2on1']

    if not os.path.isfile(outcomparisons):
        with open(outcomparisons, mode = 'a', encoding = 'utf-8') as f:
            scribe = csv.DictWriter(f, delimiter = '\t', fieldnames = columns)
            scribe.writeheader()

    periods = ['1800to1899', '1900to1919', '1920to1949', '1950to1969', '1970to1979', '1980to1989', '1990to1999', '2000to2010']

    groups = dict()
    keys = []

    for genre in ['sfnojuv', 'fantasynojuv']:
        for p in periods:
            group = []
            for i in range(5):
                name = genre + p + 'v' + str(i)

                if not os.path.isfile('../modeloutput/' + name + '.pkl'):
                    print('error, missing ' + name)
                    sys.exit(0)
                else:
                    group.append(name)

            key = genre + p
            groups[key] = group
            keys.append(key)


    for genre in ['scarborough_random', 'bailey_random']:
        group = []
        for backdrop in ['_', '_B']:
            for i in range(3):
                if not os.path.isfile('../modeloutput/' + name + '.pkl'):
                    print('error, missing ' + name)
                    sys.exit(0)
                else:
                    group.append(name)

        key = genre
        groups[key] = group
        keys.append(key)

    for k1 in keys:
        for k2 in keys:

            for name1 in groups[k1]:
                for name2 in groups[k2]:

                    r = dict()
                    if k1 == k2:
                        r['testype'] = k1 + '|self'
                    else:
                        r['testype'] = k1 + '|' + k2

                    r['name1'] = name1
                    r['name2'] = name2

                    r['spearman'], r['loss'], r['spear1on2'], r['spear2on1'], r['loss1on2'], r['loss2on1'], r['acc1'], r['acc2'], r['alienacc1'], r['alienacc2'], r['meandate1'], r['meandate2'] = get_divergence(r['name1'], r['name2'])

                    write_a_row(r, outcomparisons, columns)


## MAIN

command = sys.argv[1]

if command == "scar_19c":
    scarborough_to_19c_fantasy()
elif command == "bailey_19c":
    bailey_to_19cSF()
elif command == "scar_detective":
    scarborough_to_detective()
elif command == "sfsurprise":
    date = int(sys.argv[2])
    get_rcc_surprise(date)
elif command == "fantasysurprise":
    date = int(sys.argv[2])
    get_fantasy_surprise(date)
elif command == 'genrespace':
    genrespace()
elif command == 'scarborough_bailey':
    scarborough_to_bailey()
elif command == '19csf_fantasy':
    sf19ctofantasy19c()
elif command == 'bailey_fantasy':
    baileytofantasy19c()
elif command == 'scarborough_sf':
    scarborough_to_19cSF()


