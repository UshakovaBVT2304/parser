import requests
import json

def save_to_json_file(data, filename):
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def fetch_vacancies_and_save_to_file():
    url = 'https://api.hh.ru/vacancies'
    params = {
        'text': 'python'
    }
    response = requests.get(url, params=params)
    vacancies_data = response.json()
    save_to_json_file(vacancies_data, 'vacancies.json')

fetch_vacancies_and_save_to_file()
