# coding: utf-8

# ### Desired output
#
# || S1_id | S1_Title | S1_abstract | S1_Authors | S1_sub_date | S1_rej_date | S1_journal | match_DOI | match_title | match_authors | match_publisher | match_journal | match_pub_date | earliest_cr_date | title_similarity | CR_score | CR_cites | days_since_rej ||
#


## TODO - consider adding multithreading. You can do up to 50rps on the CrossRef API
## EXAMPLE SCRIPT:
# import threading
# import time 
# import requests

# numCall = 20
# # url 
# url = "https://api.crossref.org/works"
# class apiThread (threading.Thread):
#     def __init__(self, name, url):
#         threading.Thread.__init__(self)
#         self.name = name
#     def run(self):
#         t_1 = time.time()
#         email = 'adam.day@sagepub.co.uk'
#         headers = {
#         'User-Agent': 'Adam Day - data analysis',
#         'mailto': email
#         }
#         response = requests.get(url, headers = headers)
#         t_2 = time.time()
#         print ("%s, status_code = %s, time = %s" % (self.name, response.status_code, (t_2-t_1)))

# print ("Initiating test")
# print ("Making %s calls to the API asynchronously" % (numCall))

# threads = []
# for x in range(numCall):
#     threads.append(apiThread("API call %s" % ((x+1)), url))
#     threads[-1].start()

# # wait for all threads to finish                                            
# for t in threads:                                                           
#     t.join()  

# print ("Exiting Main Thread")



import os
import pandas as pd

import json
import csv
import numpy as np
from datetime import datetime as dt

from sklearn.linear_model import LogisticRegression
import pickle
from fuzzywuzzy import fuzz
from tools import *
import config as c

dates = c.dates
myemail = c.myemail
threshold = c.threshold

def request_row(row, successes, successes_set,myemail):
    """
    Takes dict of 'Manuscript ID', 'Manuscript Title' and 'Authors' (;-separated)
    Returns row of 
    """
    ms_id = row['Manuscript ID']
    if ms_id not in successes_set:
        try:
            authors = row['Authors']
            n_auths = len(authors.split('; '))
            title = row['Manuscript Title']
            pubdate_filter = 'from-created-date:{}'.format(row['text_sub_date'])
            rj = search_cr(title, authors, pubdate_filter, myemail)

            rank = 0
            result_dois = []
            result_scores = []
            csv_rows = dict()
            for item in rj:
                rank += 1

                if 'title' in item and type(item['title'])==str:
                    match_title = item['title']
                if 'title' in item and type(item['title'])==list:
                    match_title = item['title']
                t_sim = fuzz.ratio(title,match_title)
                if t_sim < threshold:
                    continue
                else:
                    csv_row = get_output(ms_id, item, authors, t_sim, rank)
                    if csv_row['match_one']==False: # drop all results without at least one matching author name.
                        pass
                    else:
                        doi = item['DOI']
                        csv_rows[doi] = csv_row
                        t_sim = t_sim
                        match_all = csv_row['match_all']
                        cr_score = csv_row['cr_score']
                        rank = csv_row['rank']

                        X = np.array([float(x) for x in [t_sim,match_all,cr_score,rank,n_auths]])
                        clf_scores = clf.predict_proba(np.reshape(X,(1,5)))
                        score = clf_scores[0][1]
                        result_dois.append(doi)
                        result_scores.append(score)
            if len(result_scores)>0:
                max_i = np.argmax(result_scores)
                doi_out = result_dois[max_i]
                score_out = result_scores[max_i]

                # set a threshold for the logistic regression

                if score_out >0.75:
                    # update output if all conditions are met
                    successes.append(ms_id)
                    return csv_rows[doi_out], successes, failures


            

        except Exception as e:
            print("Fail. Couldn't find:", ms_id)
            print(row['Manuscript Title'])
            print('Error message', e)
            failures.append(ms_id)
            return None, successes, failures
    else:
        print('Skipping',ms_id,'as already indexed')
        return None, successes, failures
    
# load classifier
with open('lr_model','rb') as f:
    clf = pickle.load(f)

## Requires 3 folders.  Create them if they don't exist
folder_names = ['data','input','output']
for fn in folder_names:
    if not os.path.exists(fn):
        os.mkdir(fn)
    else:
        pass



if myemail == '':
    print('EMAIL ADDRESS REQUIRED')
    print('========================================')
    print("This program will query CrossRef's servers. CrossRef ask that users \n"
          "send their email address when they make a query. This way, if our request \n"
          "causes a problem for them, they can contact us to ask us to terminate the \n"
          "request.  Requests which include email addresses get a faster data-rate in \n"
          "their responses, too. If you do not want to enter your email address every \n"
          "time you use this software, open config.py and set myemail = 'your email \n"
          "address in quotes'." )
    myemail = input('Please enter email address :')


df = pre_process(dates)


# Load lists of successful searches and failure searches. 
# If we have interrupted this search in the past, we can skip these 
successes_p = r'data/successes.json'

if os.path.exists(successes_p):
    with open(successes_p, 'r') as f:
        successes = json.loads(f.read())
else:
    successes = []
    with open(successes_p,'w') as f:
        json.dump(successes,f)

failures_p = r'data/failures.json'

if os.path.exists(failures_p):
    with open(failures_p, 'r') as f:
        failures = json.loads(f.read())
else:
    failures = []
    with open(failures_p,'w') as f:
        json.dump(failures,f)

# create file with title row if it doesn't exist
if os.path.isfile('data/search_output.csv'):
    pass
else:
    with open('data/search_output.csv','w',encoding = 'utf-8') as f1: # ,newline='')
        writer=csv.writer(
                          f1,
                          delimiter = '|',
                          lineterminator = '\r',
                          quotechar = '"'
                            )
        headers = ['ms_id','match_doi', 'match_type', 'match_title', 'match_authors','publisher',
               'match_journal','match_pub_date', 'earliest_date', 't_sim', 'match_one','match_all','cr_score', 'cr_cites','rank']
        writer.writerow(headers)

# retrieve CR data and write to file
i=0
print()
print(dt.now())
print('Starting search of CrossRef. This may take some time...')
print()
successes_set = set(successes)
output_batch = []
for index, row in df.iterrows():

    # This should yield a dict if it works, None if not
    output_row, successes, failures = request_row(row, successes, successes_set, myemail)
    if type(output_row)==dict:
        output_batch.append(output_row)

    # periodically write-out the data to file
    i+=1
    if i%100==0 or i >= df.shape[0]:
        print(dt.now())
        print(i,'/',df.shape[0],'iterations complete')
        if output_batch!=[]:
            with open('data/search_output.csv', 'a', encoding = 'utf-8')  as f1: #,newline='')
                writer=csv.writer(
                                  f1,
                                  delimiter = '|',
                                  lineterminator = '\r',
                                  quotechar = '"'
                                 )
                writer.writerows([[output_row[x] for x in output_row] for output_row in output_batch])
            output_batch = []
        with open(failures_p,'w') as f:
            json.dump(failures,f)
        with open(successes_p,'w') as f:
            json.dump(successes,f)
        print('Written progress to file')
        print('(If you need to pause, hit ctrl+c now that the write process is complete.')
        print('You can restart from where you left off at any time)')
        print()



df1 = build_input(dates)
df1 = df1.drop_duplicates(subset = ['raw_ms_id'], keep = 'last')
df2 = pd.read_csv('data/search_output.csv', error_bad_lines=False, sep='|', encoding = 'latin1')

# Note that the following line sometimes raises an error.
# This seems to be due to corruption of the csv data.
# Setting error_bad_lines=False in the above line should get around this,
# but better to avoid writing corrupted data to csv.
df2['earliest_date'] = pd.to_datetime(df2['earliest_date'], unit='ms') # convert unix timestamps in df2 to proper datetimes
df = df1.merge(right=df2, how='left', left_on='Manuscript ID', right_on='ms_id')
df['n_days'] = df['earliest_date'] - df['Decision Date']

# add journal acronym from S1 ms_id
# (potentially useful for inputs with multiple journals)
df['Jnl_acro'] = df['Manuscript ID'].map(lambda x: x[:x.find('-')])

# save output
df.to_excel('output/output.xlsx')
print("Process complete! See 'output.xlsx' in output folder.")
