# Invoice State Machine

## States

| State     | Description                                         |
|-----------|-----------------------------------------------------|
| `PENDING` | Invoice created, awaiting validation and queueing   |
| `QUEUED`  | Validated and waiting for batch submission           |
| `SENT`    | XML generated and uploaded to Turnkey                |
| `ACKED`   | Accepted by the government eGUI platform             |

## Transitions

```
PENDING ──── validate ────► QUEUED
QUEUED  ──── submit  ────► SENT
SENT    ──── ack     ────► ACKED
```

## Error Transitions

```
PENDING ──── validation_fail ────► PENDING (stays, errors attached)
SENT    ──── reject          ────► QUEUED  (re-queued for retry after fix)
```

## Void States
For voided invoices, a parallel flow exists:

```
ACKED ──── void_requested ────► VOID_PENDING
VOID_PENDING ──── submit_void ────► VOID_SENT
VOID_SENT ──── void_acked ────► VOIDED
```

## Rules
- Only `PENDING` invoices can be edited
- `QUEUED` invoices can be pulled back to `PENDING` for corrections
- `SENT` invoices cannot be modified until a response is received
- `ACKED` invoices can only be voided (not edited)
- Void is only allowed before the filing period deadline (see `void-rules.md`)

## Codebase Reference
- Invoice model: `backend/domains/invoices/models.py`
- State transitions are enforced in service layer: `backend/domains/invoices/service.py`
