import os
import requests
import json
from dotenv import load_dotenv
import base64
import hashlib

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações do GitHub
GITHUB_TOKEN = os.getenv('MY_GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO')
GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')

# Função auxiliar para calcular o hash SHA-1 de um arquivo
def calculate_file_sha1(file_path):
    BUF_SIZE = 65536  # Vamos ler o arquivo em pedaços de 64kb
    sha1 = hashlib.sha1()

    with open(file_path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
    
    return sha1.hexdigest()

# Função para fazer upload do arquivo para o GitHub
def upload_to_github(file_path, repo, branch, token):
    file_name = os.path.basename(file_path)
    url = f"https://api.github.com/repos/{repo}/contents/{file_name}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Verificar se o arquivo já existe no GitHub
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        sha = response.json()['sha']
        # Baixar o arquivo existente para comparar
        download_url = response.json()['download_url']
        existing_file_response = requests.get(download_url)
        existing_file_sha1 = hashlib.sha1(existing_file_response.content).hexdigest()
    else:
        sha = None
        existing_file_sha1 = None
    
    # Calcular o SHA-1 do arquivo local
    local_file_sha1 = calculate_file_sha1(file_path)
    
    # Se os hashes são iguais, não é necessário atualizar o arquivo no GitHub
    if existing_file_sha1 == local_file_sha1:
        print(f"O arquivo '{file_name}' já está atualizado no GitHub. Upload não necessário.")
        return
    
    with open(file_path, 'rb') as file:
        content = base64.b64encode(file.read()).decode('utf-8')
    
    data = {
        "message": f"Upload {file_name}",
        "content": content,
        "branch": branch
    }
    
    if sha:
        data["sha"] = sha
    
    response = requests.put(url, headers=headers, data=json.dumps(data))
    if response.status_code in [200, 201]:
        print(f"Arquivo '{file_name}' enviado com sucesso para o GitHub.")
    else:
        print(f"Erro ao enviar arquivo para o GitHub: {response.json()}")

try:
    # URL do arquivo CSV no Google Drive
    file_id = "1IjIEhLc9n8eLKeY-yh_YigKVWbhgGBsN"
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    print(f"Download URL: {download_url}")

    # Download do CSV
    response = requests.get(download_url)
    response.raise_for_status()

    # Extrair o nome do arquivo do cabeçalho da resposta
    content_disposition = response.headers.get('content-disposition')
    if content_disposition:
        file_name = content_disposition.split('filename=')[1].strip('"')
    else:
        file_name = 'data_latest.csv'  # Nome padrão caso o cabeçalho não esteja presente

    # Salvar o arquivo baixado localmente como CSV
    local_csv_path = os.path.join(os.getcwd(), file_name)
    with open(local_csv_path, 'wb') as f:
        f.write(response.content)

    print(f"Arquivo CSV baixado e salvo em: {local_csv_path}")

    # Fazer upload do arquivo CSV para o GitHub
    upload_to_github(local_csv_path, GITHUB_REPO, GITHUB_BRANCH, GITHUB_TOKEN)

except requests.exceptions.RequestException as e:
    print(f"Erro ao baixar o arquivo: {e}")

except Exception as e:
    print(f"Erro inesperado: {e}")
    import traceback
    traceback.print_exc()
