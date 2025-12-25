# Проект: пайплайны подготовки данных и обучения модели (Яндекс Недвижимость)

Репозиторий содержит решение проекта из трех этапов:
1) сбор датасета из таблиц `buildings` и `flats` с помощью Airflow  
2) очистка датасета и сохранение очищенной версии в БД с помощью Airflow  
3) обучение базовой модели регрессии и выгрузка модели в S3 с помощью DVC

## S3 bucket
Для проверки модели и DVC-remote используется бакет:

**s3-student-mle-20251010-5a382f9c3d**

---

## Часть 1. Airflow (ETL и очистка)

### Структура
Все материалы Airflow находятся в папке:

`part1_airflow/`

- DAG-файлы: `part1_airflow/dags/`
- Плагины/утилиты: `part1_airflow/plugins/`
- Ноутбуки: `part1_airflow/notebooks/`

### Этап 1. Сбор датасета
**DAG файл:**  
`part1_airflow/dags/real_estate_dataset_etl.py`

**DAG id:**  
`real_estate_dataset_etl`

**Назначение:**  
Создает таблицу с сырым датасетом и загружает данные, объединяя `buildings` и `flats` в единый набор признаков.

**Результат:**  
Таблица в БД: `public.real_estate_dataset_raw`

### Этап 2. Очистка данных
**DAG файл:**  
`part1_airflow/dags/real_estate_dataset_clean.py`

**DAG id:**  
`real_estate_dataset_clean`

**Назначение:**  
Загружает сырые данные, применяет функции очистки (пропуски, дубликаты, выбросы/аномалии) и сохраняет очищенный датасет.

**Функции очистки (Python):**  
`part1_airflow/plugins/cleaning_utils.py`  
(основная функция: `clean_dataset`)

**Ноутбук с анализом и описанием правил очистки:**  
`part1_airflow/notebooks/02_data_cleaning.ipynb`

**Результат:**  
Таблица в БД: `public.real_estate_dataset_clean`

---

## Часть 2. DVC (обучение модели и выгрузка в S3)

### Структура
Все материалы DVC находятся в папке:

`part2_dvc/`

- Скрипты пайплайна: `part2_dvc/scripts/`
- Данные: `part2_dvc/data/`
- Модели: `part2_dvc/models/`
- Метрики: `part2_dvc/cv_results/`

### Конфигурация DVC
- `part2_dvc/dvc.yaml` — описание стадий пайплайна
- `part2_dvc/params.yaml` — параметры (таблица-источник, гиперпараметры модели, настройки S3)
- `part2_dvc/dvc.lock` — lock-файл с зафиксированными зависимостями и артефактами

### Скрипты DVC-пайплайна
- `part2_dvc/scripts/extract_from_db.py` — выгрузка очищенного датасета из Postgres в CSV  
- `part2_dvc/scripts/train.py` — обучение модели регрессии (CatBoostRegressor + preprocessing) и сохранение `models/model.pkl`  
- `part2_dvc/scripts/evaluate.py` — расчет метрик и сохранение `cv_results/metrics.json`  
- `part2_dvc/scripts/upload_model.py` — загрузка модели в S3 и создание маркера `cv_results/upload_done.txt`

## Как запустить

Заполните .env_template и переименуйте в .env

```bash
# экспортируйте перепенные из .env
export $(grep -v '^#' .env | xargs)
```
Требование проекта: `docker-compose.yaml` находится в корне репозитория, а код Airflow лежит в `part1_airflow/`.  
Папки `dags/` и `plugins/` должны монтироваться в контейнер Airflow.
```bash
# обновление локального индекса пакетов
sudo apt-get update
# установка расширения для виртуального пространства
sudo apt-get install python3.10-venv
# создание виртуального пространства
python3.10 -m venv .venv_project_name

source .venv_project_name/bin/activate

pip install -r requirements.txt

# Скачайте официальные образы сервисов Airflow
curl -LfO https://airflow.apache.org/docs/apache-airflow/2.7.3/docker-compose.yaml
```


Запуск из корня репозитория:

```bash
# Первый запуск
docker compose up airflow-init

# Второй командой разработчики Airflow советуют очистить возможный кэш, который появился в результате первого шага. Если этого не сделать, то могут возникнуть непредвиденные ошибки.
docker compose down --volumes --remove-orphans 

# Запуск
docker compose up --build
```

DVC:
```bash
dvc init --subdir
dvc remote add -d storage s3://<ВАШ_BUCKET>/dvc-cache
dvc remote modify storage endpointurl https://storage.yandexcloud.net









