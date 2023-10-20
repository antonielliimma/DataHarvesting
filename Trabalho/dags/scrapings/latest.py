import requests
from bs4 import BeautifulSoup
import pandas as pd


def total_pages(soup):    
    items = soup.find_all('li', {'aria-label': 'pagination item'})
    numbers = []
    for item in items:
        text = item.get_text()
        if text.isdigit():
            numbers.append(int(text))

    return max(numbers)


def latest():
    urls = []
    url = "https://www.reclameaqui.com.br/empresa/prefeitura-fortaleza/lista-reclamacoes/?pagina=1"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'lxml')

        for _ in range(total_pages(soup)):
            links = soup.find_all('a')
            for link in links:
                h4 = link.find('h4')
                if h4 and 'title' in h4.attrs:            
                    url = link.get('href')  # Obtenha o atributo 'href' da tag <a>
                    if url:
                        urls.append({'url': url})

        df = pd.DataFrame(data=urls)
        df.to_csv('urls.csv', index=False)


        