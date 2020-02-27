# coding: utf-8

# ### Desired output
#
# || S1_id | S1_Title | S1_abstract | S1_Authors | S1_sub_date | S1_rej_date | S1_journal | match_DOI | match_title | match_authors | match_publisher | match_journal | match_pub_date | earliest_cr_date | title_similarity | CR_score | CR_cites | days_since_rej ||
#

import os
import pandas as pd
from fuzzywuzzy import fuzz
import json
import csv
from datetime import datetime as dt


from tools import get_output, search_cr, pre_process, build_input
import config as c

dates = c.dates
myemail = c.myemail
threshold = c.threshold

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

# create file with title row
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

output_batch= []
i=0
print()
print(dt.now())
print('Starting search of CrossRef. This may take some time...')
print()
for index, row in df.iterrows():
    ms_id = row['Manuscript ID']
    if ms_id not in successes:
        try:
            authors = row['Authors']

            title = row['Manuscript Title']
            pubdate_filter = 'from-created-date:{}'.format(row['text_sub_date'])
            rj = search_cr(title, authors, pubdate_filter, myemail)

            rank = 0
            for item in rj:
                rank += 1
                match_title = item['title'][0]
#                 print(match_title)

                t_sim = fuzz.ratio(title,match_title)
#                 print(t_sim)
                if t_sim < threshold:
                    continue
                else:
                    csv_row = get_output(ms_id, item, authors, t_sim, rank)
                    if csv_row[10]==False: # drop all results without at least one matching author name.
                        pass
#                    print(csv_row)
                    else:
                        output_batch.append(csv_row)

            successes.append(ms_id)

        except Exception as e:
            print("Fail. Couldn't find:", ms_id)
            print(row['Manuscript Title'])
            print(e)
            failures.append(ms_id)
    else:
        print('Skipping',ms_id,'as already indexed')
        pass
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
                writer.writerows(output_batch)
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
# df2['earliest_date'] = pd.to_datetime(df2['earliest_date'], unit='ms') # convert unix timestamps in df2 to proper datetimes
df = df1.merge(right=df2, how='left', left_on='Manuscript ID', right_on='ms_id')
df['n_days'] = df['earliest_date'] - df['Decision Date']

# add journal acronym from S1 ms_id
# (potentially useful for inputs with multiple journals)
df['Jnl_acro'] = df['Manuscript ID'].map(lambda x: x[:x.find('-')])

# save output
df.to_excel('output/output.xlsx')
print("Process complete! See 'output.xlsx' in output folder.")
