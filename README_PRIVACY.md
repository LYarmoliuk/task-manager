# Privacy lab: як підключити

1. Скопіюйте в проєкт (зберігаючи структуру): `app/privacy/`, `tests/test_privacy_*.py`, `docs/pii_inventory.md`.
2. В кінець `app/main.py` додайте:

```python
from app.privacy.api import install_privacy

install_privacy(app)
```

3. Запуск тестів: `pytest -q`
4. Ручна перевірка (запуск: `uvicorn app.main:app`):

```powershell
curl.exe -H "Authorization: Bearer token-alice" http://127.0.0.1:8000/api/users/1/personal-data   # gitleaks:allow (синтетичний демо-токен)
curl.exe -H "Authorization: Bearer token-bob"   http://127.0.0.1:8000/api/users/1/personal-data   # 403 gitleaks:allow
curl.exe -X POST -H "Authorization: Bearer token-alice" http://127.0.0.1:8000/api/users/1/anonymize   # gitleaks:allow (синтетичний демо-токен)
```