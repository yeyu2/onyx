Test script
import requests; r = requests.post('http://127.0.0.1:8001/execute', json={'code': 'print(42)', 'language': 'python'}); print(r.status_code, r.text)
