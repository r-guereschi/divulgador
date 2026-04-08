import requests
from bs4 import BeautifulSoup
import json

def scrape_fotop():
    try:
        url = "https://voce.fotop.com/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
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

def scrape_foco_radical():
    try:
        # URL da busca ou página principal da Foco Radical
        url = "https://vocee.focoradical.com.br/" 
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # A Foco Radical geralmente usa containers com a classe 'card-prova' ou similar
        # Ajustado para a estrutura comum da plataforma
        cards = soup.find_all('div', class_='item-prova', limit=4)
        
        eventos = []
        for card in cards:
            # Selecionando os dados com base na estrutura interna deles
            titulo_link = card.find('a', class_='titulo-prova')
            img_tag = card.find('img')
            data_local = card.find('div', class_='data-local-prova').text.strip().split('|')

            evento = {
                "titulo": titulo_link.text.strip(),
                "data": data_local[0].strip() if len(data_local) > 0 else "",
                "local": data_local[1].strip() if len(data_local) > 1 else "",
                "imagem": img_tag['src'] if img_tag else "",
                "link": titulo_link['href']
            }
            eventos.append(evento)
        return eventos
    except Exception as e:
        print(f"Erro ao raspar Foco Radical: {e}")
        return []

# --- EXECUÇÃO PRINCIPAL ---

lista_fotop = scrape_fotop()
lista_foco = scrape_foco_radical()

# Organiza o dicionário final para o seu HTML ler corretamente
dados_finais = {
    "fotop": lista_fotop,
    "foco_radical": lista_foco
}

# Salva tudo no mesmo arquivo JSON
try:
    with open('eventos.json', 'w', encoding='utf-8') as f:
        json.dump(dados_finais, f, indent=4, ensure_ascii=False)
    print(f"Sucesso! Fotop: {len(lista_fotop)} | Foco Radical: {len(lista_foco)} eventos salvos.")
except Exception as e:
    print(f"Erro ao salvar arquivo: {e}")