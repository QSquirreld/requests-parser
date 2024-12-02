import gspread, time, re
from datetime import datetime as dt

gc = gspread.service_account(filename='creds.json')
wks = gc.open('parser-reports').sheet1
wks2 = gc.open('parser-reports').get_worksheet(1)
wks3 = gc.open('parser-reports').get_worksheet(2)


def is_any_task_active():
    """Проверяет, есть ли задачи для обработки и активен ли режим работы."""
    data = wks2.get_all_records()
    for row in data:
        if (row['Запуск_поиск'] == 'TRUE' and row['Прочитано_поиск'].lower() != 'да') or \
                (row['Запуск_артикул'] == 'TRUE' and row['Прочитано_артикул'].lower() != 'да'):
            return True
    return False


def head_setter():
    """Выполняет проверку заполненности заголовков на страницах таблицы"""
    headers_wks = [
        'Дата', 'SKU', 'Название бренда', 'Наименование товара', 'Магазин/Продавец', 'Цена со скидкой',
        'Базовая цена', 'Ссылка на товар', '', 'Ключ (Запрос)', 'Бренд (Запрос)', 'Магазин/Продавец (Запрос)',
        'Цена от (Запрос)', 'Цена до (Запрос)'
    ]

    headers_wks2 = [
        'Ссылка', 'Количество страниц', 'Запуск_поиск', 'Прочитано_поиск', 'Текущее состояние', 'Прочитано_артикул',
        'Запуск_артикул', 'Артикул', 'Состояние парсера'
    ]

    headers_wks3 = [
        'Дата', 'SKU', 'Название бренда', 'Наименование товара', 'Магазин/Продавец', 'Цена со скидкой',
        'Базовая цена', 'Ссылка на товар'
    ]

    current_headers_wks = wks.row_values(1)
    if current_headers_wks != headers_wks:
        wks.delete_rows(1)
        wks.insert_row(headers_wks, index=1)
        print("Заголовки первого листа обновлены.")

    current_headers_wks2 = wks2.row_values(1)
    if current_headers_wks2 != headers_wks2:
        wks2.delete_rows(1)
        wks2.insert_row(headers_wks2, index=1)
        print("Заголовки второго листа обновлены.")

    current_headers_wks3 = wks3.row_values(1)
    if current_headers_wks3 != headers_wks3:
        wks3.delete_rows(1)
        wks3.insert_row(headers_wks3, index=1)
        print("Заголовки третьего листа обновлены.")

    if wks2.acell('I4').value != 'Режим работы':
        wks2.update_acell('I4', 'Режим работы')


def read_search_params():
    """Считывает из таблицы параметры для поиска через ссылки"""
    data = wks2.get_all_records()
    search_params = []
    for i, row in enumerate(data):
        # Проверка на флаг и значение "Прочитано"
        if row['Запуск_поиск'] == 'TRUE' and row['Прочитано_поиск'].lower() != 'да':
            input_url = row['Ссылка']
            input_pages = row['Количество страниц']
            print(input_pages, type(input_pages))
            try:
                input_pages_int = int(input_pages)
                if input_pages_int < 1:
                    input_pages = '1'
                    wks2.update_cell(i + 2, 2, input_pages)
                elif input_pages_int > 10:
                    input_pages = '10'
                    wks2.update_cell(i + 2, 2, input_pages)
            except ValueError:
                input_pages = '1'
                wks2.update_cell(i + 2, 2, input_pages)
            print(f'Получена ссылка: {input_url}')
            try:
                if "https://www.wildberries.ru/catalog/0/search.aspx" not in input_url and "&search=" not in input_url:
                    raise ValueError("[0]Ошибка: В запросе содержится неверная ссылка")

                search_params.append({
                    'input_url': input_url,
                    'row': i + 2,  # Google Sheets is 1-indexed
                    'input_pages': input_pages
                })
            except ValueError as e:
                print(e)
                erorrs_transfer(str(e), i + 2)
        else:
            erorrs_transfer('', i + 2)
    if search_params:
        return search_params
    else:
        print('Нет данных для обработки. Ожидание новых данных или исправления ссылок...')
        parser_status('Нет данных для обработки. Ожидание новых данных или исправления ссылок...')


def sku_read_params():
    """Считывает из таблицы параметры для поиска через артикулы"""
    data = wks2.get_all_records()
    sku_params = []
    for i, row in enumerate(data):
        if row['Запуск_артикул'] == 'TRUE' and row['Прочитано_артикул'].lower() != 'да':
            input_sku = row['Артикул']
            print(f'Получен sku: {input_sku}')
            try:
                if not input_sku or not re.match(r'^[0-9;]+$', str(input_sku)):
                    raise ValueError("[0]Ошибка: В запросе содержится неверный артикул")

                sku_params.append({
                    'input_sku': input_sku,
                    'row': i + 2  # Google Sheets is 1-indexed
                })
            except ValueError as e:
                print(e)
                erorrs_transfer(str(e), i + 2)
        else:
            erorrs_transfer('', i + 2)
    if sku_params:
        return sku_params
    else:
        print('Нет данных для обработки. Ожидание новых данных или исправления введённых...')
        parser_status('Нет данных для обработки. Ожидание новых данных или исправления введённых...')


def search_update_read_status(row):
    """Обновляет статус 'Прочтено' на странице вводных данных в режиме 'Ссылка'"""
    wks2.update([['Да']], f'D{row}')


def sku_update_read_status(row):
    """Обновляет статус 'Прочтено' на странице ввода в режиме 'Артикул'"""
    wks2.update([['Да']], f'F{row}')


def erorrs_transfer(error, row):
    """Отправляет на страницу ввода информацию о возникающих ошибках"""
    wks2.update([[f'{error}']], f'E{row}')
    time.sleep(2)


def parser_status(status: str):
    wks2.update([[status]], 'I2')
    while not all(value == '' for value in wks2.col_values(5)[1:]):
        wks2.update([['Измените или удалите нерабочие параметры(ссылки/артикулы)!'.upper()]], 'I2')
        time.sleep(5)
    else:
        wks2.update([['']], 'I2')


def data_to_sheets(filtered_products, name, prompt_brand, prompt_supplier, price_from, price_to):
    """Отправляет результаты парсинга по ссылкам в первую страницу"""
    rows_to_add = []

    for product in filtered_products:
        url = f'https://www.wildberries.ru/catalog/{product.id}/detail.aspx'
        row = [
            dt.now().strftime('%d-%m-%Y %H:%M'),
            product.id,
            product.brand,
            product.name,
            product.supplier,
            product.sizes[0].price.total / 100,
            product.sizes[0].price.basic / 100,
            url,
            '',
            name,
            prompt_brand,
            prompt_supplier,
            price_from,
            price_to
        ]
        rows_to_add.append(row)

    if rows_to_add:
        next_row = len(wks.get_all_values()) + 1
        range_to_update = f'A{next_row}:N{next_row + len(rows_to_add) - 1}'
        wks.update(range_to_update, rows_to_add)
        return True
    return False


def sku_data_to_sheets(filtered_products):
    """Отправляет результаты парсинга по артикулам в третью страницу"""
    existing_data = wks3.get_all_records()
    existing_ids = {row['SKU']: i + 2 for i, row in enumerate(existing_data)}

    rows_to_add = []
    rows_to_update = []

    for product in filtered_products:
        url = f'https://www.wildberries.ru/catalog/{product.id}/detail.aspx'
        new_row = [
            dt.now().strftime('%d-%m-%Y %H:%M'),
            product.id,
            product.brand,
            product.name,
            product.supplier,
            product.sizes[0].price.total / 100,
            product.sizes[0].price.basic / 100,
            url
        ]

        if product.id in existing_ids:
            row_index = existing_ids[product.id]
            rows_to_update.append((row_index, new_row))
        else:
            rows_to_add.append(new_row)

    if rows_to_update:
        for row_index, row_data in rows_to_update:
            range_to_update = f'A{row_index}:H{row_index}'
            wks3.update(range_to_update, [row_data])

    if rows_to_add:
        next_row = len(existing_data) + 2  # Plus 2 to account for the header row
        range_to_add = f'A{next_row}:H{next_row + len(rows_to_add) - 1}'
        wks3.update(range_to_add, rows_to_add)

    return bool(rows_to_add or rows_to_update)
