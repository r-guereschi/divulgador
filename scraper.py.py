import requests
from bs4 import BeautifulSoup
import json

def scrape_fotop():
    url = "https://voce.fotop.com/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Encontra o primeiro card de evento
    card = soup.find('div', class_='card-evt-busca')
    
    evento = {
        "titulo": card.find('div', class_='card-titulo-evento').text.strip(),
        "data": card.find('div', class_='card-data-evento').text.strip(),
        "local": card.find('span', class_='nome-cidade-card').text.strip(),
        "imagem": card.find('img', class_='img-card-evt-busca')['src'],
        "link": "https://voce.fotop.com" + card.find('a')['href']
    }
    return evento

# Salva em um arquivo JSON que o HTML vai ler
dados = {"fotop": scrape_fotop()}
with open('eventos.json', 'w') as f:
    json.dump(dados, f, indent=4)