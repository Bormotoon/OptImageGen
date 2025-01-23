import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image
import threading
import queue

class ImageConverterApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Image Converter")
        self.master.geometry("900x700")  # Увеличиваем ширину для дополнительного столбца

        # Переменные для хранения путей и настроек
        self.source_image_paths = tk.StringVar()
        self.output_folder_path = tk.StringVar()
        self.widths_string = tk.StringVar(value="400,800,1200")  # Значения по умолчанию
        self.selected_formats = {
            "JPEG": tk.BooleanVar(value=True),
            "PNG": tk.BooleanVar(value=True),
            "WEBP": tk.BooleanVar(value=True)
        }

        # Словарь для сопоставления путей файлов с ID элементов Treeview
        self.file_to_item = {}

        # Очередь для получения сообщений от рабочего потока
        self.queue = queue.Queue()

        # Флаг для предотвращения повторного запуска конвертации
        self.conversion_in_progress = False

        # Создаём интерфейс
        self.create_widgets()

        # Запускаем периодическую проверку очереди
        self.master.after(100, self.process_queue)

    def create_widgets(self):
        # ========== Выбор исходного файла ==========
        frame_source = tk.LabelFrame(self.master, text="Шаг 1: Исходное изображение")
        frame_source.pack(fill="x", padx=10, pady=5, ipady=5)

        lbl_source = tk.Label(frame_source, text="Файлы:")
        lbl_source.pack(side="left", padx=5, pady=5)

        entry_source = tk.Entry(frame_source, textvariable=self.source_image_paths, width=50, state='readonly')
        entry_source.pack(side="left", padx=5, pady=5)

        btn_browse_source = tk.Button(frame_source, text="Обзор...", command=self.browse_source_image)
        btn_browse_source.pack(side="left", padx=5, pady=5)

        # ========== Выбор папки для сохранения ==========
        frame_output = tk.LabelFrame(self.master, text="Шаг 2: Папка для сохранения результатов")
        frame_output.pack(fill="x", padx=10, pady=5, ipady=5)

        lbl_output_folder = tk.Label(frame_output, text="Папка:")
        lbl_output_folder.pack(side="left", padx=5, pady=5)

        entry_output_folder = tk.Entry(frame_output, textvariable=self.output_folder_path, width=50, state='readonly')
        entry_output_folder.pack(side="left", padx=5, pady=5)

        btn_browse_output = tk.Button(frame_output, text="Обзор...", command=self.browse_output_folder)
        btn_browse_output.pack(side="left", padx=5, pady=5)

        # ========== Форматы ==========
        frame_formats = tk.LabelFrame(self.master, text="Шаг 3: Выберите форматы")
        frame_formats.pack(fill="x", padx=10, pady=5, ipady=5)

        for fmt in self.selected_formats:
            cb = tk.Checkbutton(
                frame_formats,
                text=fmt,
                variable=self.selected_formats[fmt],
                command=self.update_preview
            )
            cb.pack(side="left", padx=5, pady=5)

        # ========== Размеры (ширины) ==========
        frame_sizes = tk.LabelFrame(self.master, text="Шаг 4: Укажите нужные ширины (через запятую)")
        frame_sizes.pack(fill="x", padx=10, pady=5, ipady=5)

        lbl_sizes = tk.Label(frame_sizes, text="Ширины:")
        lbl_sizes.pack(side="left", padx=5, pady=5)

        entry_sizes = tk.Entry(frame_sizes, textvariable=self.widths_string, width=30)
        entry_sizes.pack(side="left", padx=5, pady=5)
        entry_sizes.bind("<KeyRelease>", lambda event: self.update_preview())

        # ========== Кнопка конвертации и статус ==========
        frame_convert = tk.Frame(self.master)
        frame_convert.pack(pady=10)

        self.btn_convert = tk.Button(frame_convert, text="Конвертировать!", command=self.start_conversion, bg="#4CAF50", fg="#ffffff")
        self.btn_convert.pack(side="left", padx=5, pady=5)

        # Метка для отображения общего статуса конвертации
        self.lbl_conversion_status = tk.Label(frame_convert, text="", font=("Arial", 12))
        self.lbl_conversion_status.pack(side="left", padx=10, pady=5)

        # ========== Поле предпросмотра ==========
        frame_preview = tk.LabelFrame(self.master, text="Предпросмотр: Предполагаемые файлы")
        frame_preview.pack(fill="both", expand=True, padx=10, pady=5, ipady=5)

        # Настройка стилей для чередования цветов
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#FFFFFF", foreground="black", rowheight=25, fieldbackground="#FFFFFF")
        style.map('Treeview', background=[('selected', '#347083')])

        style.configure("OddRow", background="#f0f0f0")
        style.configure("EvenRow", background="#ffffff")

        # Создаём Treeview и Scrollbar
        columns = ("File Path", "Status")
        self.tree_preview = ttk.Treeview(frame_preview, columns=columns, show='headings', selectmode='browse')
        self.tree_preview.heading("File Path", text="Путь к файлу")
        self.tree_preview.heading("Status", text="Статус")
        self.tree_preview.column("File Path", anchor="w", width=700)
        self.tree_preview.column("Status", anchor="center", width=100)

        scrollbar = ttk.Scrollbar(frame_preview, orient="vertical", command=self.tree_preview.yview)
        self.tree_preview.configure(yscroll=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.tree_preview.pack(fill="both", expand=True)

    def browse_source_image(self):
        """Выбор одного или нескольких исходных файлов и установка папки экспорта по умолчанию"""
        file_paths = filedialog.askopenfilenames(
            title="Выберите исходные изображения",
            filetypes=[("Все файлы изображений", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif"),
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

    def browse_output_folder(self):
        """Выбор папки для сохранения результатов"""
        folder_path = filedialog.askdirectory(title="Выберите папку для сохранения")
        if folder_path:
            self.output_folder_path.set(folder_path)
            self.update_preview()

    def update_preview(self):
        """Обновление поля предпросмотра с предполагаемыми файлами"""
        self.tree_preview.delete(*self.tree_preview.get_children())  # Очистка списка
        self.file_to_item.clear()  # Очистка сопоставлений

        source_paths = self.source_image_paths.get().split(", ")
        output_folder = self.output_folder_path.get()
        widths_input = self.widths_string.get()
        selected_formats_list = [fmt for fmt, var in self.selected_formats.items() if var.get()]

        # Проверяем наличие необходимых данных
        if not source_paths or not any(os.path.isfile(path) for path in source_paths):
            return  # Ничего не делаем, если нет исходных файлов

        if not selected_formats_list:
            return  # Ничего не делаем, если нет выбранных форматов

        # Обрабатываем размеры
        try:
            widths = [int(w.strip()) for w in widths_input.split(",") if w.strip().isdigit()]
            if not widths:
                raise ValueError
        except ValueError:
            return  # Ничего не делаем, если размеры некорректны

        # Если папка не указана, предполагаем папку исходного файла
        if not output_folder:
            output_folder = os.path.dirname(source_paths[0])

        # Проверяем, существует ли папка
        if not os.path.isdir(output_folder):
            return  # Ничего не делаем, если папка не существует

        # Генерируем список предполагаемых файлов
        for source_path in source_paths:
            base_name = os.path.splitext(os.path.basename(source_path))[0]
            for width in widths:
                for fmt in selected_formats_list:
                    ext = fmt.lower()
                    if fmt == "JPEG":
                        ext = "jpg"  # Используем .jpg для JPEG
                    out_filename = f"{base_name}-{width}w.{ext}"
                    out_path = os.path.join(output_folder, out_filename)
                    # Определяем тег для чередования цветов
                    row_tag = "evenrow" if len(self.tree_preview.get_children()) % 2 == 0 else "oddrow"
                    item_id = self.tree_preview.insert("", "end", values=(out_path, ""), tags=(row_tag,))
                    self.file_to_item[out_path] = item_id

        # Применяем стили для чередования цветов
        self.tree_preview.tag_configure("evenrow", background="#ffffff")
        self.tree_preview.tag_configure("oddrow", background="#f0f0f0")

    def start_conversion(self):
        """Запуск конвертации в отдельном потоке"""
        if self.conversion_in_progress:
            messagebox.showwarning("Предупреждение", "Конвертация уже запущена.")
            return

        # Проверяем, есть ли файлы для конвертации
        if not self.file_to_item:
            messagebox.showwarning("Предупреждение", "Нет файлов для конвертации.")
            return

        # Устанавливаем флаг
        self.conversion_in_progress = True

        # Отключаем кнопку конвертации, чтобы предотвратить повторные нажатия
        self.btn_convert.config(state='disabled')

        # Очищаем статусные метки
        self.lbl_conversion_status.config(text="")

        # Запускаем рабочий поток
        worker = threading.Thread(target=self.convert_images_thread, daemon=True)
        worker.start()

    def convert_images_thread(self):
        """Рабочий поток для конвертации изображений"""
        source_paths = self.source_image_paths.get().split(", ")
        output_folder = self.output_folder_path.get()
        widths_input = self.widths_string.get()

        # Обрабатываем размеры
        try:
            widths = [int(w.strip()) for w in widths_input.split(",") if w.strip().isdigit()]
            if not widths:
                raise ValueError
        except ValueError:
            self.queue.put(("error", "Укажите корректные целые числа для ширины изображений (через запятую)."))
            self.conversion_in_progress = False
            return

        # Получаем выбранные форматы
        selected_formats_list = [fmt for fmt, var in self.selected_formats.items() if var.get()]
        if not selected_formats_list:
            self.queue.put(("error", "Не выбран ни один формат для конвертации."))
            self.conversion_in_progress = False
            return

        generated_files = []  # Список для хранения путей сгенерированных файлов

        for source_path in source_paths:
            try:
                with Image.open(source_path) as img:
                    # Получаем имя файла без расширения
                    base_name = os.path.splitext(os.path.basename(source_path))[0]

                    for width in widths:
                        # Вычисляем новую высоту (с сохранением пропорций)
                        ratio = width / float(img.width)
                        new_height = int(img.height * ratio)

                        # Создаём копию исходного изображения нужного размера
                        resized_img = img.resize((width, new_height), Image.LANCZOS)

                        for fmt in selected_formats_list:
                            # Формируем имя выходного файла
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
                                # Устанавливаем качество
                                save_params["quality"] = 85
                                save_params["optimize"] = True
                                save_params["progressive"] = True
                            elif fmt_pillow == "WEBP":
                                save_params["quality"] = 80
                                save_params["method"] = 6  # Оптимизация (0-6)

                            # Сохранение
                            try:
                                resized_img.save(out_path, fmt_pillow, **save_params)
                                generated_files.append(out_path)
                                print(f"Сохранено: {out_path}")
                                # Отправляем сообщение об успешной конвертации
                                self.queue.put(("update_status", out_path, "✔"))
                            except Exception as e:
                                print(f"Ошибка сохранения файла {out_path}: {e}")
                                # Отправляем сообщение об ошибке конвертации
                                self.queue.put(("update_status", out_path, "✖"))

            except Exception as e:
                print(f"Не удалось обработать файл {source_path}: {e}")
                self.queue.put(("error", f"Не удалось обработать файл {source_path}: {e}"))

        if generated_files:
            self.queue.put(("conversion_complete", "Конвертация завершена успешно."))
        else:
            self.queue.put(("conversion_complete", "Не было сгенерировано ни одного файла."))

        # Сбрасываем флаг и восстанавливаем кнопку конвертации
        self.conversion_in_progress = False

    def process_queue(self):
        """Обработка сообщений из очереди"""
        try:
            while True:
                message = self.queue.get_nowait()
                if message[0] == "update_status":
                    _, file_path, status_symbol = message
                    self.update_file_status(file_path, status_symbol)
                elif message[0] == "error":
                    _, error_msg = message
                    messagebox.showerror("Ошибка", error_msg)
                elif message[0] == "conversion_complete":
                    _, status_msg = message
                    self.lbl_conversion_status.config(text=status_msg)
                    # Включаем кнопку конвертации
                    self.btn_convert.config(state='normal')
        except queue.Empty:
            pass
        finally:
            # Продолжаем проверку очереди
            self.master.after(100, self.process_queue)

    def update_file_status(self, file_path, status_symbol):
        """Обновление статуса конкретного файла в Treeview"""
        item_id = self.file_to_item.get(file_path)
        if item_id:
            self.tree_preview.set(item_id, column="Status", value=status_symbol)

def main():
    root = tk.Tk()
    app = ImageConverterApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
