import os
import requests
import json
from dotenv import load_dotenv
import base64

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações do GitHub
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO')
GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')

# Verificar se as variáveis de ambiente foram carregadas corretamente
if not GITHUB_TOKEN or not GITHUB_REPO:
    raise ValueError("Certifique-se de que as variáveis de ambiente GITHUB_TOKEN e GITHUB_REPO estão definidas no arquivo .env")

# URL do arquivo CSV no Google Drive
file_id = "1IjIEhLc9n8eLKeY-yh_YigKVWbhgGBsN"
download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

# Função para fazer upload do arquivo para o GitHub
def upload_to_github(file_path, repo, branch, token):
    with open(file_path, 'rb') as file:
        content = base64.b64encode(file.read()).decode('utf-8')
    file_name = os.path.basename(file_path)
    url = f"https://api.github.com/repos/{repo}/contents/{file_name}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "message": f"Upload {file_name}",
        "content": content,
        "branch": branch
    }
    response = requests.put(url, headers=headers, data=json.dumps(data))
    if response.status_code == 201:
        print(f"Arquivo '{file_name}' enviado com sucesso para o GitHub.")
    else:
        print(f"Erro ao enviar arquivo para o GitHub: {response.json()}")
        print(f"URL: {url}")
        print(f"Headers: {headers}")
        print(f"Data: {data}")

try:
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