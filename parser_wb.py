import requests
import re
from models import BigData
import gtab


class ParserWB:
    def __init__(self, input_url, row, input_pages):
        self.input_url = input_url
        self.row = row
        self.input_pages = int(input_pages)
        self.query = self.extract_param('search')
        self.brand_id = self.format_param('fbrand')
        self.supplier = self.format_param('fsupplier')
        self.price_range = self.format_param('priceU')
        self.page = 1

    def extract_param(self, param):
        match = re.search(rf'{param}=([^&]+)', self.input_url)
        return match.group(1) if match else ''

    def format_param(self, param):
        value = self.extract_param(param)
        return f'&{param}={value}' if value else ''

    def parse(self):
        gtab.parser_status('Выполняется парсинг')
        while self.page <= self.input_pages:
            try:
                parsing_url = f'https://search.wb.ru/exactmatch/ru/common/v5/search?ab_testing=false&appType=1&limit=300&curr=rub&dest=-1255987{self.brand_id}{self.supplier}&page={self.page}{self.price_range}&query={self.query}&resultset=catalog&sort=popular&spp=30&suppressSpellcheck=false'
                print(parsing_url)
                response = requests.get(parsing_url)
                if response.status_code != 200:
                    raise ValueError(f"[1]Ошибка: статус код {response.status_code}")

                data = response.json()
                print(data)

                if 'metadata' not in data or 'data' not in data:
                    raise ValueError("[2]Ошибка: нет данных в ответе")

                if 'name' not in data['metadata']:
                    raise ValueError("[3]Ошибка: По данному запросу ничего не найдено")

                info_table = BigData.parse_obj(data)
                if not info_table.data.products:
                    raise ValueError("[4]Ошибка: Нет товаров в ответе")

                name = info_table.metadata.name
                prompt_brand, prompt_supplier, prompt_price_from, prompt_price_to = '', '', '', ''

                filtered_products = []
                has_valid_json = False
                for product in info_table.data.products:
                    filtered_sizes = [size for size in product.sizes if
                                      any(size.price for size in product.sizes)]
                    if filtered_sizes:
                        filtered_products.append(product)
                        has_valid_json = True
                        prompt_brand = product.brand if self.brand_id else ''
                        prompt_supplier = product.supplier if self.supplier else ''
                        prompt_price_from, prompt_price_to = map(lambda x: int(x) / 100,
                                                                 self.extract_param('priceU').split(
                                                                     '%3B')) if self.price_range else ('', '')

                if not has_valid_json:
                    gtab.erorrs_transfer('[5]Ошибка: Неверный json, повторяю запрос...', self.row)
                    continue

                if not filtered_products:
                    raise ValueError("[6]Ошибка: Нет подходящих продуктов после фильтрации")

                while True:
                    gtab.head_setter()
                    data_written = gtab.data_to_sheets(filtered_products, name, prompt_brand, prompt_supplier,
                                                       prompt_price_from, prompt_price_to)
                    if data_written:
                        print("Данные успешно записаны в таблицу")
                        gtab.erorrs_transfer('', self.row)
                        break
                    else:
                        print("Данные не записаны, повторяю...")
                self.page += 1

            except ValueError as e:
                print(e)
                gtab.erorrs_transfer(str(e), self.row)
                break
        gtab.search_update_read_status(self.row)


class ParserSKU:

    def __init__(self, sku, row):
        self.input_sku = sku
        self.row = row

    def parse(self):
        gtab.parser_status('Выполняется парсинг')
        while True:
            try:
                parsing_url = f'https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1255987&spp=30&ab_testing=false&nm={self.input_sku}'
                print(parsing_url)
                response = requests.get(parsing_url)
                if response.status_code != 200:
                    raise ValueError(f"[1]Ошибка: статус код {response.status_code}")

                data = response.json()

                print(data)

                if 'data' not in data:
                    raise ValueError("[2]Ошибка: нет данных в ответе")

                info_table = BigData.parse_obj(data)
                if not info_table.data.products:
                    raise ValueError("[4]Ошибка: Нет товаров в ответе")

                filtered_products = []
                has_valid_json = False
                for product in info_table.data.products:
                    filtered_sizes = [size for size in product.sizes if
                                      any(size.price for size in product.sizes)]
                    if filtered_sizes:
                        filtered_products.append(product)
                        has_valid_json = True

                if not has_valid_json:
                    gtab.erorrs_transfer('[5]Ошибка: Неверный json, повторяю запрос...', self.row)
                    continue

                if not filtered_products:
                    raise ValueError("[6]Ошибка: Нет подходящих продуктов после фильтрации")

                while True:
                    gtab.head_setter()
                    data_written = gtab.sku_data_to_sheets(filtered_products)
                    if data_written:
                        print("Данные успешно записаны в таблицу")
                        gtab.erorrs_transfer('', self.row)
                        gtab.sku_update_read_status(self.row)
                        return
                    else:
                        print("Данные не записаны, повторяю...")

            except ValueError as e:
                print(e)
                gtab.erorrs_transfer(str(e), self.row)
                break
