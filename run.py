import time

from parser_wb import ParserWB, ParserSKU
import gtab


def main():
    print('Парсер запущен')

    gtab.head_setter()
    last_header_check = time.time()  # Время последней проверки заголовков

    while True:
        try:
            current_time = time.time()

            # Проверка заголовков
            if current_time - last_header_check >= 90:
                gtab.head_setter()
                last_header_check = current_time

            # Проверка на наличие активных задач
            task_status = gtab.is_any_task_active()
            if task_status:
                mode = gtab.wks2.acell('I5').value
                if mode == "Поиск":
                    print('Парсер запущен в режиме "Поиск"')
                    search_params = gtab.read_search_params()
                    if search_params:
                        for param in search_params:
                            parser = ParserWB(param['input_url'], param['row'], param['input_pages'])
                            parser.parse()
                elif mode == 'Артикул':
                    print('Парсер запущен в режиме "Артикул"')
                    sku_params = gtab.sku_read_params()
                    if sku_params:
                        for param in sku_params:
                            parser = ParserSKU(param['input_sku'], param['row'])
                            parser.parse()
                else:
                    raise ValueError('Ошибка[10], Укажите режим работы: (Поиск/Артикул)')

            time.sleep(3 if task_status else 15)

        except ValueError as e:
            print(e)
            gtab.parser_status(str(e))


if __name__ == '__main__':
    main()
