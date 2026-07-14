# Airflow + DVC: подготовка данных и обучение модели недвижимости

[![Quality checks](https://github.com/matevosovp/Airflow-project/actions/workflows/quality.yml/badge.svg)](https://github.com/matevosovp/Airflow-project/actions/workflows/quality.yml)

End-to-end учебный MLOps-проект для оценки стоимости недвижимости: данные собираются и очищаются в Airflow, а обучение, оценка и публикация модели оформлены как воспроизводимый DVC-пайплайн.

## Коротко о проекте

- два связанных Airflow DAG-а: ETL сырого датасета и очистка данных;
- data-aware запуск второго DAG-а после обновления исходного набора;
- общий volume для передачи промежуточных данных между Celery workers;
- DVC-пайплайн из четырёх стадий: `extract → train → evaluate → upload`;
- CatBoost-регрессия с версионированием параметров, модели и метрик;
- S3-compatible хранилище для публикации model artifact;
- unit-тесты очистки данных и автоматические проверки GitHub Actions.

## Архитектура

```text
PostgreSQL: buildings + flats
            │
            ▼
Airflow DAG: real_estate_dataset_etl
            │
            ▼
public.real_estate_dataset_raw
            │  Dataset event
            ▼
Airflow DAG: real_estate_dataset_clean
            │
            ▼
public.real_estate_dataset_clean
            │
            ▼
DVC: extract → train → evaluate → upload
            │         │          │
            │         │          └── S3 model artifact
            │         └── cv_results/metrics.json
            └── models/model.pkl
```

## Airflow: подготовка данных

### DAG 1 — сбор датасета

Файл: [`01_real_estate_dataset_etl.py`](part1_airflow/dags/01_real_estate_dataset_etl.py)  
DAG ID: `real_estate_dataset_etl`

DAG объединяет таблицы `public.flats` и `public.buildings`, нормализует булевы признаки, загружает результат в `public.real_estate_dataset_raw` и публикует Airflow Dataset event.

### DAG 2 — очистка

Файл: [`02_real_estate_dataset_clean.py`](part1_airflow/dags/02_real_estate_dataset_clean.py)  
DAG ID: `real_estate_dataset_clean`

DAG запускается после обновления сырого датасета, применяет [`clean_dataset`](part1_airflow/plugins/cleaning_utils.py) и записывает результат в `public.real_estate_dataset_clean`.

Правила очистки включают:

- удаление дубликатов по `flat_id`;
- заполнение пропусков в булевых и числовых признаках;
- удаление объектов с невозможными площадями, ценой или числом комнат;
- ограничение выбросов по IQR.

Промежуточные pickle-файлы хранятся в общем каталоге `/opt/airflow/data`, который смонтирован во все worker-контейнеры. Telegram-уведомления опциональны и не ломают DAG при отсутствии токена.

## DVC: обучение и публикация модели

Конфигурация находится в каталоге [`part2_dvc`](part2_dvc):

| Стадия | Назначение | Основной артефакт |
|---|---|---|
| `extract` | выгрузка очищенного датасета из PostgreSQL | `data/processed/dataset.csv` |
| `train` | preprocessing и обучение CatBoostRegressor | `models/model.pkl` |
| `evaluate` | расчёт RMSE, MAE и R² | `cv_results/metrics.json` |
| `upload` | загрузка модели в S3-compatible storage | `cv_results/upload_done.txt` |

Числовые, бинарные и категориальные признаки обрабатываются отдельными ветками `ColumnTransformer`; идентификаторы объектов исключаются из обучения.

Последний сохранённый запуск содержит:

| Метрика | Значение |
|---|---:|
| R² | 0.8480 |
| RMSE | 2 422 847.95 |
| MAE | 1 844 609.84 |
| Объектов | 119 522 |

Метрики относятся к зафиксированному DVC-run. После изменения preprocessing выполните `dvc repro`, чтобы пересчитать модель и связанные артефакты.

## Быстрый старт Airflow

Требуются Docker и Docker Compose.

```bash
git clone https://github.com/matevosovp/Airflow-project.git
cd Airflow-project

cp .env.example .env
# заполните подключения к PostgreSQL и при необходимости Telegram

docker compose up airflow-init
docker compose up --build -d
```

Интерфейс Airflow будет доступен на `http://localhost:8080`.

Подключение `pg_conn` формируется из `DB_SOURCE_*` переменных в `.env`. Файл `.env` исключён из Git и не должен содержать реальные секреты в истории репозитория.

## Запуск DVC-пайплайна

```bash
cd part2_dvc
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

set -a
source ../.env
set +a

# укажите свой bucket в params.yaml
dvc repro
dvc metrics show
```

Для S3-compatible storage используются `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` и endpoint из [`params.yaml`](part2_dvc/params.yaml). Значение bucket в репозитории является безопасным placeholder.

## Структура репозитория

```text
.
├── part1_airflow/
│   ├── dags/                 # ETL и cleaning DAG-и
│   ├── plugins/              # SQL, очистка, config, уведомления
│   ├── notebooks/            # анализ правил очистки
│   └── requirements.txt
├── part2_dvc/
│   ├── scripts/              # extract, train, evaluate, upload
│   ├── dvc.yaml
│   ├── dvc.lock
│   ├── params.yaml
│   └── requirements.txt
├── tests/                    # unit-тесты cleaning logic
├── docker-compose.yaml
├── Dockerfile
└── .env.example
```

## Проверка качества

Локально можно выполнить:

```bash
pip install numpy==1.26.2 pandas==2.1.3 pytest==8.3.4
pytest -q
python -m compileall -q part1_airflow/dags part1_airflow/plugins part2_dvc/scripts
docker compose config --quiet
```

## Ограничения

- исходные таблицы PostgreSQL и S3-хранилище предоставляются отдельно;
- Docker Compose предназначен для локальной демонстрации, а не production-развёртывания;
- сохранённые метрики необходимо пересчитывать после изменений данных, параметров или preprocessing;
- batch-очистка использует промежуточные файлы; для больших production-нагрузок разумнее перенести трансформации в SQL/Spark или объектное хранилище.
