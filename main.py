import os
import requests
import json
import sqlite3
import sys
from sqlite3 import Error
from bs4 import BeautifulSoup
import time as tm
from itertools import groupby
from datetime import datetime, timedelta, time
import pandas as pd
from urllib.parse import quote
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

import smtplib
from email.message import EmailMessage
from collections import defaultdict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pprint
import re

def get_google_jobs():
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    url = ("https://www.google.com/about/careers/applications/jobs/results/"
           "?category=SOFTWARE_ENGINEERING&jex=ENTRY_LEVEL&target_level=INTERN_AND_APPRENTICE")
    driver.get(url)
    tm.sleep(3)  # Wait for JS to load; increase if needed

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    joblist = []
    # Find all <a> with href containing 'jobs/results/'
    job_links = soup.find_all('a', href=re.compile(r'^jobs/results/'))

    seen_urls = set()  # avoid duplicates

    for link in job_links:
        href = link.get('href')
        if not href or href in seen_urls:
            continue
        seen_urls.add(href)

        # Extract job title from aria-label or link text
        aria_label = link.get('aria-label', '')
        title = aria_label.replace('Learn more about ', '').strip() if aria_label else link.text.strip()

        # Sometimes location is nearby in parent elements; let's try to get it if possible
        location = ''
        parent = link.find_parent()
        if parent:
            loc_tag = parent.find_next(string=re.compile(r'[A-Za-z\s,]+'))  # naive location guess
            if loc_tag:
                location = loc_tag.strip()

        job = {
            'title': title if title else 'No Title',
            'company': 'Google',
            'location': location,
            'date': datetime.today().strftime("%Y-%m-%d"),
            'job_url': f"https://www.google.com/{href}",
            'job_description': '',
            'applied': 0,
            'hidden': 0,
            'interview': 0,
            'rejected': 0
        }
        joblist.append(job)

    print(f"Scraped {len(joblist)} Google job(s)")
    pprint.pprint(joblist)
    return joblist

def get_nvidia_intern_jobs():
    joblist = []
    # Workday jobs API endpoint for NVIDIA (example)
    api_url = "https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/jobs"

    # Typical POST body payload for Workday job search, with filters for internships
    payload = {
        "appliedFacets": {
            "workExperienceLevel": ["Internship"],
            "jobCategory": [],   # you can add categories here if needed
        },
        "limit": 50,
        "offset": 0,
        "searchText": "",  # empty for all jobs
        "includeJobDescriptions": True
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        # The jobs list may be under 'jobPostings' or similar key; inspect actual response
        jobs = data.get('jobPostings', [])
        for job in jobs:
            # Parse job fields; keys depend on actual API response structure
            title = job.get('title', 'No Title')
            location = job.get('locations', [{}])[0].get('name', '')
            job_id = job.get('id', '')
            url = f"https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/jobs/{job_id}"

            joblist.append({
                'title': title,
                'company': 'NVIDIA',
                'location': location,
                'date': datetime.today().strftime("%Y-%m-%d"),
                'job_url': url,
                'job_description': job.get('description', ''),
                'applied': 0,
                'hidden': 0,
                'interview': 0,
                'rejected': 0,
            })

        print(f"Scraped {len(joblist)} NVIDIA intern job(s)")
        return joblist

    except Exception as e:
        print("Error fetching NVIDIA jobs:", e)
        return joblist

def load_config(file_name):
    # Load the config file
    with open(file_name) as f:
        return json.load(f)

def get_with_retry(url, config, retries=3, delay=1):
    # Get the URL with retries and delay
    for i in range(retries):
        try:
            if len(config['proxies']) > 0:
                r = requests.get(url, headers=config['headers'], proxies=config['proxies'], timeout=5)
            else:
                r = requests.get(url, headers=config['headers'], timeout=5)
            return BeautifulSoup(r.content, 'html.parser')
        except requests.exceptions.Timeout:
            print(f"Timeout occurred for URL: {url}, retrying in {delay}s...")
            tm.sleep(delay)
        except Exception as e:
            print(f"An error occurred while retrieving the URL: {url}, error: {e}")
    return None

def transform(soup):
    # Parsing the job card info (title, company, location, date, job_url) from the beautiful soup object
    joblist = []
    try:
        divs = soup.find_all('div', class_='base-search-card__info')
    except:
        print("Empty page, no jobs found")
        return joblist
    for item in divs:
        title = item.find('h3').text.strip()
        company = item.find('a', class_='hidden-nested-link')
        location = item.find('span', class_='job-search-card__location')
        parent_div = item.parent
        entity_urn = parent_div['data-entity-urn']
        job_posting_id = entity_urn.split(':')[-1]
        job_url = 'https://www.linkedin.com/jobs/view/'+job_posting_id+'/'

        date_tag_new = item.find('time', class_ = 'job-search-card__listdate--new')
        date_tag = item.find('time', class_='job-search-card__listdate')
        date = date_tag['datetime'] if date_tag else date_tag_new['datetime'] if date_tag_new else ''
        job_description = ''
        job = {
            'title': title,
            'company': company.text.strip().replace('\n', ' ') if company else '',
            'location': location.text.strip() if location else '',
            'date': date,
            'job_url': job_url,
            'job_description': job_description,
            'applied': 0,
            'hidden': 0,
            'interview': 0,
            'rejected': 0
        }
        joblist.append(job)
    return joblist

def transform_job(soup):
    div = soup.find('div', class_='description__text description__text--rich')
    if div:
        # Remove unwanted elements
        for element in div.find_all(['span', 'a']):
            element.decompose()

        # Replace bullet points
        for ul in div.find_all('ul'):
            for li in ul.find_all('li'):
                li.insert(0, '-')

        text = div.get_text(separator='\n').strip()
        text = text.replace('\n\n', '')
        text = text.replace('::marker', '-')
        text = text.replace('-\n', '- ')
        text = text.replace('Show less', '').replace('Show more', '')
        return text
    else:
        return "Could not find Job Description"

def safe_detect(text):
    try:
        return detect(text)
    except LangDetectException:
        return 'en'

def remove_irrelevant_jobs(joblist, config):
    #Filter out jobs based on description, title, and language. Set up in config.json.
    new_joblist = [job for job in joblist if not any(word.lower() in job['job_description'].lower() for word in config['desc_words'])]   
    new_joblist = [job for job in new_joblist if not any(word.lower() in job['title'].lower() for word in config['title_exclude'])] if len(config['title_exclude']) > 0 else new_joblist
    new_joblist = [job for job in new_joblist if any(word.lower() in job['title'].lower() for word in config['title_include'])] if len(config['title_include']) > 0 else new_joblist
    new_joblist = [job for job in new_joblist if safe_detect(job['job_description']) in config['languages']] if len(config['languages']) > 0 else new_joblist
    new_joblist = [job for job in new_joblist if not any(word.lower() in job['company'].lower() for word in config['company_exclude'])] if len(config['company_exclude']) > 0 else new_joblist

    return new_joblist

def remove_duplicates(joblist, config):
    # Remove duplicate jobs in the joblist. Duplicate is defined as having the same title and company.
    joblist.sort(key=lambda x: (x['title'], x['company']))
    joblist = [next(g) for k, g in groupby(joblist, key=lambda x: (x['title'], x['company']))]
    return joblist

def convert_date_format(date_string):
    """
    Converts a date string to a date object. 
    
    Args:
        date_string (str): The date in string format.

    Returns:
        date: The converted date object, or None if conversion failed.
    """
    date_format = "%Y-%m-%d"
    try:
        job_date = datetime.strptime(date_string, date_format).date()
        return job_date
    except ValueError:
        print(f"Error: The date for job {date_string} - is not in the correct format.")
        return None

def create_connection(config):
    # Create a database connection to a SQLite database
    conn = None
    path = config['db_path']
    try:
        conn = sqlite3.connect(path) # creates a SQL database in the 'data' directory
        #print(sqlite3.version)
    except Error as e:
        print(e)

    return conn

def create_table(conn, df, table_name):
    ''''
    # Create a new table with the data from the dataframe
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    print (f"Created the {table_name} table and added {len(df)} records")
    '''
    # Create a new table with the data from the DataFrame
    # Prepare data types mapping from pandas to SQLite
    type_mapping = {
        'int64': 'INTEGER',
        'float64': 'REAL',
        'datetime64[ns]': 'TIMESTAMP',
        'object': 'TEXT',
        'bool': 'INTEGER'
    }
    
    # Prepare a string with column names and their types
    columns_with_types = ', '.join(
        f'"{column}" {type_mapping[str(df.dtypes[column])]}'
        for column in df.columns
    )
    
    # Prepare SQL query to create a new table
    create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS "{table_name}" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {columns_with_types}
        );
    """
    
    # Execute SQL query
    cursor = conn.cursor()
    cursor.execute(create_table_sql)
    
    # Commit the transaction
    conn.commit()

    # Insert DataFrame records one by one
    insert_sql = f"""
        INSERT INTO "{table_name}" ({', '.join(f'"{column}"' for column in df.columns)})
        VALUES ({', '.join(['?' for _ in df.columns])})
    """
    for record in df.to_dict(orient='records'):
        cursor.execute(insert_sql, list(record.values()))
    
    # Commit the transaction
    conn.commit()

    print(f"Created the {table_name} table and added {len(df)} records")

def update_table(conn, df, table_name):
    # Update the existing table with new records.
    df_existing = pd.read_sql(f'select * from {table_name}', conn)

    # Create a dataframe with unique records in df that are not in df_existing
    df_new_records = pd.concat([df, df_existing, df_existing]).drop_duplicates(['title', 'company', 'date'], keep=False)

    # If there are new records, append them to the existing table
    if len(df_new_records) > 0:
        df_new_records.to_sql(table_name, conn, if_exists='append', index=False)
        print (f"Added {len(df_new_records)} new records to the {table_name} table")
    else:
        print (f"No new records to add to the {table_name} table")

def table_exists(conn, table_name):
    # Check if the table already exists in the database
    cur = conn.cursor()
    cur.execute(f"SELECT count(name) FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    if cur.fetchone()[0]==1 :
        return True
    return False

def job_exists(df, job):
    # Check if the job already exists in the dataframe
    if df.empty:
        return False
    #return ((df['title'] == job['title']) & (df['company'] == job['company']) & (df['date'] == job['date'])).any()
    #The job exists if there's already a job in the database that has the same URL
    return ((df['job_url'] == job['job_url']).any() | (((df['title'] == job['title']) & (df['company'] == job['company']) & (df['date'] == job['date'])).any()))

def get_jobcards(config):
    #Function to get the job cards from the search results page
    all_jobs = []
    for k in range(0, config['rounds']):
        for query in config['search_queries']:
            keywords = quote(query['keywords']) # URL encode the keywords
            location = quote(query['location']) # URL encode the location
            for i in range (0, config['pages_to_scrape']):
                url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keywords}&location={location}&f_TPR=&f_WT={query['f_WT']}&geoId=&f_TPR={config['timespan']}&start={25*i}"
                soup = get_with_retry(url, config)
                jobs = transform(soup)
                all_jobs = all_jobs + jobs
                print("Finished scraping page: ", url)
    print ("Total job cards scraped: ", len(all_jobs))
    all_jobs = remove_duplicates(all_jobs, config)
    print ("Total job cards after removing duplicates: ", len(all_jobs))
    all_jobs = remove_irrelevant_jobs(all_jobs, config)
    print ("Total job cards after removing irrelevant jobs: ", len(all_jobs))
    return all_jobs

def find_new_jobs(all_jobs, conn, config):
    # From all_jobs, find the jobs that are not already in the database. Function checks both the jobs and filtered_jobs tables.
    jobs_tablename = config['jobs_tablename']
    filtered_jobs_tablename = config['filtered_jobs_tablename']
    jobs_db = pd.DataFrame()
    filtered_jobs_db = pd.DataFrame()    
    if conn is not None:
        if table_exists(conn, jobs_tablename):
            query = f"SELECT * FROM {jobs_tablename}"
            jobs_db = pd.read_sql_query(query, conn)
        if table_exists(conn, filtered_jobs_tablename):
            query = f"SELECT * FROM {filtered_jobs_tablename}"
            filtered_jobs_db = pd.read_sql_query(query, conn)

    new_joblist = [job for job in all_jobs if not job_exists(jobs_db, job) and not job_exists(filtered_jobs_db, job)]
    return new_joblist

def send_mail(joblist):
    if not joblist:
        plain_text = "No new jobs found today."
        html_content = "<p>No new jobs found today.</p>"
    else:
        groups = defaultdict(list)
        for job in joblist:
            domain = ''
            if 'linkedin.com' in job['job_url']:
                domain = 'LinkedIn'
            elif 'google.com' in job['job_url']:
                domain = 'Google Careers'
            elif 'apple.com' in job['job_url']:
                domain = 'Apple Careers'
            elif 'nvidia.com' in job['job_url'] or 'nvidia.wd5.myworkdayjobs.com' in job['job_url']:
                domain = 'NVIDIA Careers'
            else:
                domain = job.get('company', 'Other')
            groups[domain].append(job)

        plain_text = f"{sum(len(jobs) for jobs in groups.values())} new job(s) found:\n\n"
        html_content = f"<h2>{sum(len(jobs) for jobs in groups.values())} New Job(s) Found</h2>"

        for source, jobs in groups.items():
            # Sort the jobs by date (newest first)
            jobs.sort(key=lambda x: x['date'], reverse=True)

            plain_text += f"== {source} ({len(jobs)} job(s)) ==\n"
            html_content += f"<h3>{source} ({len(jobs)} job{'s' if len(jobs) > 1 else ''})</h3><ul>"

            for i, job in enumerate(jobs, 1):
                plain_text += (
                    f"{i}. {job['title']} at {job['company']}\n"
                    f"   Location: {job['location']}\n"
                    f"   Date: {job['date']}\n"
                    f"   Link: {job['job_url']}\n\n"
                )
                html_content += (
                    f"<li><strong>{job['title']}</strong> at {job['company']}<br>"
                    f"<em>{job['location']} – {job['date']}</em><br>"
                    f"<a href='{job['job_url']}'>View Job</a></li><br>"
                )

            html_content += "</ul>"

    # Create email
    msg = EmailMessage()
    msg['Subject'] = f"Job Scraper – {len(joblist)} New Jobs"
    fromMail = os.getenv("GMAIL_EMAIL")
    toMail = os.getenv("RECIPIENT_EMAIL")
    msg['From'] = fromMail
    msg['To'] = toMail

    msg.set_content(plain_text)  # fallback for non-HTML clients
    msg.add_alternative(f"""\
    <html>
        <body>
            {html_content}
        </body>
    </html>
    """, subtype='html')

    with smtplib.SMTP(host="smtp.gmail.com", port="587") as smtp:  # 設定SMTP伺服器
        try:
            smtp.ehlo()  # 驗證SMTP伺服器
            smtp.starttls()  # 建立加密傳輸

            email = os.getenv("GMAIL_EMAIL")

            password = os.getenv("GMAIL_PASSWORD")

            if not password or not email:
                raise ValueError("GMAIL_PASSWORD env variable not set")

            smtp.login(email, password)  # 登入寄件者gmail
            smtp.send_message(msg)  # 寄送郵件
            print("Complete send mail!")
        except Exception as e:
            print("Error message: ", e)

def main(config_file):
    start_time = tm.perf_counter()
    job_list = []

    config = load_config(config_file)
    jobs_tablename = config['jobs_tablename'] # name of the table to store the "approved" jobs
    filtered_jobs_tablename = config['filtered_jobs_tablename'] # name of the table to store the jobs that have been filtered out based on description keywords (so that in future they are not scraped again)
    #Scrape search results page and get job cards. This step might take a while based on the number of pages and search queries.
    all_jobs = get_jobcards(config)

    google_jobs = get_google_jobs()
    all_jobs += google_jobs

    conn = create_connection(config)
    #filtering out jobs that are already in the database
    all_jobs = find_new_jobs(all_jobs, conn, config)
    print ("Total new jobs found after comparing to the database: ", len(all_jobs))
    send_mail(all_jobs)

    if len(all_jobs) > 0:

        for job in all_jobs:
            job_date = convert_date_format(job['date'])
            job_date = datetime.combine(job_date, time())
            #if job is older than a week, skip it
            if job_date < datetime.now() - timedelta(days=config['days_to_scrape']):
                continue
            print('Found new job: ', job['title'], 'at ', job['company'], job['job_url'])
            desc_soup = get_with_retry(job['job_url'], config)
            job['job_description'] = transform_job(desc_soup)
            language = safe_detect(job['job_description'])
            if language not in config['languages']:
                print('Job description language not supported: ', language)
                #continue
            job_list.append(job)
        #Final check - removing jobs based on job description keywords words from the config file
        jobs_to_add = remove_irrelevant_jobs(job_list, config)
        print ("Total jobs to add: ", len(jobs_to_add))
        #Create a list for jobs removed based on job description keywords - they will be added to the filtered_jobs table
        filtered_list = [job for job in job_list if job not in jobs_to_add]
        df = pd.DataFrame(jobs_to_add)
        df_filtered = pd.DataFrame(filtered_list)
        df['date_loaded'] = datetime.now()
        df_filtered['date_loaded'] = datetime.now()
        df['date_loaded'] = df['date_loaded'].astype(str)
        df_filtered['date_loaded'] = df_filtered['date_loaded'].astype(str)
        if conn is not None:
            #Update or Create the database table for the job list
            if table_exists(conn, jobs_tablename):
                update_table(conn, df, jobs_tablename)
            else:
                create_table(conn, df, jobs_tablename)
                
            #Update or Create the database table for the filtered out jobs
            if table_exists(conn, filtered_jobs_tablename):
                update_table(conn, df_filtered, filtered_jobs_tablename)
            else:
                create_table(conn, df_filtered, filtered_jobs_tablename)
        else:
            print("Error! cannot create the database connection.")
        
        df.to_csv('linkedin_jobs.csv', index=False, encoding='utf-8')
        df_filtered.to_csv('linkedin_jobs_filtered.csv', index=False, encoding='utf-8')
    else:
        print("No jobs found")
    
    end_time = tm.perf_counter()
    print(f"Scraping finished in {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_dir, "config.json")
    main(config_file)
