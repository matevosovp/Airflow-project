# Airflow + DVC: MLOps-пайплайн для недвижимости

[![Quality checks](https://github.com/matevosovp/Airflow-project/actions/workflows/quality.yml/badge.svg)](https://github.com/matevosovp/Airflow-project/actions/workflows/quality.yml)

End-to-end проект для подготовки данных и обучения модели стоимости недвижимости. Airflow строит проверенные витрины в PostgreSQL, а DVC воспроизводит выгрузку, обучение CatBoost, оценку и публикацию модели.

## Что демонстрирует проект

- два связанных Airflow DAG-а с data-aware scheduling;
- SQL pushdown без переноса всего датасета в память worker-а;
- staging tables, data-quality gates и атомарная замена витрин;
- явный контракт из 18 колонок вместо хрупкого `SELECT *`;
- потоковая выгрузка PostgreSQL → CSV;
- воспроизводимый DVC-граф `extract → train → evaluate → upload`;
- preprocessing без target leakage и единая логика train/validation split;
- проверка загруженного S3-артефакта;
- unit- и architecture-тесты в GitHub Actions.

## Архитектура

```text
PostgreSQL: public.flats + public.buildings
                         │
                         ▼
Airflow: real_estate_dataset_etl
  source checks → staging build → quality gates → atomic swap
                         │ Dataset event
                         ▼
public.real_estate_dataset_raw
                         │
                         ▼
Airflow: real_estate_dataset_clean
  validation → SQL cleaning → quality gates → atomic swap
                         │ Dataset event
                         ▼
public.real_estate_dataset_clean
                         │
                         ▼
DVC: extract → train → evaluate → upload
       CSV       model      metrics      S3
```

Оба DAG-а ограничены одним активным запуском. PostgreSQL DDL выполняется в транзакции: если создание staging-таблицы или проверка качества завершается ошибкой, существующая рабочая витрина остаётся доступной.

## Airflow

### 1. Сбор сырой витрины

Файл: [`01_real_estate_dataset_etl.py`](part1_airflow/dags/01_real_estate_dataset_etl.py)  
SQL: [`real_estate_sql.py`](part1_airflow/plugins/real_estate_sql.py)

DAG:

1. проверяет наличие `public.flats` и `public.buildings`;
2. останавливается, если есть квартиры без соответствующего здания;
3. строит staging-таблицу одним явным `SELECT`;
4. проверяет непустой результат, `NULL` и дубликаты `flat_id`;
5. создаёт уникальный индекс и атомарно заменяет `public.real_estate_dataset_raw`;
6. публикует Airflow Dataset event только после успешного commit.

Булевы признаки нормализуются через `COALESCE` непосредственно при чтении — отдельный full-table `UPDATE` не нужен.

### 2. Очистка витрины

Файл: [`02_real_estate_dataset_clean.py`](part1_airflow/dags/02_real_estate_dataset_clean.py)  
SQL: [`real_estate_clean_sql.py`](part1_airflow/plugins/real_estate_clean_sql.py)

Второй DAG автоматически запускается после обновления raw dataset. Очистка выполняется set-based SQL в PostgreSQL и не использует XCom, pickle-файлы или общий диск между Celery workers.

Основные правила:

- идентификаторы и target `price` не импутируются;
- строки без положительной цены или числа комнат исключаются;
- пропуски числовых признаков заполняются медианами, тип здания — модой;
- булевы признаки получают безопасное значение `FALSE`;
- проверяются отношения `kitchen_area ≤ total_area`, `living_area ≤ total_area` и `floor ≤ floors_total`;
- выбросы цены и площадей ограничиваются границами IQR;
- итоговая таблица должна быть непустой, уникальной по `flat_id` и пройти бизнес-проверки.

[`cleaning_utils.py`](part1_airflow/plugins/cleaning_utils.py) содержит эквивалентную pandas-реализацию правил для исследовательских ноутбуков и unit-тестов.

Telegram-уведомления опциональны: отсутствие токена не ломает успешный pipeline, а ошибка отправки логируется отдельно.

## DVC

Конфигурация находится в каталоге [`part2_dvc`](part2_dvc).

| Стадия | Что делает | Артефакт |
|---|---|---|
| `extract` | валидирует имя таблицы и потоково выгружает явный набор колонок | `data/processed/dataset.csv` |
| `train` | исключает ID, кодирует категории, обучает CatBoostRegressor | `models/model.pkl` |
| `evaluate` | повторяет тот же deterministic split и считает RMSE, MAE, R² | `cv_results/metrics.json` |
| `upload` | загружает модель и сверяет размер объекта через `head_object` | `cv_results/upload_done.txt` |

URL PostgreSQL создаётся через `SQLAlchemy.URL.create`, поэтому специальные символы в credentials кодируются корректно. CSV сначала записывается во временный файл и заменяет предыдущий результат только после успешной выгрузки.

Категориальные признаки обрабатываются `OneHotEncoder(handle_unknown="ignore")`. Target encoding удалён, поскольку его применение ко всему train split до обучения создавало риск утечки целевой переменной.

## Быстрый старт Airflow

Требуются Docker и Docker Compose.

```bash
git clone https://github.com/matevosovp/Airflow-project.git
cd Airflow-project
cp .env.example .env
```

Заполните `DB_SOURCE_*` в `.env`. Затем:

```bash
docker compose up airflow-init
docker compose up --build -d
```

Airflow UI: [http://localhost:8080](http://localhost:8080). Локальные credentials по умолчанию: `airflow / airflow`.

Подключение `pg_conn` создаётся из `DB_SOURCE_*`. Секреты хранятся только в `.env), который исключён из Git.

## Запуск DVC

```bash
cd part2_dvc
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

set -a
source ../.env
set +a

dvc repro evaluate
dvc metrics show
```

Экстрактор сначала использует `DB_DESTINATION_*`, затем `DB_SOURCE_*`, затем стандартные `PG*` переменные. Если Airflow и DVC работают с одной базой, секцию `DB_DESTINATION_*` можно оставить пустой.

Для публикации задайте bucket в [`params.yaml`](part2_dvc/params.yaml), экспортируйте `AWS_ACCESS_KEY_ID` и `AWS_SECRET_ACCESS_KEY`, затем выполните:

```bash
dvc repro upload
```

Сохранённые ранее модель, метрики и `dvc.lock` относятся к последнему воспроизведённому запуску. После изменения SQL или preprocessing их необходимо обновить командой `dvc repro`; старые числа не выдаются за метрики текущего кода.

## Структура

```text
.
├── part1_airflow/
│   ├── dags/                  # raw и clean DAG-и
│   ├── plugins/               # SQL, config, cleaning reference, notifications
│   └── requirements.txt       # минимальные Airflow runtime dependencies
├── part2_dvc/
│   ├── scripts/               # extract, shared helpers, train, evaluate, upload
│   ├── dvc.yaml
│   ├── dvc.lock
│   ├── params.yaml
│   └── requirements.txt
├── tests/                     # unit- и architecture-тесты
├── .github/workflows/
├── docker-compose.yaml
├── Dockerfile
└── .env.example
```

## Проверка качества

```bash
pip install numpy==1.26.2 pandas==2.1.3 pytest==8.3.4 PyYAML==6.0.1
pytest -q
python -m compileall -q part1_airflow/dags part1_airflow/plugins part2_dvc/scripts
docker compose config --quiet
```

GitHub Actions выполняет те же проверки на каждом push и pull request. Architecture-тесты отдельно фиксируют ключевые инварианты: отсутствие `SELECT *`, раннего удаления рабочей таблицы, shared pickle-файлов и target encoder.

## Ограничения

- исходные таблицы PostgreSQL и S3-compatible storage предоставляются отдельно;
- текущая стратегия — полная batch-пересборка; для очень больших таблиц стоит перейти к инкрементальной загрузке;
- локальный Docker Compose не является production-конфигурацией;
- SQL-проверки покрыты статическими invariants; полноценный integration-тест требует тестовой PostgreSQL со схемой исходных данных.
