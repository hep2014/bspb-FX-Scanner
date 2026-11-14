# Данные и воспроизводимость

Срез проекта — 14.11.2026. Снимок `data/snapshot/` содержит только входы для расчётов. `data/SHA256SUMS` фиксирует байты этих файлов. Строки CSV считаются без заголовка.

| Вход | Строк | Период, единица и назначение |
| --- | ---: | --- |
| `snapshot/market/fx_spot_daily.csv` | 5 814 | CNY, USD и EUR, даты действия 10.01.2019–12.11.2026. `rub_per_unit = rate_original / nominal`. Официальные курсы Банка России для HedgeLab. [Динамика курсов](https://www.cbr.ru/currency_base/dynamics/) |
| `snapshot/market/rub_interest_rates.parquet` | 3 918 | RUONIA и ключевая ставка, 2019–2026, процент годовых. Контекст ликвидности. [RUONIA](https://www.cbr.ru/hd_base/ruonia/) · [Ключевая ставка](https://www.cbr.ru/hd_base/KeyRate/) |
| `snapshot/economics/foreign_trade_currency_structure.csv` | 5 604 | Валютные доли товаров и услуг до августа 2026, проценты. Отдельный ряд ФОБ товаров до сентября 2026, млн USD. Поля `frequency` и `indicator` задают разрез. [Внешний сектор](https://www.cbr.ru/statistics/macro_itm/external_sector/etg/) |
| `snapshot/economics/fx_derivatives_market.csv` | 3 122 | Оборот, число договоров, открытый номинал и межбанковский среднедневной оборот. Группировать по `measure_type`, `participant_scope` и `unit`. [Финансовые рынки](https://www.cbr.ru/statistics/finr/) · [Обзор ПФИ](https://www.cbr.ru/Collection/Collection/File/62422/derivatives_market_2026.pdf) |
| `snapshot/source_reconciliation.csv` | 696 | Сверенные ячейки кейса с официальными рядами. Поля `sheet`, `cell`, `date`, `indicator` и сравниваемые значения. |
| `reference/bop_inputs.csv` | 6 | Товары и услуги, млн USD. Точные ячейки табл. 1.1 с периодом и идентификатором источника. [Бюллетень Банка России](https://www.cbr.ru/Collection/Collection/File/62500/Bbs2610r.pdf) |
| `reference/banking_competitor_benchmark.csv` | 250 | 25 полей на канал. Каждое поле содержит статус, дату среза и связь с [реестром первоисточников](reference/source_register.csv). |

Ряды Банка России содержат прямые URL и SHA-256 исходных публикаций в полях `source`, `source_sha256`. Оборот, позиция и число сделок имеют разные единицы. Валюта платежа и валюта ценовой индексации могут различаться. [Условия цитирования ЦБ](https://www.cbr.ru/user_agreement/)

## Договорные и биржевые материалы

В репозитории есть три проверенные короткие обезличенные выдержки в `configs/court_examples.csv` и проверочные смещения CUAD в `configs/cuad_review.csv`. Английский корпус берётся из официального CUAD v1, The Atticus Project, CC BY 4.0. Используемый ZIP проверяется по MD5 `c38f490a984420b8a62600db401fafd5`. Включение полных договоров в другую публикацию требует отдельной проверки персональных данных и прав. Вход для эксперимента передаётся через `--cuad`, результаты содержат агрегаты, статусы и идентификаторы. [CUAD](https://zenodo.org/records/4595826) · [Лицензия](https://creativecommons.org/licenses/by/4.0/)

Для проверки биржевого канала используются карточки контрактов MOEX, спецификации, тарифы и методика клиринга. Исторические котировки MOEX и денежные снимки биржи в Git не входят. Если они нужны для отдельной проверки, используйте авторизованный доступ к ISS либо поставщика биржевой информации. После получения прав на нужный вид использования можно выполнить `python -m data_pipeline collect --source moex` и `python -m data_pipeline process --all` для локальной обработки. Это создаёт рабочие файлы в `data/raw/` и `data/processed/`, не меняя `data/snapshot/`. Границы использования MOEX проверяются по действующим правилам. [MOEX ISS](https://www.moex.com/a2920) · [Правила использования](https://www.moex.com/ru/documents/7064)

Исследовательские эксперименты по умолчанию используют закреплённый снимок. Команды загрузки рыночных рядов нужны для расширения исследования, поскольку поздние публикации могут пересматривать историю.
