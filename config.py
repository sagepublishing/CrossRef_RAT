# -*- coding: utf-8 -*-
"""
Created on Mon May 14 16:52:20 2018

@author: ADay
"""



# enter your email address here
# This program uses the CrossRef API extensively
# adding your email address lets them know who is using it and
# allows them to contact you if there are any problems.
myemail = ""


# set a threshold for Levenshtein distance between titles
# CrossRef will return all results remotely similar to the title of each
# rejected article. Generally, I find it's unlikely to have a good result
# if the Levenshtein distance is below 70
threshold = 70

# what submission date-range do you want to consider?
# narrow your search here.
# remember to put dates in the format YYYY-MM-DD with the start of the date range first
dates = ['2007-01-01','2018-12-31']
