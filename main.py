import requests
import psycopg2
from psycopg2 import sql
from psycopg2 import OperationalError
from pywebio.input import input, select, input_group
from pywebio.output import put_html
from pywebio import start_server

def create_connection(db_name, db_user, db_password, db_host, db_port, timeout=15):
    connection = None
    try:
        connection = psycopg2.connect(
            database=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
            connect_timeout=timeout
        )
        print("Подключение к базе данных успешно установлено")
    except OperationalError as e:
        print(f"Ошибка при подключении к базе данных: {e}")
    return connection
connection = create_connection("vacancies", "postgres", "1234", "127.0.0.1", "1234")

def create_table(connection):
    with connection.cursor() as cursor:
        create_table_query = """
        CREATE TABLE IF NOT EXISTS vacancies (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255),
            company VARCHAR(255),
            city VARCHAR(100),
            salary_from INTEGER,
            salary_to INTEGER,
            currency VARCHAR(3),
            work_format VARCHAR(50),
            work_experience VARCHAR(50),
            employment_type VARCHAR(50),
            vacancy_url TEXT
        );
        """
        cursor.execute(create_table_query)
    connection.commit()
create_table(connection)

def insert_vacancy_data(connection, vacancy_data):
    with connection.cursor() as cursor:
        query = sql.SQL("""
            INSERT INTO vacancies (name, company, city, salary_from, salary_to, currency, work_format, work_experience, employment_type, vacancy_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING;
        """)
        cursor.execute(query, (
            vacancy_data['name'],
            vacancy_data['company'],
            vacancy_data['city'],
            vacancy_data['salary_from'],
            vacancy_data['salary_to'],
            vacancy_data['currency'],
            vacancy_data['work_format'],
            vacancy_data['work_experience'],
            vacancy_data['employment_type'],
            vacancy_data['vacancy_url']
        ))
    connection.commit()

EMPLOYMENT_TYPE_MAP = {
    'all': None,
    'full': 'full',
    'part': 'part',
    'probation': 'probation',
}
def found_vacancies_and_fill_db(vacancies_title=None, city_id=None, employment_type=None ):
    vacancies_to_insert = []
    page = 0
    has_more_pages = True
    api_employment_type = EMPLOYMENT_TYPE_MAP.get(employment_type, None)

    while has_more_pages and page<=200:
        params = {
            'text': vacancies_title,
            'area': city_id,
            'employment': api_employment_type ,
            'page': page
        }
        response = requests.get('https://api.hh.ru/vacancies', params=params)
        vacancies = response.json()
        page_items = vacancies.get('items', [])
        has_more_pages = vacancies.get('pages', page) > page

        for item in page_items:
            name = item.get('name', '').lower()
            if vacancies_title.lower() in name.lower():
                salary_data = item.get('salary', {})
                if salary_data:
                    salary_from = salary_data.get('from')
                    salary_to = salary_data.get('to')
                    currency = salary_data.get('currency', 'RUR')
                else:
                    salary_from = None
                    salary_to = None
                    currency = 'RUR'
                salary_str = 'не указана'
                if salary_from and salary_to:
                    salary_str = f"{salary_from} - {salary_to} {currency}"
                elif salary_from:
                    salary_str = f"от {salary_from} {currency}"
                elif salary_to:
                    salary_str = f"до {salary_to} {currency}"

                vacancy_data = {
                    'name': item.get('name'),
                    'company': item.get('employer', {}).get('name'),
                    'city': item.get('area', {}).get('name'),
                    'salary_from': salary_from,
                    'salary_to': salary_to,
                    'currency': currency,
                    'work_format': item.get('schedule', {}).get('name'),
                    'work_experience': item.get('experience', {}).get('name'),
                    'employment_type': item.get('employment', {}).get('name'),
                    'vacancy_url': f"https://hh.ru/vacancy/{item.get('id')}"
                }


                vacancies_to_insert.append(vacancy_data)
                vacancy_output = f"""
                        <p><b>Название вакансии:</b> {vacancy_data['name']}</p>
                        <p><b>Компания:</b> {vacancy_data['company']}</p>
                        <p><b>Город:</b> {vacancy_data['city']}</p>
                        <p><b>Зарплата:</b> {salary_str}</p>
                        <p><b>Формат работы:</b> {vacancy_data['work_format']}</p>
                        <p><b>Требуемый опыт работы:</b> {vacancy_data['work_experience']}</p>
                        <p><b>Занятость:</b> {vacancy_data['employment_type']}</p>
                        <p><b>Ссылка на вакансию:</b> <a href="{vacancy_data['vacancy_url']}" target="_blank">{vacancy_data['vacancy_url']}</a></p>
                        <br>
                        """
                put_html(vacancy_output)

        page+=1
    if not vacancies_to_insert:
        put_html("<p>Вакансии не найдены. Проверьте введённые фильтры и название.</p>")
    else:
        for vacancy_data in vacancies_to_insert:
            insert_vacancy_data(connection, vacancy_data)
def remove_duplicates(connection):
    with connection.cursor() as cursor:
        delete_query = """
        DELETE FROM vacancies
        WHERE ctid IN (
            SELECT ctid
            FROM (
                SELECT ctid, ROW_NUMBER() OVER (PARTITION BY vacancy_url ORDER BY ctid) AS rnum
                        FROM vacancies
            ) t
            WHERE t.rnum > 1
            );
            """
        cursor.execute(delete_query)
    connection.commit()
remove_duplicates(connection)

def main():
    employment_options = list(EMPLOYMENT_TYPE_MAP.keys())
    data = input_group("Ввод данных для поиска вакансий", [
        input('Введите название вакансии', name='vacancies_title'),
        input('Введите идентификатор города (1 - Москва, 2 - Санкт-Петербург)', name='city_id', type='number'),
        select('Выберите тип занятости (all - Не важно, full - Полная занятость, part - Частичная занятость, probation - Стажировка)', options=employment_options, name='employment_type')
    ])
    user_selected_employment = data['employment_type']
    api_employment_type = EMPLOYMENT_TYPE_MAP.get(user_selected_employment, None)
    found_vacancies_and_fill_db(vacancies_title=data['vacancies_title'], city_id=data['city_id'], employment_type=api_employment_type)

if __name__ == '__main__':
    start_server(main, port=8080)
