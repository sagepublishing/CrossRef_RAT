# Rejected article tracker

This simple program will take a spreadsheet of ScholarOne submission data as input and return a spreadsheet of published articles with similar titles and author-names.

## How it works

The process for obtaining this data is very simple and uses a utility made available by CrossRef.

- To search for an article by title, we simply add the title to the end of this:
?query.title=
- And add the author first name and last name to this
&query.author=

- And then add those to this:
https://api.crossref.org/works
- The result is a url like this. Here, we are looking for a paper called ‘The origin of chemical elements’ by Ralph Alpher et al.
https://api.crossref.org/works?query.title=the%20origin%20of%20chemical%20elements&query.author=r+alpher

Clicking on the above link shows that CrossRef was able to find the article despite not having a unique identifier (such as a DOI).  CrossRef remains good at this even when there are minor changes in the title of the work.

With this in mind, we can use CrossRef to find rejected articles.  It's not perfect:
- sometimes authors make significant changes to the titles of articles and sometimes author lists of papers change before publication.  So it won't always find a rejected article which has changed.
- The utility will also occasionally mis-identify articles with similar titles.
However, this is a simple, effective, and cheap method of tracking rejected articles and it should give you some insights into your journal's competitive position.

The data CrossRef returns is in a format (called JSON) which can be hard to read for humans, so this program will take the results from CrossRef and convert them into an excel spreadsheet.  

There are some obvious adaptations that users may wish to make. Some users may prefer to adapt the code to feed a database instead of working with spreadsheets.  Users who do not use ScholarOne may also wish to adapt the code to work with data from their submission system of choice.

## Setup

You will need the following pieces of software:
-	The latest Python 3 version of Anaconda from continuum.io
-	Once you have this, you will need to open a terminal and install a package called ‘fuzzywuzzy’
o	> pip install fuzzywuzzy
-	You can configure the script in ‘config.py’.  The various options are explained in comments in that script.
-	There are also a few configurations changes that you can make in the script
o	‘allowed_cols’ in ‘tools.py’ will let you change which columns go into the script.  If you want to carry more columns from your input spreadsheet through to the output spreadsheet, you can add those columns to this list.
o	‘rows’ in ‘payload’ sets the number of rows returned in the CrossRef search (100 is the maximum allowed by CrossRef without paging).  In order to generate the output, the script must iterate through each row of results looking for titles that match the query title.  The row where each result is found is stored in the ‘rank’ column of the output.  It may speed up the script to set ‘rows’ to a lower value if you find that good results tend to have ‘rank’ below a certain value.
o	Currently, the search only looks for articles that were not accepted.  This is so that we can find instances where authors failed to resubmit a revised MS.  However, it appears to lead to a lot of false-positives where articles that were accepted but not marked as such.  If you would prefer a more strict search, go into tools.py and change this line:
	> accs = df[df['Accept or Reject Final Decision'] != 'Accept']['raw_ms_id']
To this:
	> accs = df[df['Accept or Reject Final Decision'] == 'Reject']['raw_ms_id']
o	Another solution to the problem of Accepted articles might simply be to exclude the query journal from the results.


## Usage

From Scholar One under  ‘Peer Review Details Reports’ select ‘Build Your Own Reports’.  The report should have the following columns:
['Journal Name', 'Manuscript Type',	'Manuscript ID',	'Manuscript Title',	'Author Names',
 'Submission Date',	'Decision Date',	'Decision Type', 'Accept or Reject Final Decision']
If you already have a report that includes these columns, it’s ok to include those in the report, but they are not needed and will be ignored by the script.
Important: remember to download your report as Excel 2007 Data Format.
Copy the report to the ‘input’ folder
Check the settings in config.py
Open a terminal and type:
	python run.py
The process here is very slow.  Expect to wait around 3 seconds per input article.  However, you can stop the script (ctrl+c) any time and restart where you left-off (as long as you don’t delete anything in the ‘data’ folder - which stores your progress).  
If you simply want to update the existing output with additional data, you can just add another file to ‘input’ and run again.  However, if you want to run the code again with a different dataset, it may be wise to delete all of the files in the ‘data’ folder.

## Data columns

-	ms_id	should match the ‘Manuscript ID’ column
-	match_doi DOI of a ‘match’ article (a ‘match’ being an article with a similar title to the rejected article)
-	match_type Article type of the match
-	match_title Title of the match (compare this with ‘Manuscript Title’ column to assess the quality of the match.
-	match_authors	should match ‘Author Names’
-	publisher the publisher of the match article
-	match_journal	the journal which accepted the match article
-	match_pub_date the ‘issued’ date from CrossRef.  This should be the date of publication.  Unfortunately, it sometimes is just a year, or a year and month rather than an actual date.
-	earliest_date CrossRef records various dates for each entry, such as the date that the article was indexed with CrossRef, the date of creation of the database entry, publication date, epub date etc.  This column shows the earliest of those dates and is usually close to the publication date.  In cases where the publication date is unclear or not recorded, this date is likely to be better.  
-	n_days number of days between rejection from your journal and publication elsewhere.
-	t_sim	textual similarity.  This seems to be a good measure for how good a match there is between the title of the rejected article and a match article.
-	cr_score CrossRef’s own measure for the quality of a match.  This seems to also take into account the authors’ names and possibly other variables too.  I’m not sure how it works, but it may be helpful.
-	cr_cites	 The number of citations recorded by CrossRef for the match article.  (Better citation counts are available!)
