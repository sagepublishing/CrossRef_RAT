# -*- coding: utf-8 -*-
"""
Created on Mon May 14 16:50:33 2018

@author: ADay
"""

import os
import pandas as pd
import numpy as np
#from fuzzywuzzy import fuzz
#import json
import requests
#import csv



def get_earliest_date(item):
    tags = ['issued','created','indexed','deposited']
    stamps = []
    for tag in tags:
        try:
            stamps.append(int(item[tag]['timestamp']))
        except:
            pass
    try:
        t_stamp = min(stamps)
    except:
        t_stamp = np.nan
    return t_stamp


def json_authors_to_list(authors):
    match_authors = []
    for author in authors:
        try:
            given = author['given']
        except:
            given = ''
        try:
            family = author['family']
        except:
            family = ''
        match_authors.append(given+'+'+family)
    return match_authors


def strip_newlines(s):
	return s.replace('\n', ' ').replace('\r', '')


def get_output(ms_id,item, authors, t_sim, rank):
    match_title = strip_newlines(item['title'][0])
    score = item['score']
    match_doi = item['DOI']

    # build authors list
    authors2 = item['author']
    match_authors = json_authors_to_list(authors2)

    # check author name matches here.  Do we have a first initial and surname in common with the articles CR has found?
    names1 = [(name[0],name[name.rfind('+')+1:]) for name in authors.split(', ')]
    names2 = [(name[0],name[name.rfind('+')+1:]) for name in match_authors]
    match_one = any(name in names2 for name in names1)
    match_all = all(name in names2 for name in names1)

    publisher =  item['publisher']

    try:
        match_type = strip_newlines(item['type'])
    except:
        match_type = ''

    try:
        match_journal  = strip_newlines(item['container-title'][0])
    except:
        match_journal = ''

    try:
        match_pub_date = str(item['issued']['date-parts'][0])
    except:
        match_pub_date=''

    earliest_date = get_earliest_date(item)

    cr_score = score
    cr_cites = item['is-referenced-by-count']
    return [ms_id,
            match_doi,
            match_type,
           match_title,
           match_authors,
           publisher,
           match_journal,
           match_pub_date,
           earliest_date,
            t_sim,
            match_one,
            match_all,
           cr_score,
           cr_cites,
           rank]

def search_cr(title, authors, pubdate_filter, myemail):
    """
    Searches CrossRef for matching titles.
    Requires: requests, json
    """
    authors = authors.split(', ')
    address = "https://api.crossref.org/works/"
     # search crossref
    payload = { 'filter'       : pubdate_filter,
                'query.title'  : title,
                'query.author' : authors,
                'rows'         : 10} # you might want to change this...

    headers = {
    'User-Agent': "Adam Day's rejected article tracker",
    'mailto': myemail
    }

    r = requests.get(address, params=payload, headers = headers)
    # check response time.  Documentation recommends backing off if response time is too long.
    response_time = r.elapsed.total_seconds()
    # print(response_time, 'seconds for last request')
    # responses are generally <1s.
    # simple rule for sleeping if responses are slow
    if response_time > 2.0:
        print('CrossRef slow to respond. To last request. Sleeping for a few seconds.')
        time.sleep(int(response_time))
        # print('Finished sleeping')
    rj = r.json()['message']['items']
    return rj


def convert_name(names):
    """
    Converts name into a simple form suitable for the CrossRef search
    """
    if ';' in names:
        names = names.split('; ')
    else:
        names = [names]
    out = []
    for name in names:
        name = name.split(', ')
        name = name[::-1]
        name = '+'.join(name)
        out.append(name)
    return ', '.join(out)

def raw(s):
    """
    Coverts ScholarOne MS_ID into its base form (i.e. removes revision number if present)
    """
    if '.R' in s:
        s = s[:s.find('.R')]
    return s

def build_input(dates):
    filepaths = os.listdir('input')

    df = pd.DataFrame({})
    allowed_cols = ['Journal Name', 'Manuscript Type',	'Manuscript ID',	'Manuscript Title',	'Author Names',
                    'Submission Date',	'Decision Date',	'Decision Type', 'Accept or Reject Final Decision']
    for filepath in filepaths:
        # set cols to row 1
        df_ = pd.read_excel(os.path.join('input',filepath))
        df_ = df_[allowed_cols]
        df = pd.concat([df,df_])


    # drop drafts
    df = df[df['Manuscript ID']!='draft']

    # drop nans
    df = df.dropna(subset=['Manuscript Title',	'Author Names'])
	# TODO - also drop titles that are < X chars.  This will help when dealing with drafts

    # create a raw id col (without revision no)
    df['raw_ms_id'] = df['Manuscript ID'].map(lambda x: raw(x))



    # set datetimes
    df['Submission Date'] = pd.to_datetime(df['Submission Date'])
    df['Decision Date'] = pd.to_datetime(df['Decision Date'])

    # limit dates
    df = df[(df['Submission Date'] >= dates[0] ) & (df['Submission Date'] <= dates[1])]
    return df


def pre_process(dates):
    df = build_input(dates)

    # limit to article THAT WERE NOT ACCEPTED (not articles that were rejected! it might be interesting to see if articles sent for revision ended up elsewhere)
    df = df[df['Accept or Reject Final Decision'] != 'Accept']

	# limit to articles that were accepted (for testing purposes)
    # df = df[df['Accept or Reject Final Decision'] == 'Accept']

    # drop duplicates otherwise there can be a row for every revision of each article (assume titles stay constant - could change this to subset = ['Manuscript Title'])
    # keep = last means that we should be looking at the final round of revision.
    df = df.drop_duplicates(subset = ['raw_ms_id'], keep = 'last')

    # add a text version of the submission date (input parameter for CR search)
    df['text_sub_date'] = df['Submission Date'].astype( str ).map( lambda x: str(x)[:10] )

    # convert author names for input to the CR search engine
    df['Authors'] = df['Author Names'].map( lambda x: convert_name(x) )
    return df