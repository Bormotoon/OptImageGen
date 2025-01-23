import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image
import threading
import queue

class ImageConverterApp:
    """
    Класс приложения для конвертации изображений с графическим интерфейсом на основе Tkinter.

    Этот класс предоставляет интерфейс для выбора исходных изображений, настройки форматов и размеров
    конвертации, генерации HTML-кода с атрибутом srcset и lazy loading, а также отображения прогресса
    выполнения конвертации.
    """

    def __init__(self, master):
        """
        Инициализирует приложение.

        :param master: Корневой объект Tkinter.
        """
        self.master = master
        self.master.title("Image Converter")
        self.master.geometry("1200x700")  # Устанавливаем начальный размер окна

        # Инициализация переменных для хранения путей и настроек
        self.source_image_paths = tk.StringVar()
        self.output_folder_path = tk.StringVar()
        self.widths_string = tk.StringVar(value="400,800,1200")  # Значения по умолчанию для ширин
        self.selected_formats = {
            "JPEG": tk.BooleanVar(value=False),  # JPEG отключен по умолчанию
            "PNG": tk.BooleanVar(value=False),   # PNG отключен по умолчанию
            "WEBP": tk.BooleanVar(value=True)    # WEBP включен по умолчанию
        }
        self.generate_html = tk.BooleanVar(value=True)       # Генерация HTML-кода включена по умолчанию
        self.add_lazy_loading = tk.BooleanVar(value=True)   # Добавление lazy loading включено по умолчанию

        # Словарь для сопоставления путей файлов с ID элементов в Treeview
        self.file_to_item = {}

        # Очередь для обмена сообщениями между рабочим потоком и главным потоком
        self.queue = queue.Queue()

        # Флаг для предотвращения повторного запуска конвертации
        self.conversion_in_progress = False

        # Создание элементов интерфейса
        self.create_widgets()

        # Запуск периодической проверки очереди сообщений
        self.master.after(100, self.process_queue)

    def create_widgets(self):
        """
        Создаёт и размещает все виджеты интерфейса приложения.
        """
        # Создание родительского фрейма для верхней части интерфейса
        frame_top = tk.Frame(self.master)
        frame_top.pack(fill="x", padx=10, pady=5)

        # Разделение верхней части на две части: Настройки и Предпросмотр HTML
        frame_left = tk.LabelFrame(frame_top, text="Настройки")
        frame_left.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        frame_right = tk.LabelFrame(frame_top, text="Предпросмотр HTML-кода")
        frame_right.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        # ------------------------ Левая половина (Настройки) ------------------------

        # ========== Выбор исходного файла ==========
        frame_source = tk.Frame(frame_left)
        frame_source.pack(fill="x", padx=5, pady=2)  # Уменьшены отступы

        # Метка для выбора файлов
        lbl_source = tk.Label(frame_source, text="Файлы:", width=15, anchor='w')  # Фиксированная ширина и выравнивание по левому краю
        lbl_source.pack(side="left", padx=5, pady=2)

        # Поле для отображения выбранных файлов
        entry_source = tk.Entry(frame_source, textvariable=self.source_image_paths, width=50, state='readonly')
        entry_source.pack(side="left", padx=5, pady=2)

        # Кнопка для открытия диалога выбора файлов
        btn_browse_source = tk.Button(frame_source, text="Обзор...", command=self.browse_source_image)
        btn_browse_source.pack(side="left", padx=5, pady=2)

        # ========== Выбор папки для сохранения ==========
        frame_output = tk.Frame(frame_left)
        frame_output.pack(fill="x", padx=5, pady=2)  # Уменьшены отступы

        # Метка для выбора папки
        lbl_output_folder = tk.Label(frame_output, text="Папка:", width=15, anchor='w')  # Фиксированная ширина и выравнивание по левому краю
        lbl_output_folder.pack(side="left", padx=5, pady=2)

        # Поле для отображения выбранной папки
        entry_output_folder = tk.Entry(frame_output, textvariable=self.output_folder_path, width=50, state='readonly')
        entry_output_folder.pack(side="left", padx=5, pady=2)

        # Кнопка для открытия диалога выбора папки
        btn_browse_output = tk.Button(frame_output, text="Обзор...", command=self.browse_output_folder)
        btn_browse_output.pack(side="left", padx=5, pady=2)

        # ========== Форматы ==========
        frame_formats = tk.Frame(frame_left)
        frame_formats.pack(fill="x", padx=5, pady=2)  # Уменьшены отступы

        # Метка для выбора форматов
        lbl_formats = tk.Label(frame_formats, text="Форматы:")
        lbl_formats.pack(side="left", padx=5, pady=2)

        # Создание чекбоксов для выбора форматов
        for fmt in self.selected_formats:
            cb = tk.Checkbutton(
                frame_formats,
                text=fmt,
                variable=self.selected_formats[fmt],
                command=self.update_preview  # Обновление предпросмотра при изменении форматов
            )
            cb.pack(side="left", padx=5, pady=2)

        # ========== Размеры (ширины) ==========
        frame_sizes = tk.Frame(frame_left)
        frame_sizes.pack(fill="x", padx=5, pady=2)  # Уменьшены отступы

        # Метка для ввода размеров
        lbl_sizes = tk.Label(frame_sizes, text="Ширины:")
        lbl_sizes.pack(side="left", padx=5, pady=2)

        # Поле для ввода размеров через запятую
        entry_sizes = tk.Entry(frame_sizes, textvariable=self.widths_string, width=30)
        entry_sizes.pack(side="left", padx=5, pady=2)
        entry_sizes.bind("<KeyRelease>", lambda event: self.update_preview())  # Обновление предпросмотра при изменении размеров

        # ========== HTML Опции ==========
        frame_html_options = tk.Frame(frame_left)
        frame_html_options.pack(fill="x", padx=5, pady=2)  # Уменьшены отступы

        # Чекбокс для генерации HTML-кода
        chk_generate_html = tk.Checkbutton(
            frame_html_options,
            text="Генерировать HTML-код для изображений",
            variable=self.generate_html,
            command=self.update_html_preview_after_selection  # Обновление HTML-предпросмотра при изменении опций
        )
        chk_generate_html.pack(anchor='w', padx=5, pady=2)

        # Чекбокс для добавления lazy loading
        chk_lazy_loading = tk.Checkbutton(
            frame_html_options,
            text="Добавить Lazy Loading",
            variable=self.add_lazy_loading,
            command=self.update_html_preview_after_selection  # Обновление HTML-предпросмотра при изменении опций
        )
        chk_lazy_loading.pack(anchor='w', padx=5, pady=2)

        # ------------------------ Правая половина (Предпросмотр HTML-кода) ------------------------

        # Виджет Text для предпросмотра HTML-кода
        self.text_html_preview = tk.Text(frame_right, height=15, width=60, state='disabled', wrap='none')  # wrap='none' отключает переносы строк
        self.text_html_preview.pack(fill='both', expand=True, padx=5, pady=2)  # Уменьшены отступы и высота

        # ========== Кнопка конвертации и статус ==========
        frame_convert = tk.Frame(self.master)
        frame_convert.pack(pady=5)  # Уменьшены вертикальные отступы

        # Кнопка для запуска конвертации
        self.btn_convert = tk.Button(
            frame_convert,
            text="Конвертировать!",
            command=self.start_conversion,
            bg="#4CAF50",   # Зеленый фон
            fg="#ffffff",   # Белый текст
            padx=10,
            pady=5          # Уменьшены внутренние отступы
        )
        self.btn_convert.pack(side="left", padx=5, pady=2)

        # Метка для отображения общего статуса конвертации
        self.lbl_conversion_status = tk.Label(frame_convert, text="", font=("Arial", 12))
        self.lbl_conversion_status.pack(side="left", padx=10, pady=2)

        # ========== Поле предпросмотра ==========
        frame_preview = tk.LabelFrame(self.master, text="Предпросмотр: Предполагаемые файлы")
        frame_preview.pack(fill="both", expand=True, padx=10, pady=5, ipady=5)

        # Настройка стилей для чередования цветов строк в Treeview
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#FFFFFF", foreground="black", rowheight=25, fieldbackground="#FFFFFF")
        style.map('Treeview', background=[('selected', '#347083')])  # Цвет выбранной строки

        style.configure("OddRow", background="#f0f0f0")    # Цвет нечетных строк
        style.configure("EvenRow", background="#ffffff")   # Цвет четных строк

        # Создание Treeview для отображения предполагаемых файлов и их статусов
        columns = ("File Path", "Status")
        self.tree_preview = ttk.Treeview(frame_preview, columns=columns, show='headings', selectmode='browse')
        self.tree_preview.heading("File Path", text="Путь к файлу")
        self.tree_preview.heading("Status", text="Статус")
        self.tree_preview.column("File Path", anchor="w", width=900)
        self.tree_preview.column("Status", anchor="center", width=100)

        # Создание вертикальной полосы прокрутки для Treeview
        scrollbar = ttk.Scrollbar(frame_preview, orient="vertical", command=self.tree_preview.yview)
        self.tree_preview.configure(yscroll=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.tree_preview.pack(fill="both", expand=True)

    def browse_source_image(self):
        """
        Открывает диалог выбора исходных изображений и устанавливает папку экспорта по умолчанию.

        При выборе изображений пути к ним отображаются в поле "Файлы:", а папка экспорта устанавливается
        в ту же директорию, что и первый выбранный файл.
        """
        file_paths = filedialog.askopenfilenames(
            title="Выберите исходные изображения",
            filetypes=[
                ("Все файлы изображений", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif"),
                ("PNG файлы", "*.png"),
                ("JPEG файлы", "*.jpg;*.jpeg"),
                ("WEBP файлы", "*.webp"),
                ("BMP файлы", "*.bmp"),
                ("GIF файлы", "*.gif"),
                ("Все файлы", "*.*")]
        )
        if file_paths:
            # Преобразуем список путей в строку, разделённую запятыми
            self.source_image_paths.set(", ".join(file_paths))
            # Установим папку экспорта в ту же папку, что и первый выбранный файл
            first_file_dir = os.path.dirname(file_paths[0])
            self.output_folder_path.set(first_file_dir)
            self.update_preview()
            # Генерация HTML-кода для первого изображения, если опция выбрана
            if self.generate_html.get():
                self.generate_html_preview_for_first_image(file_paths[0])

    def browse_output_folder(self):
        """
        Открывает диалог выбора папки для сохранения результатов.

        При выборе папки пути к файлам обновляются, и при активированной опции генерации HTML-кода
        обновляется предпросмотр HTML для первого изображения.
        """
        folder_path = filedialog.askdirectory(title="Выберите папку для сохранения")
        if folder_path:
            self.output_folder_path.set(folder_path)
            self.update_preview()
            # Генерация HTML-кода для первого изображения, если опция выбрана
            if self.generate_html.get() and self.source_image_paths.get():
                first_image_path = self.source_image_paths.get().split(", ")[0]
                self.generate_html_preview_for_first_image(first_image_path)

    def update_preview(self):
        """
        Обновляет поле предпросмотра с предполагаемыми файлами для конвертации.

        Включает генерируемые файлы на основе выбранных форматов и размеров, а также добавляет
        файл `code.txt` для хранения сгенерированного HTML-кода при активированной опции.
        """
        # Очистка существующих записей в Treeview
        self.tree_preview.delete(*self.tree_preview.get_children())
        self.file_to_item.clear()  # Очистка сопоставлений файлов с элементами Treeview

        # Получение путей к исходным файлам и настройкам
        source_paths = self.source_image_paths.get().split(", ")
        output_folder = self.output_folder_path.get()
        widths_input = self.widths_string.get()
        selected_formats_list = [fmt for fmt, var in self.selected_formats.items() if var.get()]

        # Проверка наличия необходимых данных
        if not source_paths or not any(os.path.isfile(path) for path in source_paths):
            return  # Ничего не делаем, если нет исходных файлов

        if not selected_formats_list:
            return  # Ничего не делаем, если нет выбранных форматов

        # Обработка размеров
        try:
            widths = [int(w.strip()) for w in widths_input.split(",") if w.strip().isdigit()]
            if not widths:
                raise ValueError
        except ValueError:
            return  # Ничего не делаем, если размеры некорректны

        # Если папка не указана, предполагаем папку исходного файла
        if not output_folder:
            output_folder = os.path.dirname(source_paths[0])

        # Проверка существования папки
        if not os.path.isdir(output_folder):
            return  # Ничего не делаем, если папка не существует

        # Добавление всех генерируемых файлов в Treeview
        for source_path in source_paths:
            base_name = os.path.splitext(os.path.basename(source_path))[0]
            for width in widths:
                for fmt in selected_formats_list:
                    ext = fmt.lower()
                    if fmt == "JPEG":
                        ext = "jpg"  # Используем .jpg для JPEG
                    out_filename = f"{base_name}-{width}w.{ext}"
                    out_path = os.path.join(output_folder, out_filename)

                    # Определение тега для чередования цветов строк
                    row_tag = "evenrow" if len(self.tree_preview.get_children()) % 2 == 0 else "oddrow"
                    item_id = self.tree_preview.insert("", "end", values=(out_path, ""), tags=(row_tag,))
                    self.file_to_item[out_path] = item_id  # Сохранение сопоставления пути файла с элементом Treeview

        # Добавление "code.txt" только один раз и в конец списка
        if self.generate_html.get():
            code_filename = "code.txt"
            code_path = os.path.join(output_folder, code_filename)
            if code_path not in self.file_to_item:
                item_id = self.tree_preview.insert("", "end", values=(code_path, ""), tags=("evenrow",))
                self.file_to_item[code_path] = item_id  # Сохранение ID элемента

        # Применение стилей для чередования цветов строк
        self.tree_preview.tag_configure("evenrow", background="#ffffff")
        self.tree_preview.tag_configure("oddrow", background="#f0f0f0")

        # Обновление HTML-предпросмотра, если опция активирована и есть хотя бы одно изображение
        if self.generate_html.get() and source_paths:
            first_image_path = source_paths[0]
            self.generate_html_preview_for_first_image(first_image_path)

    def generate_html_preview_for_first_image(self, source_path):
        """
        Генерирует HTML-код для первого исходного изображения и отображает его в предпросмотре.

        :param source_path: Путь к первому исходному изображению.
        """
        output_folder = self.output_folder_path.get()
        widths_input = self.widths_string.get()
        selected_formats_list = [fmt for fmt, var in self.selected_formats.items() if var.get()]

        # Проверка существования папки
        if not os.path.isdir(output_folder):
            return  # Папка не существует

        try:
            widths = sorted([int(w.strip()) for w in widths_input.split(",") if w.strip().isdigit()])
            if not widths:
                raise ValueError
        except ValueError:
            return  # Некорректные размеры

        base_name = os.path.splitext(os.path.basename(source_path))[0]
        html_code = ""
        srcset_entries = []
        smallest_image = ""
        alt_text = base_name.replace("-", " ")
        sizes_attr = "(max-width: 480px) 100px, (max-width: 768px) 120px, 120px"
        loading_attr = 'loading="lazy"' if self.add_lazy_loading.get() else ''  # Добавление атрибута loading при необходимости

        # Сборка строк для srcset
        for width in widths:
            for fmt in selected_formats_list:
                ext = fmt.lower()
                if fmt == "JPEG":
                    ext = "jpg"  # Используем .jpg для JPEG
                filename = f"{base_name}-{width}w.{ext}"
                srcset_entries.append(f"{filename} {width}w")
                if not smallest_image or width < smallest_image[0]:
                    smallest_image = (width, filename)

        # Определение основного изображения (самого маленького)
        if smallest_image:
            src = smallest_image[1]
        else:
            src = srcset_entries[0].split(" ")[0]

        # Формирование строки srcset с правильным отступом
        srcset_str = ",\n\t".join(srcset_entries)  # Один знак табуляции перед каждым элементом srcset

        # Форматирование HTML-кода согласно заданным требованиям
        # Перед alt, class, loading, sizes, src - два знака табуляции
        # Перед каждым элементом srcset - один знак табуляции
        html_code = f'''<img
\talt="{alt_text}"
\tclass="profile-image"
\t{loading_attr}
\tsizes="{sizes_attr}"
\tsrc="{src}" srcset="
\t{srcset_str}
">'''

        # Обновление поля предпросмотра HTML-кода
        self.text_html_preview.config(state='normal')
        self.text_html_preview.delete(1.0, tk.END)
        self.text_html_preview.insert(tk.END, html_code)
        self.text_html_preview.config(state='disabled')  # Отключение редактирования

    def update_html_preview_after_selection(self):
        """
        Генерирует HTML-код для первого исходного изображения при изменении опций генерации HTML-кода
        или добавления lazy loading.
        """
        if self.generate_html.get() and self.source_image_paths.get():
            first_image_path = self.source_image_paths.get().split(", ")[0]
            self.generate_html_preview_for_first_image(first_image_path)
        else:
            self.clear_html_preview()

    def start_conversion(self):
        """
        Запускает процесс конвертации изображений в отдельном потоке.

        Проверяет, не запущена ли уже конвертация, и есть ли файлы для обработки. Затем запускает
        рабочий поток и обновляет интерфейс.
        """
        if self.conversion_in_progress:
            messagebox.showwarning("Предупреждение", "Конвертация уже запущена.")
            return

        # Проверка наличия файлов для конвертации
        if not self.file_to_item:
            messagebox.showwarning("Предупреждение", "Нет файлов для конвертации.")
            return

        # Установка флага конвертации
        self.conversion_in_progress = True

        # Отключение кнопки конвертации для предотвращения повторных нажатий
        self.btn_convert.config(state='disabled')

        # Очистка статусных меток и HTML-предпросмотра
        self.lbl_conversion_status.config(text="Конвертация началась...")
        if self.generate_html.get():
            self.html_code_full = ""  # Сброс накопленного HTML-кода

        # Запуск рабочего потока для конвертации
        worker = threading.Thread(target=self.convert_images_thread, daemon=True)
        worker.start()

    def convert_images_thread(self):
        """
        Рабочий поток для конвертации изображений.

        Выполняет конвертацию изображений по заданным параметрам, обновляет статус файлов и
        генерирует HTML-код при необходимости.
        """
        source_paths = self.source_image_paths.get().split(", ")
        output_folder = self.output_folder_path.get()
        widths_input = self.widths_string.get()

        # Обработка размеров
        try:
            widths = sorted([int(w.strip()) for w in widths_input.split(",") if w.strip().isdigit()])
            if not widths:
                raise ValueError
        except ValueError:
            self.queue.put(("error", "Укажите корректные целые числа для ширины изображений (через запятую)."))
            self.conversion_in_progress = False
            return

        # Получение выбранных форматов
        selected_formats_list = [fmt for fmt, var in self.selected_formats.items() if var.get()]
        if not selected_formats_list:
            self.queue.put(("error", "Не выбран ни один формат для конвертации."))
            self.conversion_in_progress = False
            return

        generated_files = []  # Список для хранения путей сгенерированных файлов
        html_code_full = ""    # Накопленный HTML-код

        total_files = len(source_paths) * len(widths) * len(selected_formats_list)  # Общее количество файлов для конвертации
        processed_files = 0  # Счётчик обработанных файлов

        for source_path in source_paths:
            try:
                with Image.open(source_path) as img:
                    # Получение имени файла без расширения
                    base_name = os.path.splitext(os.path.basename(source_path))[0]

                    generated_files_current = {}  # Для хранения сгенерированных файлов текущего изображения

                    for width in widths:
                        # Вычисление новой высоты с сохранением пропорций
                        ratio = width / float(img.width)
                        new_height = int(img.height * ratio)

                        # Создание копии исходного изображения нужного размера
                        resized_img = img.resize((width, new_height), Image.LANCZOS)

                        for fmt in selected_formats_list:
                            # Формирование имени выходного файла
                            ext = fmt.lower()
                            if fmt == "JPEG":
                                ext = "jpg"  # Используем .jpg для JPEG
                                fmt_pillow = "JPEG"
                            else:
                                fmt_pillow = fmt  # "PNG" или "WEBP"

                            out_filename = f"{base_name}-{width}w.{ext}"
                            out_path = os.path.join(output_folder, out_filename)

                            # Дополнительные параметры сохранения
                            save_params = {}
                            if fmt_pillow == "JPEG":
                                # Установка качества и оптимизация для JPEG
                                save_params["quality"] = 85
                                save_params["optimize"] = True
                                save_params["progressive"] = True
                            elif fmt_pillow == "WEBP":
                                # Установка качества и метода для WEBP
                                save_params["quality"] = 80
                                save_params["method"] = 6  # Оптимизация (0-6)

                            # Сохранение изображения
                            try:
                                resized_img.save(out_path, fmt_pillow, **save_params)
                                generated_files.append(out_path)
                                print(f"Сохранено: {out_path}")
                                # Обновление статуса в Treeview
                                self.queue.put(("update_status", out_path, "✔"))

                                # Сбор данных для HTML-кода
                                if self.generate_html.get():
                                    if base_name not in generated_files_current:
                                        generated_files_current[base_name] = []
                                    generated_files_current[base_name].append((width, out_filename))

                            except Exception as e:
                                print(f"Ошибка сохранения файла {out_path}: {e}")
                                # Обновление статуса в Treeview при ошибке
                                self.queue.put(("update_status", out_path, "✖"))

                            # Увеличение счётчика обработанных файлов и обновление прогрессбара
                            processed_files += 1
                            self.queue.put(("update_progress", 1))

                    # Генерация HTML-кода для текущего изображения
                    if self.generate_html.get():
                        for base_name, files in generated_files_current.items():
                            # Сортировка файлов по ширине и формату
                            sorted_files = sorted(files, key=lambda x: (x[0], selected_formats_list.index(
                                os.path.splitext(x[1])[1][1:].upper().replace('JPG','JPEG'))))
                            srcset_entries = ",\n\t".join([f"{filename} {width}w" for width, filename in sorted_files])
                            smallest_image = sorted_files[0][1]
                            alt_text = base_name.replace("-", " ")
                            sizes_attr = "(max-width: 480px) 100px, (max-width: 768px) 120px, 120px"
                            loading_attr = 'loading="lazy"' if self.add_lazy_loading.get() else ''

                            # Форматирование HTML-кода согласно заданным требованиям
                            html_code = f'''<img
\talt="{alt_text}"
\tclass="profile-image"
\t{loading_attr}
\tsizes="{sizes_attr}"
\tsrc="{smallest_image}" srcset="
\t{srcset_entries}
">'''
                            html_code_full += html_code + "\n\n"  # Разделение кодов разных изображений пустой строкой

            except Exception as e:
                print(f"Не удалось обработать файл {source_path}: {e}")
                self.queue.put(("error", f"Не удалось обработать файл {source_path}: {e}"))

        # Запись накопленного HTML-кода в файл code.txt, если опция активирована
        if self.generate_html.get() and html_code_full.strip():
            txt_filename = "code.txt"
            txt_path = os.path.join(output_folder, txt_filename)
            try:
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(html_code_full.strip())
                print(f"HTML-код записан в файл: {txt_path}")
                # Обновление статуса "code.txt" в Treeview
                self.queue.put(("update_status", txt_path, "✔"))
            except Exception as e:
                print(f"Ошибка записи HTML-кода в файл: {e}")
                self.queue.put(("error", f"Ошибка записи HTML-кода в файл: {e}"))

        # Обновление общего статуса конвертации
        if generated_files:
            self.queue.put(("conversion_complete", "Конвертация завершена успешно."))
        else:
            self.queue.put(("conversion_complete", "Не было сгенерировано ни одного файла."))

        # Сброс флага конвертации и восстановление кнопки конвертации
        self.conversion_in_progress = False

    def process_queue(self):
        """
        Обрабатывает сообщения из очереди и выполняет соответствующие действия.

        Этот метод вызывается периодически (каждые 100 мс) и обрабатывает обновления статуса файлов,
        прогресса конвертации и ошибок.
        """
        try:
            while True:
                message = self.queue.get_nowait()
                if message[0] == "update_status":
                    _, file_path, status_symbol = message
                    self.update_file_status(file_path, status_symbol)
                elif message[0] == "update_progress":
                    _, increment = message
                    self.update_progress_bar(increment)
                elif message[0] == "error":
                    _, error_msg = message
                    messagebox.showerror("Ошибка", error_msg)
                elif message[0] == "conversion_complete":
                    _, status_msg = message
                    self.lbl_conversion_status.config(text=status_msg)
                    # Включение кнопки конвертации после завершения
                    self.btn_convert.config(state='normal')
        except queue.Empty:
            pass
        finally:
            # Продолжение проверки очереди
            self.master.after(100, self.process_queue)

    def update_file_status(self, file_path, status_symbol):
        """
        Обновляет статус конкретного файла в Treeview.

        :param file_path: Путь к файлу.
        :param status_symbol: Символ статуса ("✔" для успешного, "✖" для неудачного).
        """
        item_id = self.file_to_item.get(file_path)
        if item_id:
            # Обновление существующего элемента
            self.tree_preview.set(item_id, column="Status", value=status_symbol)
        else:
            # Если item_id отсутствует (например, для "code.txt"), добавляем новый элемент
            if os.path.basename(file_path) == "code.txt":
                # Проверка, не было ли уже добавлено "code.txt"
                if not any(self.tree_preview.item(child)["values"][0] == file_path for child in self.tree_preview.get_children()):
                    # Добавление "code.txt" в конец списка
                    new_item = self.tree_preview.insert("", "end", values=(file_path, status_symbol), tags=("evenrow",))
                    self.file_to_item[file_path] = new_item

    def update_progress_bar(self, increment):
        """
        Обновляет прогрессбар при конвертации файлов.

        :param increment: Значение, на которое увеличивается прогрессбар.
        """
        # Если прогрессбар ещё не создан, создаём его
        if not hasattr(self, 'progress_bar'):
            frame_convert = self.btn_convert.master
            self.progress_bar = ttk.Progressbar(frame_convert, orient='horizontal', mode='determinate', length=300)
            self.progress_bar.pack(side="left", padx=10, pady=2)
            self.progress_bar['value'] = 0
            # Установка максимального значения прогрессбара как общее количество файлов
            total_files = len(self.file_to_item) - (1 if self.generate_html.get() else 0)  # Исключаем code.txt
            self.progress_bar['maximum'] = total_files

        # Увеличение значения прогрессбара
        self.progress_bar['value'] += increment

    def update_html_preview(self, html_code):
        """
        Обновляет поле предпросмотра HTML-кода.

        :param html_code: Строка с HTML-кодом для отображения.
        """
        self.text_html_preview.config(state='normal')  # Включение редактирования
        self.text_html_preview.delete(1.0, tk.END)    # Очистка поля
        self.text_html_preview.insert(tk.END, html_code)  # Вставка нового кода
        self.text_html_preview.config(state='disabled')  # Отключение редактирования

    def clear_html_preview(self):
        """
        Очищает поле предпросмотра HTML-кода.
        """
        self.text_html_preview.config(state='normal')  # Включение редактирования
        self.text_html_preview.delete(1.0, tk.END)    # Очистка поля
        self.text_html_preview.config(state='disabled')  # Отключение редактирования

def main():
    """
    Основная функция для запуска приложения.
    """
    root = tk.Tk()
    app = ImageConverterApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
