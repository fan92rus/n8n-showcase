# Демо 4 — Заказный пайплайн (webhook → CRM → Telegram)

Продвинутый пример: приём заказов из любой внешней системы (сайт, лендинг, 1С-выгрузка) через HTTP.

## Что показывает

- **Webhook API**: ваша система шлёт `POST /webhook/new-order`, n8n отвечает JSON'ом
- **Строгая валидация** (Code-node): order_id, email, сумма — мусор не проходит дальше и уходит в error-ветку
- **Маршрутизация по бизнес-правилу**: заказ ≥ 50 000 ₽ → мгновенный VIP-алерту админу
- **Идемпотентность**: Google Sheets `appendOrUpdate` с матчингом по `order_id` — повторная отправка не создаёт дубль
- **Уведомления**: менеджеру — каждый заказ, админу — только VIP

## Схема

```
Webhook POST /new-order
  → Валидация (throw при мусоре)
  → IF сумма ≥ 50к
      ├─ true:  TG-алерт админу ─┐
      └─ false:                  ├─→ Sheets (dedup order_id) → TG менеджеру → Response {ok:true}
```

## Настройка под себя

1. Импортируйте `workflows/04-order-pipeline.json`
2. Подключите креденшелы: Telegram Bot API, Google Sheets (OAuth2)
3. Заведите переменные окружения (Settings → Variables): `TG_ADMIN_CHAT_ID`, `TG_MANAGER_CHAT_ID`, `SHEET_ORDERS_ID`
4. В таблице Orders первая строка-заголовок: `order_id | email | customer | amount | amount_fmt | is_vip | received_at`
5. Активируйте — используйте Production URL вебхука в своей системе

## Тест

```bash
curl -X POST https://<ваш-n8n>/webhook/new-order \
  -H "Content-Type: application/json" \
  -d '{"order_id":"1001","email":"client@example.com","customer":"Иван","amount":75000}'
```

Ожидаемо: ответ `{"ok":true,"order_id":"1001",...}`, строка в таблице, два уведомления (VIP + менеджеру).
