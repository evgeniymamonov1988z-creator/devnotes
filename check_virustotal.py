import requests
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

API_KEY = '898c230dcb70c404c55b88c1e146483a7fb8d9cbe6b4f8793f1d1f0f31f855df'
FILE_PATH = r'C:\Users\evgen\Documents\GitHub\devnotes\dist\DevNotes.exe'

print('Uploading file to VirusTotal...')
try:
    with open(FILE_PATH, 'rb') as f:
        files = {'file': ('DevNotes.exe', f, 'application/octet-stream')}
        response = requests.post(
            'https://www.virustotal.com/api/v3/files',
            headers={'x-apikey': API_KEY},
            files=files,
            timeout=60
        )

    print(f'Status: {response.status_code}')
    data = response.json()
    print(data)

    if response.status_code == 200:
        analysis_id = data['data']['id']
        print(f'Analysis ID: {analysis_id}')
        print('Waiting for analysis...')
        
        for i in range(60):
            time.sleep(10)
            try:
                resp = requests.get(
                    f'https://www.virustotal.com/api/v3/analyses/{analysis_id}',
                    headers={'x-apikey': API_KEY},
                    timeout=30
                )
                result = resp.json()
                status = result['data']['attributes']['status']
                
                if status == 'completed':
                    stats = result['data']['attributes']['stats']
                    print(f'Results: {stats}')
                    break
                else:
                    print(f'Processing... {status}')
            except Exception as e:
                print(f'Error checking: {e}')
    else:
        print(f'Error: {response.text}')
except Exception as e:
    print(f'Failed: {e}')
