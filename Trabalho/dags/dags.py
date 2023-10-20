from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import numpy as np
import re


csv_file = '/opt/airflow/dags/complaints.csv'


def total_pages(soup):
    items = soup.find_all('li', {'aria-label': 'pagination item'})
    numbers = []
    for item in items:
        text = item.get_text()
        if text.isdigit():
            numbers.append(int(text))

    return max(numbers)


def crawler_page(page=1):
    url = f"https://www.reclameaqui.com.br/empresa/prefeitura-fortaleza/lista-reclamacoes/?pagina={page}"    
    return crawler(url)


def crawler_details(uri):
    url = f"https://www.reclameaqui.com.br/{uri}"    
    return crawler(url)


def crawler(url):
    headers = {
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36' 
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return BeautifulSoup(response.text, 'lxml')
    
    return None


def extract_urls(soup):
    urls = []
    if soup is not None:        
        links = soup.find_all('a')
        for link in links:
            h4 = link.find('h4')
            if h4 and 'title' in h4.attrs:
                url = link.get('href')
                if url:
                    urls.append(url)

    return urls


def latest_complaints():
    soup = crawler_page(1)
    urls = extract_urls(soup)
    pages = total_pages(soup)
    if pages > 1:
        for page in range(2, pages):
            soup = crawler_page(page)
            urls += extract_urls(soup)

    if os.path.exists(csv_file):        
        df = pd.read_csv(csv_file, sep=';')
        for url in urls:
            row = df.loc[df['uri'] == url]
            if row.empty :
                new_row = {
                    'id': '',
                    'uri': url,
                    'title': '',
                    'description': '',
                    'created_at': '',
                    'city': '',
                    'answered': False,
                    'evaluated': False
                }
                df = df.append(new_row, ignore_index=True)

    else:
        data = []
        for url in urls:
            data.append({
                'id': '',
                'uri': url,
                'title': '',
                'description': '',
                'created_at': '',
                'city': '',
                'answered': False,
                'evaluated': False
            })
        df = pd.DataFrame(data)        


    df.to_csv(csv_file, index=False, sep=';')


def extract_details():
    df = pd.read_csv(csv_file, sep=';')
    for i, row in df.iterrows():
        if np.isnan(row['id']):
            soup = crawler_details(row['uri'])
            if soup is not None:
                id = soup.find('span', {'data-testid': 'complaint-id'})
                if id is not None:
                    match = re.search(r'\d+', id.text)
                    if match:
                        row['id'] = match.group()

                title = soup.find('h1', class_='lzlu7c-3 eisBFu')
                if title is not None:
                    row['title'] = title.text

                description = soup.find('p', {'data-testid': 'complaint-description'})
                if description is not None:
                    row['description'] = description.text

                city = soup.find('span', {'data-testid': 'complaint-location'})
                if city is not None:
                    row['city'] = city.text

                created = soup.find('span', {'data-testid': 'complaint-creation-date'})
                if created is not None:
                    row['created_at'] = created.text

                answered = soup.find('span', class_='sc-1a60wwz-1 kwzooO')
                row['answered'] = False
                if answered is not None:
                    row['answered'] = False if "não" in soup.find('span', class_='sc-1a60wwz-1 kwzooO').text.lower() else True

                df.at[i] = row

    df.to_csv(csv_file, index=False, sep=';')
    

default_args = {
    'owner': 'Antonie_Lima',
    'depends_on_past': False,
    'start_date': datetime(2023, 10, 11),
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

# Defina a DAG
dag = DAG(
    'web_scraping',
    default_args=default_args,
    description='Realizar coleta do reclame aqui',
    schedule_interval=timedelta(days=1),
)

# Defina a tarefa de scraping
latest_complaints_task = PythonOperator(
    task_id='latest_complaints',
    python_callable=latest_complaints,
    dag=dag
)

extract_details_task = PythonOperator(
    task_id='extract_details',
    python_callable=extract_details,
    dag=dag
)

# Defina as dependências
latest_complaints_task >> extract_details_task

