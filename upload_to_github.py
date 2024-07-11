import os
import requests
import json
import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações do Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CLIENT_SECRET_FILE = os.getenv('CLIENT_SECRET_FILE')
TOKEN_FILE = os.getenv('TOKEN_FILE')
DRIVE_FOLDER_ID = os.getenv('DRIVE_FOLDER_ID')

# Configurações do GitHub
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO')
GITHUB_BRANCH = os.getenv('GITHUB_BRANCH')

# Verificar se as variáveis de ambiente foram carregadas corretamente
if not CLIENT_SECRET_FILE or not TOKEN_FILE or not DRIVE_FOLDER_ID or not GITHUB_TOKEN or not GITHUB_REPO or not GITHUB_BRANCH:
    raise ValueError("Certifique-se de que todas as variáveis de ambiente estão definidas no arquivo .env")

# Função para obter credenciais do usuário
def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as token:
            creds = Credentials.from_authorized_user_info(json.load(token), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return creds

# Função para encontrar arquivo por nome na pasta do Google Drive
def find_file_by_name(drive_service, file_name, folder_id):
    query = f"name = '{file_name}' and '{folder_id}' in parents and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])
    return items[0]['id'] if items else None

# Função para enviar arquivo para o GitHub
def upload_to_github(file_path, repo, branch, token):
    with open(file_path, 'rb') as file:
        content = file.read()
    base64_content = base64.b64encode(content).decode('utf-8')
    file_name = os.path.basename(file_path)
    url = f"https://api.github.com/repos/{repo}/contents/{file_name}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "message": f"Add {file_name}",
        "content": base64_content,
        "branch": branch
    }
    response = requests.put(url, headers=headers, data=json.dumps(data))
    if response.status_code == 201:
        print(f"Arquivo '{file_name}' enviado com sucesso para o GitHub.")
    else:
        print(f"Erro ao enviar arquivo para o GitHub: {response.json()}")
        print(f"URL: {url}")
        print(f"Headers: {headers}")

# Autenticação
creds = get_credentials()
drive_service = build('drive', 'v3', credentials=creds)

# ID do arquivo Google Drive a ser baixado
file_id = "1IjIEhLc9n8eLKeY-yh_YigKVWbhgGBsN"

# URL de download direto do arquivo
download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

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

    # Ler o CSV com pandas e salvar como XLSX
    local_xlsx_path = local_csv_path.replace('.csv', '.xlsx')
    df = pd.read_csv(local_csv_path)
    df.to_excel(local_xlsx_path, index=False)

    print(f"Arquivo XLSX salvo em: {local_xlsx_path}")

    # Procura por um arquivo existente com o mesmo nome (XLSX)
    existing_file_id = find_file_by_name(drive_service, os.path.basename(local_xlsx_path), DRIVE_FOLDER_ID)

    if existing_file_id:
        # Atualiza o arquivo existente
        print(f"Atualizando arquivo existente: {os.path.basename(local_xlsx_path)}")
        media = MediaFileUpload(local_xlsx_path, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', resumable=True)
        updated_file = drive_service.files().update(
            fileId=existing_file_id,
            media_body=media,
            fields='id'
        ).execute()
        print(f"Arquivo '{os.path.basename(local_xlsx_path)}' atualizado com sucesso no Google Drive. ID: {updated_file.get('id')}")

    else:
        # Cria um novo arquivo
        print(f"Criando novo arquivo: {os.path.basename(local_xlsx_path)}")
        file_metadata = {
            'name': os.path.basename(local_xlsx_path),
            'parents': [DRIVE_FOLDER_ID]
        }
        media = MediaFileUpload(local_xlsx_path, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', resumable=True)
        uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"Arquivo '{os.path.basename(local_xlsx_path)}' enviado com sucesso para o Google Drive. ID: {uploaded_file.get('id')}")

    # Enviar o arquivo CSV para o GitHub
    upload_to_github(local_csv_path, GITHUB_REPO, GITHUB_BRANCH, GITHUB_TOKEN)

except requests.exceptions.RequestException as e:
    print(f"Erro ao baixar o arquivo: {e}")

except HttpError as e:
    print(f"Erro na API do Google Drive: {e}")
    if e.resp.status == 403:
        print("Verifique as permissões da pasta de destino no Google Drive.")
    import traceback
    traceback.print_exc()

except Exception as e:
    print(f"Erro inesperado: {e}")
    import traceback
    traceback.print_exc()