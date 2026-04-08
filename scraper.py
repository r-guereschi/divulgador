import requests
from bs4 import BeautifulSoup
import json

def scrape_fotop():
    try:
        url = "https://voce.fotop.com/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Selecionamos todos os cards encontrados
        cards = soup.find_all('div', class_='card-evt-busca', limit=4)
        
        eventos = []
        for card in cards:
            evento = {
                "titulo": card.find('div', class_='card-titulo-evento').text.strip(),
                "data": card.find('div', class_='card-data-evento').text.strip(),
                "local": card.find('span', class_='nome-cidade-card').text.strip(),
                "imagem": card.find('img', class_='img-card-evt-busca')['src'],
                "link": "https://voce.fotop.com" + card.find('a')['href']
            }
            eventos.append(evento)
        return eventos
    except Exception as e:
        print(f"Erro ao raspar Fotop: {e}")
        return []

# Executa e salva os 4 últimos
lista_fotop = scrape_fotop()
if lista_fotop:
    dados = {"fotop": lista_fotop}
    with open('eventos.json', 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)
    print(f"Sucesso: {len(lista_fotop)} eventos salvos.")