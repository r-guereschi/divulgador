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
        # A URL que contém esses cards (geralmente a home ou busca)
        url = "https://vocee.focoradical.com.br/" 
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # O card principal é a div com classe 'competition'
        cards = soup.find_all('div', class_='competition', limit=4)
        eventos = []

        for card in cards:
            wrapper = card.find('a', class_='competition-wrapper')
            if not wrapper:
                continue
                
            # Extração do Título
            titulo = wrapper.find('h2', class_='details-name').text.strip()
            
            # Extração do Link
            link = wrapper['href']
            if not link.startswith('http'):
                link = "https://www.focoradical.com.br" + link
            
            # Extração da Imagem (eles usam data-original para lazyload)
            img_div = wrapper.find('div', class_='competition-banner')
            imagem = img_div.get('data-original') or ""
            
            # Extração da Data (Concatenando dia, mês e ano)
            dia = wrapper.find('div', class_='calendar-day').text.strip()
            mes = wrapper.find('div', class_='calendar-month').text.strip()
            ano = wrapper.find('div', class_='calendar-year').text.strip()
            data_formatada = f"{dia} {mes} {ano}"
            
            # Extração do Local
            local = wrapper.find('small').text.strip() if wrapper.find('small') else "Brasil"

            eventos.append({
                "titulo": titulo,
                "data": data_formatada,
                "local": local,
                "imagem": imagem,
                "link": link
            })
            
        return eventos
    except Exception as e:
        print(f"Erro na Foco Radical: {e}")
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