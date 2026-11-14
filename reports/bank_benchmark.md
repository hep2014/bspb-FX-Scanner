# Корпоративный FX в России — 8 банков, БСПБ и MOEX

Срез на 14.11.2026. В выборку включены семь системно значимых банков с предложениями корпоративного FX и Уралсиб как сопоставимый по обслуживанию ВЭД. БСПБ — база сравнения. MOEX — отдельный канал с брокерским подключением юрлица. [REG](https://www.cbr.ru/banking_sector/credit/SystemBanks.html), [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/)

Все 250 основных полей заполнены свидетельством или статусом. 149 — подтверждено, 74 — не раскрыто, 25 — требуется уточнение, 2 — недоступно по опубликованным условиям. Отдельная проверка CNY NDF БСПБ дана ниже. Публичный продукт и исполнимая сделка имеют разные подтверждения. Статус подтверждает только явно указанный факт, например срок отдельного свопа, а остальные неизвестные условия описаны в строке. Отсутствие значения на витрине не позволяет утверждать, что инструмент отсутствует.

| Канал | Конверсия | FWD | NDF | FX swap | Опцион | Фьючерсы через брокера | Основание включения |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | --- |
| Сбер | ✓ | ✓ | н/р | ✓ | ✓ | ✓ | Системно значимый банк, сравнение цифрового ВЭД и массовых каналов. |
| ВТБ | ✓ | ✓ | уточнить | ✓ | ✓ | ✓ | Системно значимый банк, эталон структурирования и сопровождения крупных компаний. |
| Альфа-Банк | ✓ | ✓ | н/р | ✓ | ✓ | уточнить | Системно значимый банк, сильный прямой аналог по CNY для МСБ и электронному FX. |
| Газпромбанк | ✓ | ✓ | н/р | н/р | н/р | ✓ | Системно значимый банк с крупным корпоративным дилингом и публичным брокерским каналом. |
| ПСБ | ✓ | уточнить | н/р | н/р | ✓ | уточнить | Системно значимый банк, прямой сравнительный канал FX для среднего бизнеса. |
| Россельхозбанк | ✓ | ✓ | ✓ | ✓ | ✓ | уточнить | Системно значимый банк, сильный ориентир по публично раскрытым форвардам и CNY. |
| Совкомбанк | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Системно значимый банк, близкий функциональный аналог персонального анализа и работы с контрактом. |
| Уралсиб | ✓ | ✓ | н/р | уточнить | ✓ | н/р | Сопоставимый сервисный ВЭД-банк, контраст по ручной экспертизе и открытой дате. |
| Банк «Санкт-Петербург» | ✓ | ✓ | ✓ | уточнить | ✓ | н/р | Исходная линейка банка и каналы, на которых строится FX Control. |
| Московская биржа через брокера | ✓ | вне канала | вне канала | ✓ | ✓ | ✓ | Реальная альтернатива банковскому OTC для компаний с учётом ликвидности и базиса. |

`✓` — подтверждено в указанной области, `н/р` — не раскрыто, `уточнить` — требуется уточнение, `вне канала` — недоступно по опубликованному описанию канала. См. полные поля ниже и [CSV](../data/reference/banking_competitor_benchmark.csv).

## БСПБ — применимость CNY по каналу

- **Фактический платёж в CNY.** Витрина приводит поставочный форвард и онлайн-конверсию. Казначейство подтверждает маршрут поставки, сумму, дату, курс и лимит. [BS1](https://www.bspb.ru/foreign-trade/hedge), [BS4](https://www.bspb.ru/foreign-trade/ved-china)
- **Рублёвый платёж под CNY NDF на «Котировальной доске».** В витрине имеется пример NDF CNY, а CNYFIX определён в п. 3.1.27. Перечень доступных пар в обеих опубликованных версиях п. 3.1.35 — USDRUB, EURRUB, EURUSD. В опубликованном соглашении i2B CNY/RUB недоступен для данного типа сделки. Минимальная дата валютирования NDF — 4-й рабочий день, в витрине указано от одного дня. [BS1](https://www.bspb.ru/foreign-trade/hedge), [BS2](https://cdn.bspb.ru/pravila_ib_i2b_28_04_2026_84077be70b.pdf), [BS3](https://cdn.bspb.ru/pravila_ib_i2b_e3ae85cd70.pdf)
- **Голосовой OTC под CNY NDF.** Требуется уточнение по RISDA с актуальным приложением. Нужны пара, срок, валюта выплаты, формула и дата фиксинга, номинал, лимит, обеспечение и живая котировка. [BS1](https://www.bspb.ru/foreign-trade/hedge), [BS2](https://cdn.bspb.ru/pravila_ib_i2b_28_04_2026_84077be70b.pdf)

## MOEX через брокера — расчётные фьючерсы CNY/RUB

Лот 1 000 CNY, цена в ₽/CNY, шаг 0,001 ₽/CNY и стоимость шага 1 ₽ на контракт. Срочная серия рассчитывается в рублях по CNYFIXME в 14:00 МСК, CNYRUBF — один день с автопролонгацией и фандингом. Договорный курс, стоимость сделки и даты клиента могут отличаться от биржевых. Вариационная маржа и меняющееся ГО создают потребность в рублёвой ликвидности. Для получения CNY на дату платежа в дополнение нужна отдельная валютная операция. [MX1](https://www.moex.com/ru/derivatives/futures-on-currency/crz6), [MX2](https://www.moex.com/ru/derivatives/perpetual-futures/CNYRUBF), [MX3](https://www.moex.com/a3873), [MX4](https://www.moex.com/a113), [MX6](https://www.nationalclearingcentre.ru/catalog/030902), [MX7](https://www.moex.com/s135), [MX12](https://www.moex.com/n104130?nt=112)

| Серия | Дата окончания | Карточка с ценой и ГО |
| --- | --- | --- |
| CRZ6 | 17.12.2026 | [MOEX](https://www.moex.com/ru/derivatives/futures-on-currency/crz6) |
| CRH7 | 18.03.2027 | [MOEX](https://www.moex.com/ru/derivatives/futures-on-currency/crh7) |
| CRM7 | 17.06.2027 | [MOEX](https://www.moex.com/ru/derivatives/futures-on-currency/crm7) |
| CRU7 | 16.09.2027 | [MOEX](https://www.moex.com/ru/derivatives/futures-on-currency/cru7) |
| CRZ7 | 16.12.2027 | [MOEX](https://www.moex.com/en/derivatives/futures-on-currency/crz7) |
| CRH8 | 16.03.2028 | [MOEX](https://www.moex.com/en/derivatives/futures-on-currency/crh8) |
| CNYRUBF | Однодневный с автопролонгацией | [MOEX](https://www.moex.com/ru/derivatives/perpetual-futures/CNYRUBF) |

ГО зависит от даты, концентрации и категории клиента. Цена исполнения определяется условиями сделки. Биржевые и брокерские тарифы сверяются по инструменту и брокерскому договору. [Биржевые комиссии](https://www.moex.com/a90) · [НКЦ](https://www.nationalclearingcentre.ru/catalog/030902) · [Пример тарифа брокера ГПБ](https://www.gazprombank.ru/corporate/page/brokerage-service/trading-in-markets/)

## Проверенные поля по каналам

### Сбер

Системно значимый банк, сравнение цифрового ВЭД и массовых каналов.

| Поле | Статус | Свидетельство и первичный источник |
| --- | --- | --- |
| Конвертация | подтверждено | Онлайн покупка/продажа и валютные ордера. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation), [SB2](https://www.sberbank.ru/ru/legal/investments/instrumenty-raboty-s-kitaem?tab=advance) |
| Поставочный FX-forward | подтверждено | Конверсия с отсрочкой. В поставочном варианте с предоплатой документирована поставка остатка. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation), [SB2](https://www.sberbank.ru/ru/legal/investments/instrumenty-raboty-s-kitaem?tab=advance) |
| Расчётный FX-forward (NDF) | не раскрыто | Страница говорит о нескольких вариантах расчётов без поимённого подтверждения NDF для корпоративного сегмента. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation) |
| Валютный своп (FX swap) | подтверждено | Валютные свопы в терминале, своп овернайт с CNY для ликвидности. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation), [SB2](https://www.sberbank.ru/ru/legal/investments/instrumenty-raboty-s-kitaem?tab=advance) |
| Валютный опцион | подтверждено | Валютные опционы и опционные стратегии в корпоративной линейке. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation) |
| Биржевые валютные фьючерсы | подтверждено | Корпоративный брокерский счёт и фьючерсные поручения отдельно от OTC. [SB3](https://www.sberbank.ru/ru/legal/investments/broker_service/marketsandservices?page=1), [SB4](https://www.sberbank.ru/ru/legal/investments/broker_service/marketsandservices/info?tab=phone) |
| Минимальная сумма / лот | не раскрыто | Минимум обычного CNY FWD и NDF не опубликован. ₽50 тыс. относятся к бивалютному депозиту. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation), [SB2](https://www.sberbank.ru/ru/legal/investments/instrumenty-raboty-s-kitaem?tab=advance) |
| Срок / экспирация | подтверждено | Своп O/N на витрине до 3 дней. Бронирование курса от 2 дней до года. Срок обычного FWD не раскрыт. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation), [SB2](https://www.sberbank.ru/ru/legal/investments/instrumenty-raboty-s-kitaem?tab=advance) |
| Валюты и пары | подтверждено | CNY/RUB публично в витрине решений по юаню. Перечень всех пар по каждому деривативу закрыт. [SB2](https://www.sberbank.ru/ru/legal/investments/instrumenty-raboty-s-kitaem?tab=advance) |
| Цены, спреды и комиссии | требуется уточнение | Для CNY FWD заявлено отсутствие дополнительной комиссии. Цена сделки, спред и обеспечение нужны от банка. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation), [SB2](https://www.sberbank.ru/ru/legal/investments/instrumenty-raboty-s-kitaem?tab=advance) |
| Договор / документация | не раскрыто | Форма и приложение к внебиржевому CNY форварду в рассмотренных источниках не опубликованы. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation), [SB2](https://www.sberbank.ru/ru/legal/investments/instrumenty-raboty-s-kitaem?tab=advance), [SB3](https://www.sberbank.ru/ru/legal/investments/broker_service/marketsandservices?page=1) |
| Допуск и требования | подтверждено | Корпоративный клиент, для свопа на юаневой витрине нужен счёт в CNY. Брокерский допуск отдельный. [SB2](https://www.sberbank.ru/ru/legal/investments/instrumenty-raboty-s-kitaem?tab=advance), [SB3](https://www.sberbank.ru/ru/legal/investments/broker_service/marketsandservices?page=1) |
| Обеспечение / ГО | не раскрыто | Ставка/тип OTC обеспечения на выбранной витрине не опубликованы. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation), [SB2](https://www.sberbank.ru/ru/legal/investments/instrumenty-raboty-s-kitaem?tab=advance) |
| Кредитный / торговый лимит | не раскрыто | Сумма контрагентского лимита и правила расчёта по CNY не опубликованы. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation), [SB2](https://www.sberbank.ru/ru/legal/investments/instrumenty-raboty-s-kitaem?tab=advance) |
| Переоценка / дополнительные взносы | не раскрыто | Условия изменения OTC обеспечения по контракту не раскрыты. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation), [SB2](https://www.sberbank.ru/ru/legal/investments/instrumenty-raboty-s-kitaem?tab=advance) |
| Капитал / нагрузка на ликвидность | не раскрыто | Аллокация капитала под корпоративный FX не раскрыта. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation), [SB2](https://www.sberbank.ru/ru/legal/investments/instrumenty-raboty-s-kitaem?tab=advance) |
| ДБО / терминал | подтверждено | СберБизнес и SberCIB Terminal, в том числе онлайн котировки и валютные заявки. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation), [SB2](https://www.sberbank.ru/ru/legal/investments/instrumenty-raboty-s-kitaem?tab=advance) |
| Торговый API | не раскрыто | Торговый API для рассматриваемой корпоративной OTC операции не раскрыт. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation) |
| Менеджер / дилер / брокер | подтверждено | Выделенные специалисты по конверсии, хеджированию и ВЭД в пределах соответствующего сервиса. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation) |
| Обучение | подтверждено | На витрине есть видеокейсы. Программа подготовки к конкретному хеджу не раскрыта. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation) |
| Аналитика / контроль / сопровождение | подтверждено | Аналитический терминал, поддержка ВЭД и расчёты. В китайской линейке также сопровождение документов. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation), [SB2](https://www.sberbank.ru/ru/legal/investments/instrumenty-raboty-s-kitaem?tab=advance) |
| Целевой сегмент | подтверждено | Бизнес с ВЭД, в том числе клиенты, торгующие с Китаем. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation), [SB2](https://www.sberbank.ru/ru/legal/investments/instrumenty-raboty-s-kitaem?tab=advance) |
| Отрасль / специализация | подтверждено | Китай как отдельная ВЭД-география. Отраслевой допуск к деривативам не раскрыт. [SB2](https://www.sberbank.ru/ru/legal/investments/instrumenty-raboty-s-kitaem?tab=advance) |
| Заявленное позиционирование | подтверждено | Цифровая конверсия, линейка хеджей, авансирование до 90% в отдельном продукте. [SB1](https://digital.sber.ru/ru/legal/cib/currency-operation), [SB2](https://www.sberbank.ru/ru/legal/investments/instrumenty-raboty-s-kitaem?tab=advance) |
| Типовой сценарий | подтверждено | Импортная покупка CNY и фиксация курса будущего платежа. [SB2](https://www.sberbank.ru/ru/legal/investments/instrumenty-raboty-s-kitaem?tab=advance) |

### ВТБ

Системно значимый банк, эталон структурирования и сопровождения крупных компаний.

| Поле | Статус | Свидетельство и первичный источник |
| --- | --- | --- |
| Конвертация | подтверждено | Безналичная конверсия крупных клиентов и онлайн-ордера малого бизнеса. [VT2](https://www.vtb.ru/krupnyj-biznes/raschety/konversionnye-operacii/), [VT4](https://www.vtb.ru/malyj-biznes/raschetnoe-obsluzhivanie/konversionnye-operacii/) |
| Поставочный FX-forward | подтверждено | Опубликована конструкция покупки/продажи валюты по форварду и форвард с предоплатой; форма поставки уточняется по сделке. [VT1](https://www.vtb.ru/derivatives/) |
| Расчётный FX-forward (NDF) | требуется уточнение | Фраза о расчётном формате у валютно-процентного свопа. Пара/фиксинг и наличие отдельного NDF не подтверждены. [VT1](https://www.vtb.ru/derivatives/) |
| Валютный своп (FX swap) | подтверждено | Валютный своп указан отдельно в линейке. Валютно-процентный своп проверяется отдельно. [VT1](https://www.vtb.ru/derivatives/) |
| Валютный опцион | подтверждено | Валютный опцион, коридор и частичная защита по общей линейке. [VT1](https://www.vtb.ru/derivatives/) |
| Биржевые валютные фьючерсы | подтверждено | Брокерское хеджирование валютного риска на срочном рынке для юридических лиц. Допуск к серии индивидуальный. [VT3](https://www.vtb.ru/personal/investicii/repo-ul/) |
| Минимальная сумма / лот | не раскрыто | Минимальный номинал корпоративного FWD/опциона не опубликован. [VT1](https://www.vtb.ru/derivatives/), [VT2](https://www.vtb.ru/krupnyj-biznes/raschety/konversionnye-operacii/) |
| Срок / экспирация | подтверждено | Конверсия TOD/TOM/послезавтра, варианты FWD с открытой датой. Минимум срока FWD не опубликован. [VT1](https://www.vtb.ru/derivatives/), [VT2](https://www.vtb.ru/krupnyj-biznes/raschety/konversionnye-operacii/) |
| Валюты и пары | требуется уточнение | Для конкретного корпоративного CNY/RUB FWD/NDF список пар и котировка нужны от ВТБ. CNY пример в валютно-процентном свопе ограничен этим продуктом. [VT1](https://www.vtb.ru/derivatives/), [VT2](https://www.vtb.ru/krupnyj-biznes/raschety/konversionnye-operacii/) |
| Цены, спреды и комиссии | требуется уточнение | Страница FWD указывает отсутствие отдельной комиссии/премии. Курсовые условия и спред индивидуальны. [VT1](https://www.vtb.ru/derivatives/) |
| Договор / документация | подтверждено | Генеральное соглашение, стандартный комплект документов, отдельный договор для отдельных конверсий. Форма OTC подтверждения не раскрыта. [VT1](https://www.vtb.ru/derivatives/), [VT2](https://www.vtb.ru/krupnyj-biznes/raschety/konversionnye-operacii/) |
| Допуск и требования | подтверждено | Для OTC подписать генсоглашение, предоставить пакет документов. Для части сделок — финансовый анализ компании. [VT1](https://www.vtb.ru/derivatives/) |
| Обеспечение / ГО | не раскрыто | Вид/размер обеспечения конкретного FX дериватива не опубликован. Маржинальное кредитование брокера — отдельная услуга. [VT1](https://www.vtb.ru/derivatives/), [VT3](https://www.vtb.ru/personal/investicii/repo-ul/) |
| Кредитный / торговый лимит | подтверждено | Торговый лимит требуется для части сделок. Сумма и метод расчёта не раскрыты. [VT1](https://www.vtb.ru/derivatives/) |
| Переоценка / дополнительные взносы | не раскрыто | Порядок довнесения по корпоративному FX не опубликован в изученных материалах. [VT1](https://www.vtb.ru/derivatives/) |
| Капитал / нагрузка на ликвидность | не раскрыто | Аллокация банковского капитала на такие сделки не раскрыта. [VT1](https://www.vtb.ru/derivatives/) |
| ДБО / терминал | подтверждено | Интернет-банк/онлайн-конверсия для МСБ. OTC после согласования через трейдера. [VT1](https://www.vtb.ru/derivatives/), [VT4](https://www.vtb.ru/malyj-biznes/raschetnoe-obsluzhivanie/konversionnye-operacii/) |
| Торговый API | не раскрыто | Корпоративный торговый API для OTC не выявлен по изученным источникам. [VT1](https://www.vtb.ru/derivatives/), [VT4](https://www.vtb.ru/malyj-biznes/raschetnoe-obsluzhivanie/konversionnye-operacii/) |
| Менеджер / дилер / брокер | подтверждено | Трейдеры банка после договора, консультация по заявке, для брокерского канала отдельный доступ. [VT1](https://www.vtb.ru/derivatives/), [VT3](https://www.vtb.ru/personal/investicii/repo-ul/) |
| Обучение | подтверждено | Вебинар для СМБ о ВЭД и интернет-банке. [VT5](https://kdelu.vtb.ru/webinars/ekosistema-ved-v-novom-internet-banke-vtb-7/) |
| Аналитика / контроль / сопровождение | подтверждено | Подбор хедж-стратегии, финансовый анализ для сделок с лимитом. [VT1](https://www.vtb.ru/derivatives/) |
| Целевой сегмент | подтверждено | Большой корпоративный сегмент для сложных хеджей; отдельная конверсия МСБ. [VT1](https://www.vtb.ru/derivatives/), [VT2](https://www.vtb.ru/krupnyj-biznes/raschety/konversionnye-operacii/), [VT4](https://www.vtb.ru/malyj-biznes/raschetnoe-obsluzhivanie/konversionnye-operacii/) |
| Отрасль / специализация | не раскрыто | Отраслевой порог корпоративного FX не опубликован. [VT1](https://www.vtb.ru/derivatives/) |
| Заявленное позиционирование | подтверждено | Сложные/нестандартные хеджи, брокерский доступ и отдельные онлайн-каналы для МСБ. [VT1](https://www.vtb.ru/derivatives/), [VT3](https://www.vtb.ru/personal/investicii/repo-ul/), [VT4](https://www.vtb.ru/malyj-biznes/raschetnoe-obsluzhivanie/konversionnye-operacii/) |
| Типовой сценарий | подтверждено | Крупная компания с будущим валютным платежом или обязательством в иностранной валюте. [VT1](https://www.vtb.ru/derivatives/) |

### Альфа-Банк

Системно значимый банк, сильный прямой аналог по CNY для МСБ и электронному FX.

| Поле | Статус | Свидетельство и первичный источник |
| --- | --- | --- |
| Конвертация | подтверждено | TOD/TOM/SPOT и безналичная конверсия через ДБО. [AL2](https://alfabank.ru/corporate/financial/conversion/), [AL3](https://alfabank.ru/sme/ved/conversion/) |
| Поставочный FX-forward | подтверждено | В CNY по МСБ продукт предусматривает поставку валюты клиенту в дату сделки. [AL1](https://alfabank.ru/sme/ved/risk-hedging/) |
| Расчётный FX-forward (NDF) | не раскрыто | Корпоративная расчётная схема CNY NDF не названа. [AL1](https://alfabank.ru/sme/ved/risk-hedging/), [AL2](https://alfabank.ru/corporate/financial/conversion/), [AL4](https://alfabank.ru/corporate/ved/hedging/) |
| Валютный своп (FX swap) | подтверждено | Валютные свопы в корпоративной линейке рынка. [AL2](https://alfabank.ru/corporate/financial/conversion/) |
| Валютный опцион | подтверждено | Опцион и опционные стратегии для МСБ, премия индивидуальна. [AL1](https://alfabank.ru/sme/ved/risk-hedging/) |
| Биржевые валютные фьючерсы | требуется уточнение | Есть торговый функционал по фьючерсам и брокерские документы для юрлиц. Доступ к конкретной валютной серии и тариф проверить. [AL2](https://alfabank.ru/corporate/financial/conversion/), [AL6](https://alfainvest.alfabank.ru/invest/s3/static/aktsii-ai/pravilaavp2026.pdf) |
| Минимальная сумма / лот | не раскрыто | Витрина МСБ оглашает срок и валюту. Минимальный номинал не показывает. [AL1](https://alfabank.ru/sme/ved/risk-hedging/) |
| Срок / экспирация | подтверждено | Срок продуктов хеджирования в линейке МСБ от 3 дней. Верхний срок по CNY контракту не раскрыт. [AL1](https://alfabank.ru/sme/ved/risk-hedging/) |
| Валюты и пары | подтверждено | CNY в линейке МСБ. Корпоративный рынок заявляет широкий выбор пар без перечня по деривативам. [AL1](https://alfabank.ru/sme/ved/risk-hedging/), [AL2](https://alfabank.ru/corporate/financial/conversion/) |
| Цены, спреды и комиссии | требуется уточнение | Премия опциона считается по сделке. Накопительный тариф относится к конверсии, а не к форварду. [AL1](https://alfabank.ru/sme/ved/risk-hedging/), [AL3](https://alfabank.ru/sme/ved/conversion/) |
| Договор / документация | подтверждено | Соглашение с банком для опциона. Брокерское генеральное соглашение опубликовано отдельно, формы OTC FWD/NDF не раскрыты. [AL1](https://alfabank.ru/sme/ved/risk-hedging/), [AL6](https://alfainvest.alfabank.ru/invest/s3/static/aktsii-ai/pravilaavp2026.pdf) |
| Допуск и требования | подтверждено | Линейка МСБ для внешней торговли/заимствований. Для конверсии — отдельный счёт по валюте. [AL1](https://alfabank.ru/sme/ved/risk-hedging/), [AL3](https://alfabank.ru/sme/ved/conversion/) |
| Обеспечение / ГО | не раскрыто | Залог и схема маржевых взносов по МСБ CNY не раскрыты. [AL1](https://alfabank.ru/sme/ved/risk-hedging/), [AL4](https://alfabank.ru/corporate/ved/hedging/) |
| Кредитный / торговый лимит | не раскрыто | Наличие и размер отдельного кредитного лимита по CNY FWD в найденной линейке не раскрыты. [AL1](https://alfabank.ru/sme/ved/risk-hedging/), [AL4](https://alfabank.ru/corporate/ved/hedging/) |
| Переоценка / дополнительные взносы | не раскрыто | Довнесение OTC обеспечения по линейке не раскрыто. [AL1](https://alfabank.ru/sme/ved/risk-hedging/), [AL4](https://alfabank.ru/corporate/ved/hedging/) |
| Капитал / нагрузка на ликвидность | не раскрыто | Банковская аллокация на FX риск по продукту не раскрыта. [AL1](https://alfabank.ru/sme/ved/risk-hedging/), [AL4](https://alfabank.ru/corporate/ved/hedging/) |
| ДБО / терминал | подтверждено | Торговая платформа и алгоритмические ордера, конверсия для МСБ через ДБО. [AL2](https://alfabank.ru/corporate/financial/conversion/), [AL3](https://alfabank.ru/sme/ved/conversion/) |
| Торговый API | не раскрыто | Алгоритмические ордера публичны. Внешний API для CNY OTC не подтверждён. [AL2](https://alfabank.ru/corporate/financial/conversion/) |
| Менеджер / дилер / брокер | подтверждено | Сотрудник подбирает стратегию, FX-деск для конверсии 24/5 по витрине. [AL1](https://alfabank.ru/sme/ved/risk-hedging/), [AL2](https://alfabank.ru/corporate/financial/conversion/), [AL4](https://alfabank.ru/corporate/ved/hedging/) |
| Обучение | подтверждено | Курс Альфа-Курса по ВЭД-2026. [AL5](https://kurs.alfabank.ru/courses/vehd-2026-chto-izmenitsya-v-zakonah-i-kak-dejstvovat-biznesu/) |
| Аналитика / контроль / сопровождение | подтверждено | Подбор стратегии финансовыми специалистами, контроль/поддержка ВЭД и рыночные инструменты. [AL1](https://alfabank.ru/sme/ved/risk-hedging/), [AL2](https://alfabank.ru/corporate/financial/conversion/), [AL4](https://alfabank.ru/corporate/ved/hedging/) |
| Целевой сегмент | подтверждено | МСБ с внешними расчётами и крупный/средний корпоративный бизнес в отдельных линейках. [AL1](https://alfabank.ru/sme/ved/risk-hedging/), [AL3](https://alfabank.ru/sme/ved/conversion/), [AL4](https://alfabank.ru/corporate/ved/hedging/) |
| Отрасль / специализация | не раскрыто | Приоритетная отрасль/отраслевой порог FX хеджа не раскрыты. [AL1](https://alfabank.ru/sme/ved/risk-hedging/), [AL4](https://alfabank.ru/corporate/ved/hedging/) |
| Заявленное позиционирование | подтверждено | CNY для МСБ, алгоритмические ордера и сервис экспертов. [AL1](https://alfabank.ru/sme/ved/risk-hedging/), [AL2](https://alfabank.ru/corporate/financial/conversion/) |
| Типовой сценарий | подтверждено | Импортёр из МСБ покупает CNY к сроку расчёта, выбирает FWD или опцион. [AL1](https://alfabank.ru/sme/ved/risk-hedging/) |

### Газпромбанк

Системно значимый банк с крупным корпоративным дилингом и публичным брокерским каналом.

| Поле | Статус | Свидетельство и первичный источник |
| --- | --- | --- |
| Конвертация | подтверждено | Конверсия в реальном времени, в том числе TOD до 16:30 по витрине. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/), [GP2](https://www.gazprombank.ru/corporate/page/v-operation/) |
| Поставочный FX-forward | подтверждено | Есть конверсия с датой валютирования FORWARD. Срок/пары и форма подтверждения подлежат проверке. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/), [GP2](https://www.gazprombank.ru/corporate/page/v-operation/) |
| Расчётный FX-forward (NDF) | не раскрыто | Отдельный NDF в рассмотренном клиентском предложении не назван. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/), [GP2](https://www.gazprombank.ru/corporate/page/v-operation/), [GP3](https://www.gazprombank.ru/corporate/page/dilling/) |
| Валютный своп (FX swap) | не раскрыто | Именно FX swap в сопоставимой линейке нефинансовых клиентов не раскрыт. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/), [GP2](https://www.gazprombank.ru/corporate/page/v-operation/), [GP3](https://www.gazprombank.ru/corporate/page/dilling/) |
| Валютный опцион | не раскрыто | Валютный OTC опцион для указанного клиентского контура не раскрыт. Опционы FORTS считаются отдельно. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/), [GP2](https://www.gazprombank.ru/corporate/page/v-operation/), [GP5](https://www.gazprombank.ru/corporate/page/brokerage-service/trading-in-markets/) |
| Биржевые валютные фьючерсы | подтверждено | Для юрлиц публичен брокерский доступ FORTS для валютного хеджирования. [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/), [GP5](https://www.gazprombank.ru/corporate/page/brokerage-service/trading-in-markets/) |
| Минимальная сумма / лот | не раскрыто | Минимум OTC конверсии/FWD не опубликован. У брокера минимум зависит от биржевого инструмента. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/), [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/) |
| Срок / экспирация | подтверждено | В конверсии описаны любые даты валютирования, включая FORWARD. Числовая граница FWD не раскрыта. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/) |
| Валюты и пары | требуется уточнение | Для конверсии заявлены доступные банку пары без договорного перечня CNY для FWD/NDF. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/), [GP2](https://www.gazprombank.ru/corporate/page/v-operation/) |
| Цены, спреды и комиссии | требуется уточнение | По OTC условия индивидуальны. Страница FORTS отдельно показывает брокерские 0,50 ₽ за сделку и 1 ₽ за исполнение на контракт. [GP2](https://www.gazprombank.ru/corporate/page/v-operation/), [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/), [GP5](https://www.gazprombank.ru/corporate/page/brokerage-service/trading-in-markets/) |
| Договор / документация | подтверждено | Публикуется раздел Генерального соглашения в форме присоединения, OTC каналы отделены от брокерского договора. [GP2](https://www.gazprombank.ru/corporate/page/v-operation/), [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/) |
| Допуск и требования | подтверждено | Корпоративный клиент и присоединение к условиям банка. Брокерский счёт и допуск к секции — отдельная процедура. [GP2](https://www.gazprombank.ru/corporate/page/v-operation/), [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/) |
| Обеспечение / ГО | не раскрыто | Ставка и форма OTC залога по CNY форварду не указаны. Биржевое ГО зависит от инструмента и брокера. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/), [GP2](https://www.gazprombank.ru/corporate/page/v-operation/), [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/) |
| Кредитный / торговый лимит | не раскрыто | Предел кредитного/торгового лимита для корпоративного FWD не опубликован. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/), [GP2](https://www.gazprombank.ru/corporate/page/v-operation/) |
| Переоценка / дополнительные взносы | не раскрыто | График OTC довнесений не опубликован. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/), [GP2](https://www.gazprombank.ru/corporate/page/v-operation/) |
| Капитал / нагрузка на ликвидность | не раскрыто | Публичная аллокация капитала на корпоративную сделку отсутствует. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/), [GP2](https://www.gazprombank.ru/corporate/page/v-operation/) |
| ДБО / терминал | подтверждено | ГПБ-Дилинг, ГПБ Бизнес-Онлайн. Для брокерского канала GPB-i-Trade. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/), [GP3](https://www.gazprombank.ru/corporate/page/dilling/), [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/) |
| Торговый API | не раскрыто | Торговый API для OTC клиентского FX не подтверждён. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/), [GP3](https://www.gazprombank.ru/corporate/page/dilling/) |
| Менеджер / дилер / брокер | подтверждено | Прямой дилинг, телефон и персональный брокерский менеджер для юрлиц. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/), [GP3](https://www.gazprombank.ru/corporate/page/dilling/), [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/) |
| Обучение | не раскрыто | Формальная учебная программа по OTC FX в проверенных источниках не раскрыта. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/), [GP3](https://www.gazprombank.ru/corporate/page/dilling/), [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/) |
| Аналитика / контроль / сопровождение | подтверждено | Информационно-торговая система и поддержка корпоративных операций FX. [GP2](https://www.gazprombank.ru/corporate/page/v-operation/), [GP3](https://www.gazprombank.ru/corporate/page/dilling/), [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/) |
| Целевой сегмент | подтверждено | Крупный/корпоративный бизнес, возможен отдельный брокерский маршрут. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/), [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/) |
| Отрасль / специализация | не раскрыто | Отраслевой допуск именно к FWD в публичных условиях не раскрыт. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/), [GP2](https://www.gazprombank.ru/corporate/page/v-operation/) |
| Заявленное позиционирование | подтверждено | Онлайн дилинг с выбором расчётной даты и отдельный доступ FORTS. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/), [GP3](https://www.gazprombank.ru/corporate/page/dilling/), [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/) |
| Типовой сценарий | подтверждено | Корпоративная конверсия с будущей датой или биржевая защита через брокерский счёт. [GP1](https://www.gazprombank.ru/corporate/page/c-operations/), [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/), [GP5](https://www.gazprombank.ru/corporate/page/brokerage-service/trading-in-markets/) |

### ПСБ

Системно значимый банк, прямой сравнительный канал FX для среднего бизнеса.

| Поле | Статус | Свидетельство и первичный источник |
| --- | --- | --- |
| Конвертация | подтверждено | Конверсия, FX-модуль клиент-банка, заявлены 50+ валютных пар. [PS2](https://www.psbank.ru/corporate/international/conversion) |
| Поставочный FX-forward | требуется уточнение | Раздел хеджирования подтверждает форварды и стратегии. Обязательная поставка по конкретному FX продукту не раскрыта. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging) |
| Расчётный FX-forward (NDF) | не раскрыто | Отдельный NDF, список пар и фиксинг не указаны. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging), [PS2](https://www.psbank.ru/corporate/international/conversion) |
| Валютный своп (FX swap) | не раскрыто | В линейке явно названы товарный и валютно-процентный своп. Обычный FX swap для рассматриваемых нефинансовых клиентов не установлен. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging), [PS2](https://www.psbank.ru/corporate/international/conversion) |
| Валютный опцион | подтверждено | Поддерживаются валютный коридор, call-spread и барьерные стратегии. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging) |
| Биржевые валютные фьючерсы | требуется уточнение | Официально есть корпоративный брокерский продукт и операции с ПФИ. Доступ юрлица к конкретному CNY фьючерсу проверить. [PS3](https://www.psbank.ru/corporate/investment/business-broker), [PS4](https://www.psbank.ru/personal/wealth/markets/documents), [PS5](https://www.psbank.ru/personal/wealth/markets/about) |
| Минимальная сумма / лот | не раскрыто | Фраза о любых суммах относится к покупке/продаже валюты. Минимум FX форварда не опубликован. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging), [PS2](https://www.psbank.ru/corporate/international/conversion) |
| Срок / экспирация | не раскрыто | Числовой срок FX форварда не раскрыт. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging) |
| Валюты и пары | требуется уточнение | Число 50+ относится к конверсии. Пары FWD и возможность CNY NDF требуют проверки. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging), [PS2](https://www.psbank.ru/corporate/international/conversion) |
| Цены, спреды и комиссии | не раскрыто | Точные спреды, стоимость внебиржевой сделки и премии не опубликованы. Брокерский тариф имеет собственную редакцию. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging), [PS2](https://www.psbank.ru/corporate/international/conversion), [PS4](https://www.psbank.ru/personal/wealth/markets/documents) |
| Договор / документация | не раскрыто | Рамочная документация OTC для этого сегмента не опубликована в проверенных источниках. Брокерский регламент не заменяет её. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging), [PS4](https://www.psbank.ru/personal/wealth/markets/documents) |
| Допуск и требования | требуется уточнение | Средний/крупный корпоративный клиент указан. Документы и допуск к конкретной сделке нужны от банка. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging), [PS3](https://www.psbank.ru/corporate/investment/business-broker) |
| Обеспечение / ГО | не раскрыто | Залог/маржа нефинансовых клиентов по OTC FX не раскрыты. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging), [PS2](https://www.psbank.ru/corporate/international/conversion) |
| Кредитный / торговый лимит | не раскрыто | Критерии и сумма торгового лимита для среднего нефинансового клиента не раскрыты. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging), [PS2](https://www.psbank.ru/corporate/international/conversion) |
| Переоценка / дополнительные взносы | не раскрыто | Условия довнесения OTC обеспечения не раскрыты. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging), [PS4](https://www.psbank.ru/personal/wealth/markets/documents) |
| Капитал / нагрузка на ликвидность | не раскрыто | Публичной аллокации риск-капитала по продукту нет в проверенных источниках. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging), [PS2](https://www.psbank.ru/corporate/international/conversion) |
| ДБО / терминал | подтверждено | FX-модуль в клиент-банке для конверсии. [PS2](https://www.psbank.ru/corporate/international/conversion) |
| Торговый API | не раскрыто | Клиентский торговый API для подтверждённых FX деривативов не раскрыт. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging), [PS2](https://www.psbank.ru/corporate/international/conversion) |
| Менеджер / дилер / брокер | подтверждено | Центр экспертизы и FX-деск, отдельный контакт для среднего бизнеса. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging) |
| Обучение | не раскрыто | Формальная программа обучения корпоративного FX клиента не раскрыта в просмотренных материалах. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging), [PS3](https://www.psbank.ru/corporate/investment/business-broker) |
| Аналитика / контроль / сопровождение | подтверждено | Центр экспертизы, работа с чувствительностью финансового результата к курсу. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging) |
| Целевой сегмент | подтверждено | Средний и крупный бизнес, более широкий брокерский контур. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging), [PS3](https://www.psbank.ru/corporate/investment/business-broker), [PS5](https://www.psbank.ru/personal/wealth/markets/about) |
| Отрасль / специализация | подтверждено | Банк раскрывает специализацию на ГОЗ и крупных госконтрактах. Доступ FX к конкретной отрасли отдельно не установлен. [PS5](https://www.psbank.ru/personal/wealth/markets/about) |
| Заявленное позиционирование | подтверждено | Широкая конверсия и персональные стратегии хеджирования, включая сложные конструкции. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging), [PS2](https://www.psbank.ru/corporate/international/conversion) |
| Типовой сценарий | подтверждено | Средний бизнес с будущими валютными платежами обращается за форвардной/опционной стратегией. [PS1](https://www.psbank.ru/financialmarkets/expertisecenter/hedging) |

### Россельхозбанк

Системно значимый банк, сильный ориентир по публично раскрытым форвардам и CNY.

| Поле | Статус | Свидетельство и первичный источник |
| --- | --- | --- |
| Конвертация | подтверждено | Конверсия по рыночной котировке/курсу ЦБ, прямой дилинг, лимитные ордера и TWAP. [RS1](https://www.rshb.ru/business/ved/currency-operations), [RS3](https://www.rshb.ru/api/v1/storage/b126517f-3f0d-4c0c-a2fb-17e83a88b964/attachment) |
| Поставочный FX-forward | подтверждено | В корпоративной линейке прямо названы поставочные форварды. [RS1](https://www.rshb.ru/business/ved/currency-operations) |
| Расчётный FX-forward (NDF) | подтверждено | В той же линейке прямо названы беспоставочные форварды. Конкретную комбинацию пары, срока и фиксинга проверяют у дилера. [RS1](https://www.rshb.ru/business/ved/currency-operations) |
| Валютный своп (FX swap) | подтверждено | Валютный своп публично указан на витрине работы с валютным рынком. [RS1](https://www.rshb.ru/business/ved/currency-operations) |
| Валютный опцион | подтверждено | Валютные опционы и коридор, срок до 6 мес. для CNY/USD/EUR. [RS1](https://www.rshb.ru/business/ved/currency-operations) |
| Биржевые валютные фьючерсы | требуется уточнение | Брокерские правила включают юрлиц и срочные контракты. Доступ к нужной серии CNY по договору нужно подтвердить. [RS4](https://www.rshb.ru/api/v1/storage/1167f99c-60d7-4f6e-ab31-1610475e8938/attachment) |
| Минимальная сумма / лот | не раскрыто | Минимальный номинал FWD/NDF в публичной продуктовой карточке не указан. [RS1](https://www.rshb.ru/business/ved/currency-operations) |
| Срок / экспирация | подтверждено | Форвард до 1 года, опционы до 6 мес. для CNY/USD/EUR. Нижняя граница форварда не раскрыта. [RS1](https://www.rshb.ru/business/ved/currency-operations) |
| Валюты и пары | подтверждено | CNY/USD/EUR заявлены для линейки, разбивку по типу сделки и расчётному курсу проверить. [RS1](https://www.rshb.ru/business/ved/currency-operations) |
| Цены, спреды и комиссии | требуется уточнение | Премия по опциону оговорена, возможна комбинация с нулевой премией. Фактические котировки и спред OTC индивидуальны. [RS1](https://www.rshb.ru/business/ved/currency-operations) |
| Договор / документация | подтверждено | Договор прямого дилинга, типовую форму выдают по запросу. Правила «Валютные торги» открыты отдельно. [RS1](https://www.rshb.ru/business/ved/currency-operations), [RS3](https://www.rshb.ru/api/v1/storage/b126517f-3f0d-4c0c-a2fb-17e83a88b964/attachment) |
| Допуск и требования | подтверждено | Предложение участникам ВЭД, по прямому дилингу нужен соответствующий договор. Кредитный допуск индивидуален. [RS1](https://www.rshb.ru/business/ved/currency-operations), [RS2](https://www.rshb.ru/business/ved) |
| Обеспечение / ГО | не раскрыто | Витрина указывает, что деньги по форварду нужны в дату расчетов. Ставка/форма дополнительного обеспечения не раскрыты. [RS1](https://www.rshb.ru/business/ved/currency-operations) |
| Кредитный / торговый лимит | не раскрыто | Размер и метод назначения лимита по FX не раскрыты. [RS1](https://www.rshb.ru/business/ved/currency-operations) |
| Переоценка / дополнительные взносы | не раскрыто | График OTC переоценки и довнесения обеспечения не раскрыт. Брокерское регулирование отдельно. [RS1](https://www.rshb.ru/business/ved/currency-operations), [RS4](https://www.rshb.ru/api/v1/storage/1167f99c-60d7-4f6e-ab31-1610475e8938/attachment) |
| Капитал / нагрузка на ликвидность | не раскрыто | Банковская аллокация капитала на продукт не раскрыта. [RS1](https://www.rshb.ru/business/ved/currency-operations) |
| ДБО / терминал | подтверждено | Модуль «Валютные торги» системы «Свой бизнес». [RS1](https://www.rshb.ru/business/ved/currency-operations), [RS3](https://www.rshb.ru/api/v1/storage/b126517f-3f0d-4c0c-a2fb-17e83a88b964/attachment) |
| Торговый API | не раскрыто | Клиентский торговый API для OTC не раскрыт. [RS1](https://www.rshb.ru/business/ved/currency-operations), [RS3](https://www.rshb.ru/api/v1/storage/b126517f-3f0d-4c0c-a2fb-17e83a88b964/attachment) |
| Менеджер / дилер / брокер | подтверждено | Прямой дилер, экспертное и персональное сопровождение ВЭД. [RS1](https://www.rshb.ru/business/ved/currency-operations), [RS2](https://www.rshb.ru/business/ved) |
| Обучение | требуется уточнение | Есть бесплатные консультации по валютному законодательству. Специализированная программа обучения хеджу требует проверки. [RS1](https://www.rshb.ru/business/ved/currency-operations), [RS5](https://www.rshb.ru/business/ved/currency-controls) |
| Аналитика / контроль / сопровождение | подтверждено | Рыночные консультации, дистанционный учёт и контроль контрактов. [RS1](https://www.rshb.ru/business/ved/currency-operations), [RS5](https://www.rshb.ru/business/ved/currency-controls) |
| Целевой сегмент | подтверждено | Импортёры и экспортёры из корпоративного ВЭД с потоками в разных валютах. [RS1](https://www.rshb.ru/business/ved/currency-operations), [RS2](https://www.rshb.ru/business/ved) |
| Отрасль / специализация | не раскрыто | Отраслевые критерии допуска именно к FX форварду не опубликованы. [RS1](https://www.rshb.ru/business/ved/currency-operations), [RS2](https://www.rshb.ru/business/ved) |
| Заявленное позиционирование | подтверждено | Комбинирует прямой дилинг, валютные ордера и явно раскрытые FWD/NDF и опционы. [RS1](https://www.rshb.ru/business/ved/currency-operations) |
| Типовой сценарий | подтверждено | Импортёр или экспортёр фиксирует будущий расчёт, сопоставляя поставочный и денежный хедж. [RS1](https://www.rshb.ru/business/ved/currency-operations) |

### Совкомбанк

Системно значимый банк, близкий функциональный аналог персонального анализа и работы с контрактом.

| Поле | Статус | Свидетельство и первичный источник |
| --- | --- | --- |
| Конвертация | подтверждено | Онлайн-конверсия среднего/крупного бизнеса, в том числе юань. [SV5](https://sovcombank.ru/corp/ved/konversiya-valyuti) |
| Поставочный FX-forward | подтверждено | Поставочный форвард назван в текущей витрине и отдельно описан в паспорте. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging), [SV2](https://sovcombank.ru/document/9262) |
| Расчётный FX-forward (NDF) | подтверждено | Паспорт 2021 описывает NDF с фиксингом. Актуальные пары, цена и кредитные условия нужны от банка. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging), [SV2](https://sovcombank.ru/document/9262) |
| Валютный своп (FX swap) | подтверждено | Валютный своп в продуктовой линейке, отдельный паспорт поставочного свопа. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging), [SV3](https://sovcombank.ru/document/9261) |
| Валютный опцион | подтверждено | Валютные опционы и комбинации в текущей корпоративной витрине. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging), [SV4](https://sovcombank.ru/corporate/broker/for-corporations) |
| Биржевые валютные фьючерсы | подтверждено | Срочная секция MOEX и фьючерсы через корпоративный брокерский канал. [SV4](https://sovcombank.ru/corporate/broker/for-corporations) |
| Минимальная сумма / лот | не раскрыто | Минимум корпоративного форварда в изученных материалах не указан. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging), [SV2](https://sovcombank.ru/document/9262) |
| Срок / экспирация | подтверждено | Паспорт поставочного FWD описывает расчёты не раньше 3-го рабочего дня; подтвердить актуальную редакцию и предельный срок. [SV2](https://sovcombank.ru/document/9262) |
| Валюты и пары | требуется уточнение | Для конверсии заявлен CNY. Для конкретной пары FWD/NDF условия согласуются, список не опубликован. [SV2](https://sovcombank.ru/document/9262), [SV5](https://sovcombank.ru/corp/ved/konversiya-valyuti) |
| Цены, спреды и комиссии | требуется уточнение | Банк раскрывает факторы цены: срок, сумма, рынок и инструмент. Фактическую цену/спред нужно запрашивать. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging) |
| Договор / документация | подтверждено | Генеральное соглашение, в отдельных случаях ВЭД-контракт. Паспорта FWD/NDF и свопа доступны. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging), [SV2](https://sovcombank.ru/document/9262), [SV3](https://sovcombank.ru/document/9261) |
| Допуск и требования | подтверждено | Предложение ВЭД, клиентам с валютными кредитами и сырьевыми рисками; первичная оценка валюты, суммы, срока. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging) |
| Обеспечение / ГО | не раскрыто | Точное OTC обеспечение не раскрыто применительно к нужной сделке. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging), [SV2](https://sovcombank.ru/document/9262) |
| Кредитный / торговый лимит | не раскрыто | Публичного лимита или универсальной методики выделения лимита нет в проверенных источниках. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging), [SV2](https://sovcombank.ru/document/9262) |
| Переоценка / дополнительные взносы | не раскрыто | Условия маржинальных требований корпоративных CNY OTC не раскрыты. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging), [SV2](https://sovcombank.ru/document/9262) |
| Капитал / нагрузка на ликвидность | не раскрыто | Аллокация банковского капитала на сделку не опубликована. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging), [SV2](https://sovcombank.ru/document/9262) |
| ДБО / терминал | подтверждено | FX-модуль клиент-банка для конверсии и отдельный брокерский канал. [SV4](https://sovcombank.ru/corporate/broker/for-corporations), [SV5](https://sovcombank.ru/corp/ved/konversiya-valyuti) |
| Торговый API | не раскрыто | Торговый API для OTC сделки не раскрыт в просмотренных источниках. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging), [SV4](https://sovcombank.ru/corporate/broker/for-corporations), [SV5](https://sovcombank.ru/corp/ved/konversiya-valyuti) |
| Менеджер / дилер / брокер | подтверждено | Специалисты анализируют сделки и подбирают механизм, для биржи — брокерский счёт. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging), [SV4](https://sovcombank.ru/corporate/broker/for-corporations) |
| Обучение | не раскрыто | Формальная учебная программа по корпоративному OTC хеджу не раскрыта. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging), [SV4](https://sovcombank.ru/corporate/broker/for-corporations) |
| Аналитика / контроль / сопровождение | подтверждено | Анализ валюты расчётов, сумм и сроков, подбор хеджа и запрос контракта. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging) |
| Целевой сегмент | подтверждено | Прежде всего средний и крупный бизнес, ВЭД и заёмщики с валютными обязательствами. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging), [SV5](https://sovcombank.ru/corp/ved/konversiya-valyuti) |
| Отрасль / специализация | подтверждено | Отдельные заявки от сырьевых компаний, сегмент также включает ВЭД и валютных заемщиков. Это публичная специализация, а не барьер допуска. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging) |
| Заявленное позиционирование | подтверждено | Персональный подбор и сочетание внебиржевой и биржевой линейки. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging), [SV4](https://sovcombank.ru/corporate/broker/for-corporations) |
| Типовой сценарий | подтверждено | ВЭД-компания приносит контракт, банк оценивает сумму, валюту и сроки и предлагает хедж. [SV1](https://sovcombank.ru/investbank/financial-instruments/hedging) |

### Уралсиб

Сопоставимый сервисный ВЭД-банк, контраст по ручной экспертизе и открытой дате.

| Поле | Статус | Свидетельство и первичный источник |
| --- | --- | --- |
| Конвертация | подтверждено | Котировки, конверсия по курсу дилинга, желаемому курсу и онлайн. [UR1](https://uralsib.ru/business/ved), [UR3](https://uralsib.ru/api/directory-engine/files/rates/usloviya-konversionnyh-sdelok_oual3gi4.pdf) |
| Поставочный FX-forward | подтверждено | Витрина предлагает форвард с открытой/фиксированной датой, FAQ описывает покупку/продажу валюты. [UR1](https://uralsib.ru/business/ved), [UR2](https://uralsib.ru/faq/business/ved) |
| Расчётный FX-forward (NDF) | не раскрыто | Расчётный форвард как отдельный контракт не раскрыт. [UR1](https://uralsib.ru/business/ved), [UR2](https://uralsib.ru/faq/business/ved), [UR3](https://uralsib.ru/api/directory-engine/files/rates/usloviya-konversionnyh-sdelok_oual3gi4.pdf) |
| Валютный своп (FX swap) | требуется уточнение | FAQ объясняет FX swap. Исполнимое предложение и рамочный документ клиенту не подтверждены. [UR1](https://uralsib.ru/business/ved), [UR2](https://uralsib.ru/faq/business/ved) |
| Валютный опцион | подтверждено | ВЭД-витрина и FAQ показывают валютный опцион/его механику. Условия по CNY уточняются. [UR1](https://uralsib.ru/business/ved), [UR2](https://uralsib.ru/faq/business/ved) |
| Биржевые валютные фьючерсы | не раскрыто | Корпоративный допуск к фьючерсу MOEX публично не подтверждён в рассмотренной линейке. [UR1](https://uralsib.ru/business/ved), [UR3](https://uralsib.ru/api/directory-engine/files/rates/usloviya-konversionnyh-sdelok_oual3gi4.pdf) |
| Минимальная сумма / лот | не раскрыто | Порог суммы дериватива не указан. Пороги постановки на учёт контракта — иной параметр. [UR1](https://uralsib.ru/business/ved), [UR2](https://uralsib.ru/faq/business/ved), [UR3](https://uralsib.ru/api/directory-engine/files/rates/usloviya-konversionnyh-sdelok_oual3gi4.pdf) |
| Срок / экспирация | подтверждено | У форварда открытая или фиксированная дата; числовой минимум срока не опубликован. [UR1](https://uralsib.ru/business/ved), [UR2](https://uralsib.ru/faq/business/ved) |
| Валюты и пары | требуется уточнение | Работа с Китаем/валютами ВЭД не равна CNY/RUB FWD или NDF. Список пар нужно запросить. [UR1](https://uralsib.ru/business/ved), [UR2](https://uralsib.ru/faq/business/ved) |
| Цены, спреды и комиссии | не раскрыто | Цена/спред FWD и премия для целевой сделки не опубликованы. [UR1](https://uralsib.ru/business/ved), [UR2](https://uralsib.ru/faq/business/ved), [UR3](https://uralsib.ru/api/directory-engine/files/rates/usloviya-konversionnyh-sdelok_oual3gi4.pdf) |
| Договор / документация | подтверждено | Публичны правила конверсионных сделок (прил. 16). Форма рамочного соглашения именно на FX FWD не раскрыта. [UR1](https://uralsib.ru/business/ved), [UR3](https://uralsib.ru/api/directory-engine/files/rates/usloviya-konversionnyh-sdelok_oual3gi4.pdf) |
| Допуск и требования | требуется уточнение | Импортёр/экспортёр и заявка на консультацию видны. Допуск к OTC деривативу выясняется по клиенту. [UR1](https://uralsib.ru/business/ved), [UR2](https://uralsib.ru/faq/business/ved), [UR5](https://uralsib.ru/faq/business/ved/obschaya-informatsiya/kontakty-dlya-dopolnitelnykh-konsultatsiy) |
| Обеспечение / ГО | не раскрыто | Залог и его ставка для CNY форварда не опубликованы. [UR1](https://uralsib.ru/business/ved), [UR3](https://uralsib.ru/api/directory-engine/files/rates/usloviya-konversionnyh-sdelok_oual3gi4.pdf) |
| Кредитный / торговый лимит | не раскрыто | Торговый/кредитный лимит OTC не раскрыт. [UR1](https://uralsib.ru/business/ved), [UR3](https://uralsib.ru/api/directory-engine/files/rates/usloviya-konversionnyh-sdelok_oual3gi4.pdf) |
| Переоценка / дополнительные взносы | не раскрыто | График довнесений для корпоративного OTC не раскрыт. [UR1](https://uralsib.ru/business/ved), [UR3](https://uralsib.ru/api/directory-engine/files/rates/usloviya-konversionnyh-sdelok_oual3gi4.pdf) |
| Капитал / нагрузка на ликвидность | не раскрыто | Аллокация банковского капитала не раскрыта. [UR1](https://uralsib.ru/business/ved), [UR3](https://uralsib.ru/api/directory-engine/files/rates/usloviya-konversionnyh-sdelok_oual3gi4.pdf) |
| ДБО / терминал | подтверждено | Онлайн-котировки и ордера в интернет-банке. [UR1](https://uralsib.ru/business/ved), [UR3](https://uralsib.ru/api/directory-engine/files/rates/usloviya-konversionnyh-sdelok_oual3gi4.pdf) |
| Торговый API | не раскрыто | Клиентский торговый API для CNY OTC не раскрыт. [UR1](https://uralsib.ru/business/ved), [UR3](https://uralsib.ru/api/directory-engine/files/rates/usloviya-konversionnyh-sdelok_oual3gi4.pdf) |
| Менеджер / дилер / брокер | подтверждено | Дилеры, контакты валютного хеджирования и персональный валютный контролёр. [UR1](https://uralsib.ru/business/ved), [UR4](https://uralsib.ru/blog/uralsib-zapustil-novye-servisy-dlya-uchastnikov-ved), [UR5](https://uralsib.ru/faq/business/ved/obschaya-informatsiya/kontakty-dlya-dopolnitelnykh-konsultatsiy) |
| Обучение | подтверждено | Публичная справка по инструментам, в том числе по открытой дате, опционам и свопу. [UR2](https://uralsib.ru/faq/business/ved) |
| Аналитика / контроль / сопровождение | подтверждено | Экспертиза ВЭД-контрактов, документы, персональный валютный контроль и отдельные консультации по хеджу. [UR1](https://uralsib.ru/business/ved), [UR4](https://uralsib.ru/blog/uralsib-zapustil-novye-servisy-dlya-uchastnikov-ved), [UR5](https://uralsib.ru/faq/business/ved/obschaya-informatsiya/kontakty-dlya-dopolnitelnykh-konsultatsiy) |
| Целевой сегмент | подтверждено | Корпоративные участники ВЭД, импортеры, экспортеры и ИП для сервисов ВЭД. [UR1](https://uralsib.ru/business/ved), [UR4](https://uralsib.ru/blog/uralsib-zapustil-novye-servisy-dlya-uchastnikov-ved) |
| Отрасль / специализация | не раскрыто | Отраслевая специализация хеджей/порог допуска не раскрыты. [UR1](https://uralsib.ru/business/ved) |
| Заявленное позиционирование | подтверждено | Сервис ВЭД, экспертиза договора и форвард с выбором формата даты. [UR1](https://uralsib.ru/business/ved), [UR4](https://uralsib.ru/blog/uralsib-zapustil-novye-servisy-dlya-uchastnikov-ved) |
| Типовой сценарий | подтверждено | Импортер с неопределённой датой платежа выясняет условия форварда с открытой датой. [UR1](https://uralsib.ru/business/ved), [UR2](https://uralsib.ru/faq/business/ved) |

### Банк «Санкт-Петербург»

Исходная линейка банка и каналы, на которых строится FX Control.

| Поле | Статус | Свидетельство и первичный источник |
| --- | --- | --- |
| Конвертация | подтверждено | Безналичная конверсия CNY через «Котировальную доску», актуальные котировки. [BS1](https://www.bspb.ru/foreign-trade/hedge), [BS4](https://www.bspb.ru/foreign-trade/ved-china) |
| Поставочный FX-forward | подтверждено | Поставочный форвард присутствует в витрине с примером CNY. Срок, канал и параметры требуют исполнимой котировки. [BS1](https://www.bspb.ru/foreign-trade/hedge), [BS2](https://cdn.bspb.ru/pravila_ib_i2b_28_04_2026_84077be70b.pdf), [BS4](https://www.bspb.ru/foreign-trade/ved-china) |
| Расчётный FX-forward (NDF) | подтверждено | i2B «Котировальная доска» дает USDRUB, EURRUB, EURUSD в п. 3.1.35. Отдельно см. статус CNY. [BS2](https://cdn.bspb.ru/pravila_ib_i2b_28_04_2026_84077be70b.pdf), [BS3](https://cdn.bspb.ru/pravila_ib_i2b_e3ae85cd70.pdf) |
| Валютный своп (FX swap) | требуется уточнение | FX swap buy-sell описан в банковском материале. Применимость для нужной сделки уточняется. CCIRS — другой продукт. [BS9](https://www.bspb.ru/foreign-trade/hedge-risks), [BS10](https://www.bspb.ru/blog/ved/cur-insurance) |
| Валютный опцион | подтверждено | Call, коридор и варианты для экспортера, CNY/EUR/USD в витрине. Сложные инструменты через трейдера. [BS1](https://www.bspb.ru/foreign-trade/hedge) |
| Биржевые валютные фьючерсы | не раскрыто | Корпоративный маршрут на CNY фьючерс через брокера БСПБ в рассмотренных материалах не подтверждён. [BS1](https://www.bspb.ru/foreign-trade/hedge), [BS7](https://www.bspb.ru/foreign-trade) |
| Минимальная сумма / лот | подтверждено | Витрина FWD/NDF от 0,01 USD, валютные опционы от 100 тыс. USD; витрина конверсии CNY от 1 ₽ / 0,01 CNY. Порог живой котировки подтвердить. [BS1](https://www.bspb.ru/foreign-trade/hedge), [BS4](https://www.bspb.ru/foreign-trade/ved-china) |
| Срок / экспирация | подтверждено | На витрине FWD/NDF от 1 дня, опцион от 3 дней. Для NDF в i2B п. 3.1.35 устанавливает не раньше 4-го рабочего дня. [BS1](https://www.bspb.ru/foreign-trade/hedge), [BS2](https://cdn.bspb.ru/pravila_ib_i2b_28_04_2026_84077be70b.pdf), [BS3](https://cdn.bspb.ru/pravila_ib_i2b_e3ae85cd70.pdf) |
| Валюты и пары | требуется уточнение | CNY FWD есть в китайской витрине. NDF CNY есть в примере и в определении CNYFIX, но не в перечне п. 3.1.35. Запросить условия голосового OTC. [BS1](https://www.bspb.ru/foreign-trade/hedge), [BS2](https://cdn.bspb.ru/pravila_ib_i2b_28_04_2026_84077be70b.pdf), [BS3](https://cdn.bspb.ru/pravila_ib_i2b_e3ae85cd70.pdf), [BS4](https://www.bspb.ru/foreign-trade/ved-china) |
| Цены, спреды и комиссии | требуется уточнение | Витрина говорит об отсутствии отдельной платы за форвард. Форвардный курс, bid/ask и условия обеспечения определяют экономическую цену. [BS1](https://www.bspb.ru/foreign-trade/hedge), [BS2](https://cdn.bspb.ru/pravila_ib_i2b_28_04_2026_84077be70b.pdf), [BS8](https://www.bspb.ru/foreign-trade/tariffs) |
| Договор / документация | подтверждено | ДБО и соглашение «Котировальная доска» с формой подтверждения/уведомлением, для голосового канала RISDA по запросу. [BS1](https://www.bspb.ru/foreign-trade/hedge), [BS2](https://cdn.bspb.ru/pravila_ib_i2b_28_04_2026_84077be70b.pdf), [BS3](https://cdn.bspb.ru/pravila_ib_i2b_e3ae85cd70.pdf) |
| Допуск и требования | подтверждено | Для «Доски» счета и подключение i2B; по витрине голосовой канал доступен с RISDA без обязательного счёта в БСПБ. [BS1](https://www.bspb.ru/foreign-trade/hedge), [BS2](https://cdn.bspb.ru/pravila_ib_i2b_28_04_2026_84077be70b.pdf), [BS11](https://www.bspb.ru/business/distant-services) |
| Обеспечение / ГО | подтверждено | Прил. 16 предусматривает маржевой взнос в подтверждении. Сумму рассчитывает банк по условиям сделки. [BS2](https://cdn.bspb.ru/pravila_ib_i2b_28_04_2026_84077be70b.pdf), [BS3](https://cdn.bspb.ru/pravila_ib_i2b_e3ae85cd70.pdf) |
| Кредитный / торговый лимит | не раскрыто | Сумма и правила OTC лимита конкретного клиента для CNY не раскрыты публично. [BS1](https://www.bspb.ru/foreign-trade/hedge), [BS2](https://cdn.bspb.ru/pravila_ib_i2b_28_04_2026_84077be70b.pdf), [BS3](https://cdn.bspb.ru/pravila_ib_i2b_e3ae85cd70.pdf) |
| Переоценка / дополнительные взносы | подтверждено | Прил. 16, п. 3.3: договорный механизм дополнительного маржевого взноса. Фактический уровень определяет банк. [BS2](https://cdn.bspb.ru/pravila_ib_i2b_28_04_2026_84077be70b.pdf), [BS3](https://cdn.bspb.ru/pravila_ib_i2b_e3ae85cd70.pdf) |
| Капитал / нагрузка на ликвидность | не раскрыто | Риск-капитал конкретных банковских сделок не опубликован. Модельные 12 млн ₽ не относятся к публичным лимитам БСПБ. [BS1](https://www.bspb.ru/foreign-trade/hedge), [BS2](https://cdn.bspb.ru/pravila_ib_i2b_28_04_2026_84077be70b.pdf) |
| ДБО / терминал | подтверждено | Корпоративное ДБО i2B и «Котировальная доска», ВЭД.Alert и проверка документов. [BS2](https://cdn.bspb.ru/pravila_ib_i2b_28_04_2026_84077be70b.pdf), [BS5](https://www.bspb.ru/foreign-trade/service), [BS6](https://www.bspb.ru/foreign-trade/ved-alert-about), [BS11](https://www.bspb.ru/business/distant-services) |
| Торговый API | не раскрыто | Внешний API для заключения корпоративного CNY OTC не раскрыт. [BS1](https://www.bspb.ru/foreign-trade/hedge), [BS2](https://cdn.bspb.ru/pravila_ib_i2b_28_04_2026_84077be70b.pdf), [BS11](https://www.bspb.ru/business/distant-services) |
| Менеджер / дилер / брокер | подтверждено | Менеджер ВЭД как канал сопровождения, звонок трейдеру — действующий путь заключения. [BS1](https://www.bspb.ru/foreign-trade/hedge), [BS7](https://www.bspb.ru/foreign-trade) |
| Обучение | подтверждено | Центр ВЭД360, консультации и мероприятия с экспертами ВЭД. [BS7](https://www.bspb.ru/foreign-trade) |
| Аналитика / контроль / сопровождение | подтверждено | ВЭД.Alert и уведомления о валютном контроле, ожидаемых сроках/СПД, проверка перед отправкой, учёт договора. [BS5](https://www.bspb.ru/foreign-trade/service), [BS6](https://www.bspb.ru/foreign-trade/ved-alert-about), [BS7](https://www.bspb.ru/foreign-trade) |
| Целевой сегмент | подтверждено | Участники ВЭД, отдельно импортеры и экспортёры, есть линейка ВЭД с Китаем. [BS1](https://www.bspb.ru/foreign-trade/hedge), [BS4](https://www.bspb.ru/foreign-trade/ved-china), [BS7](https://www.bspb.ru/foreign-trade) |
| Отрасль / специализация | подтверждено | ВЭД с Китаем как географическая специализация витрины. Отраслевые пороги инструмента неизвестны. [BS4](https://www.bspb.ru/foreign-trade/ved-china), [BS7](https://www.bspb.ru/foreign-trade) |
| Заявленное позиционирование | подтверждено | Комплексный ВЭД-сервис, ДБО и голосовой доступ к индивидуальным сделкам. [BS1](https://www.bspb.ru/foreign-trade/hedge), [BS2](https://cdn.bspb.ru/pravila_ib_i2b_28_04_2026_84077be70b.pdf), [BS7](https://www.bspb.ru/foreign-trade) |
| Типовой сценарий | подтверждено | Фактический платеж CNY или рублёвый платёж с валютной оговоркой, если юридически и операционно пригодный инструмент подтверждён. [BS1](https://www.bspb.ru/foreign-trade/hedge), [BS2](https://cdn.bspb.ru/pravila_ib_i2b_28_04_2026_84077be70b.pdf), [BS3](https://cdn.bspb.ru/pravila_ib_i2b_e3ae85cd70.pdf), [BS4](https://www.bspb.ru/foreign-trade/ved-china) |

### Московская биржа через брокера

Реальная альтернатива банковскому OTC для компаний с учётом ликвидности и базиса.

| Поле | Статус | Свидетельство и первичный источник |
| --- | --- | --- |
| Конвертация | подтверждено | Валютная секция: поставочная конверсия CNY/RUB и другие разрешенные пары, через брокера с доступом. [MX7](https://www.moex.com/s135), [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/), [SV4](https://sovcombank.ru/corporate/broker/for-corporations) |
| Поставочный FX-forward | недоступно по опубликованным условиям | Индивидуальный банковский поставочный форвард не относится к биржевому контракту CR; OTC банк остаётся альтернативой. [MX1](https://www.moex.com/ru/derivatives/futures-on-currency/crz6), [MX3](https://www.moex.com/a3873) |
| Расчётный FX-forward (NDF) | недоступно по опубликованным условиям | Индивидуальный OTC NDF вне стандартного биржевого канала. Расчётный CNY фьючерс — отдельная конструкция. [MX1](https://www.moex.com/ru/derivatives/futures-on-currency/crz6), [MX3](https://www.moex.com/a3873), [MX8](https://www.moex.com/ru/derivatives/money/currency/) |
| Валютный своп (FX swap) | подтверждено | Валютная секция MOEX публикует CNY/RUB свопы; клиентский доступ зависит от брокера и тарифа. [MX7](https://www.moex.com/s135) |
| Валютный опцион | подтверждено | На MOEX есть биржевые опционы на CNY/RUB. OTC опцион с индивидуальными условиями рассматривается отдельно. [MX8](https://www.moex.com/ru/derivatives/money/currency/) |
| Биржевые валютные фьючерсы | подтверждено | Расчётные CR и CNYRUBF через брокера. По срочной серии базовый актив CNY/RUB, без физической поставки валюты. [MX1](https://www.moex.com/ru/derivatives/futures-on-currency/crz6), [MX2](https://www.moex.com/ru/derivatives/perpetual-futures/CNYRUBF), [MX3](https://www.moex.com/a3873), [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/), [SV4](https://sovcombank.ru/corporate/broker/for-corporations) |
| Минимальная сумма / лот | подтверждено | 1 контракт = 1 000 CNY; тик = 0,001 ₽/CNY и 1 ₽/контракт. [MX1](https://www.moex.com/ru/derivatives/futures-on-currency/crz6), [MX2](https://www.moex.com/ru/derivatives/perpetual-futures/CNYRUBF), [MX3](https://www.moex.com/a3873) |
| Срок / экспирация | подтверждено | CR — срочные серии с датой и расчётом по CNYFIXME, CNYRUBF — 1 день с автопролонгацией и фандингом. [MX1](https://www.moex.com/ru/derivatives/futures-on-currency/crz6), [MX2](https://www.moex.com/ru/derivatives/perpetual-futures/CNYRUBF), [MX4](https://www.moex.com/a113), [MX9](https://www.moex.com/ru/derivatives/futures-on-currency/crh7), [MX10](https://www.moex.com/ru/derivatives/futures-on-currency/crm7), [MX11](https://www.moex.com/ru/derivatives/futures-on-currency/cru7), [MX12](https://www.moex.com/n104130?nt=112), [MX15](https://www.moex.com/en/derivatives/futures-on-currency/crz7), [MX16](https://www.moex.com/en/derivatives/futures-on-currency/crh8) |
| Валюты и пары | подтверждено | CNY/RUB у CR и CNYRUBF; широкая линейка других валют на срочном и валютном рынках. [MX3](https://www.moex.com/a3873), [MX7](https://www.moex.com/s135), [MX8](https://www.moex.com/ru/derivatives/money/currency/) |
| Цены, спреды и комиссии | подтверждено | Есть датированные расчётные цены и сборы в карточках. Биржа/НКЦ и брокер тарифицируют отдельно. Пример ставки брокера ГПБ — опубликованная таблица, не общая цена. [MX1](https://www.moex.com/ru/derivatives/futures-on-currency/crz6), [MX2](https://www.moex.com/ru/derivatives/perpetual-futures/CNYRUBF), [MX5](https://www.moex.com/a90), [GP5](https://www.gazprombank.ru/corporate/page/brokerage-service/trading-in-markets/) |
| Договор / документация | подтверждено | Брокерское открытие счёта и допуск к срочной секции, регламент брокера и спецификация MOEX/НКЦ. [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/), [SV4](https://sovcombank.ru/corporate/broker/for-corporations), [MX3](https://www.moex.com/a3873), [MX6](https://www.nationalclearingcentre.ru/catalog/030902) |
| Допуск и требования | подтверждено | Юрлицо обращается к брокеру, открывает счёт, получает доступ к секции и пополняет обеспечение. Допуск к коду инструмента проверить у брокера. [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/), [SV4](https://sovcombank.ru/corporate/broker/for-corporations), [MX6](https://www.nationalclearingcentre.ru/catalog/030902) |
| Обеспечение / ГО | подтверждено | ГО в рублях на контракт, отдельные ставки long/short и уровни концентрации. Брокерский уровень зависит от категории клиента. [MX1](https://www.moex.com/ru/derivatives/futures-on-currency/crz6), [MX2](https://www.moex.com/ru/derivatives/perpetual-futures/CNYRUBF), [MX6](https://www.nationalclearingcentre.ru/catalog/030902), [MX13](https://www.moex.com/ru/derivatives/go_futures.aspx) |
| Кредитный / торговый лимит | требуется уточнение | Биржевое ГО и доступ брокера отличаются от банковского двустороннего кредитного лимита. Опциональный брокерский кредит проверяется отдельно. [MX6](https://www.nationalclearingcentre.ru/catalog/030902), [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/), [SV4](https://sovcombank.ru/corporate/broker/for-corporations) |
| Переоценка / дополнительные взносы | подтверждено | Вариационная маржа приводит к регулярным денежным списаниям/зачислениям; возможны изменение ГО и довнесение средств. [MX4](https://www.moex.com/a113), [MX6](https://www.nationalclearingcentre.ru/catalog/030902), [MX13](https://www.moex.com/ru/derivatives/go_futures.aspx), [RS4](https://www.rshb.ru/api/v1/storage/1167f99c-60d7-4f6e-ab31-1610475e8938/attachment) |
| Капитал / нагрузка на ликвидность | подтверждено | У клиента блокируется ГО и нужен запас на отрицательную вариационную маржу/расширение ГО. Аллокация капитала брокера не определялась. [MX1](https://www.moex.com/ru/derivatives/futures-on-currency/crz6), [MX2](https://www.moex.com/ru/derivatives/perpetual-futures/CNYRUBF), [MX4](https://www.moex.com/a113), [MX6](https://www.nationalclearingcentre.ru/catalog/030902) |
| ДБО / терминал | подтверждено | Брокерский терминал/клиент-банк, например GPB-i-Trade и ГПБ Бизнес-Онлайн. [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/), [SV4](https://sovcombank.ru/corporate/broker/for-corporations) |
| Торговый API | требуется уточнение | Доступ к ордерному API зависит от брокера. Рыночные данные биржи сами по себе не дают торгового доступа. [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/), [MX1](https://www.moex.com/ru/derivatives/futures-on-currency/crz6), [MX2](https://www.moex.com/ru/derivatives/perpetual-futures/CNYRUBF) |
| Менеджер / дилер / брокер | подтверждено | Брокер юрлица. Возможны терминал и телефон по конкретному регламенту. [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/), [SV4](https://sovcombank.ru/corporate/broker/for-corporations) |
| Обучение | подтверждено | MOEX публикует методические материалы по валютной защите, доступ к сопровождению зависит от брокера. [MX8](https://www.moex.com/ru/derivatives/money/currency/), [MX14](https://www.moex.com/files/4wcyvgrax6jeavhgvrcq7t29w6), [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/) |
| Аналитика / контроль / сопровождение | подтверждено | Публичные котировки с задержкой, риск-параметры и спецификации; клиент самостоятельно сопоставляет базис, срок и денежный риск. [MX1](https://www.moex.com/ru/derivatives/futures-on-currency/crz6), [MX2](https://www.moex.com/ru/derivatives/perpetual-futures/CNYRUBF), [MX4](https://www.moex.com/a113), [MX6](https://www.nationalclearingcentre.ru/catalog/030902) |
| Целевой сегмент | подтверждено | Юрлица с брокерским счётом и готовностью управлять ГО и вариационной маржой. [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/), [GP5](https://www.gazprombank.ru/corporate/page/brokerage-service/trading-in-markets/), [SV4](https://sovcombank.ru/corporate/broker/for-corporations) |
| Отрасль / специализация | не раскрыто | Для базовых CNY контрактов биржа не публикует отраслевую специализацию клиента. Требования конкретного брокера проверяются отдельно. [MX3](https://www.moex.com/a3873), [GP4](https://www.gazprombank.ru/corporate/page/brokerage-service/) |
| Заявленное позиционирование | подтверждено | Стандартизированные срок/лот, биржевая цена и клиринг с НКЦ, отдельная стоимость брокера. [MX1](https://www.moex.com/ru/derivatives/futures-on-currency/crz6), [MX3](https://www.moex.com/a3873), [MX4](https://www.moex.com/a113), [MX5](https://www.moex.com/a90), [GP5](https://www.gazprombank.ru/corporate/page/brokerage-service/trading-in-markets/) |
| Типовой сценарий | подтверждено | Импортёр снижает риск роста CNY длинными фьючерсами. Если нужны CNY для платежа, конверсия выполняется отдельно. [MX1](https://www.moex.com/ru/derivatives/futures-on-currency/crz6), [MX3](https://www.moex.com/a3873), [MX7](https://www.moex.com/s135) |

Публикации, сроки и область доказательств см. в [реестре источников](../data/reference/source_register.csv).
