# Scrap Service

Exchange rate collection service. It dynamically walks through a folder
of **scrapers**, runs each one, and persists the results to the database
repository.

---

## 📋 Table of contents

- [What it does](#-what-it-does)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Usage](#-usage)
- [Project structure](#-project-structure)
- [How to add a scraper](#-how-to-add-a-scraper)
- [Environment variables](#-environment-variables)
- [Tests](#-tests)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 What it does

1. **Scans** the `scrapers/` folder looking for `.py` files.
2. **Imports** each scraper dynamically.
3. **Runs** the `get_cotization()` function of each one.
4. **Filters** the currencies of interest (USD, EUR).
5. **Persists** every rate into the repository (`CurrencyRepository`).

```
scrapers/          collector.py            repository
   │                    │                      │
   │  get_cotization()  │                      │
   ├───────────────────►│                      │
   │                    │      save(rate)      │
   │                    ├─────────────────────►│
   │                    │                      │
```

---

## ✅ Requirements

- **Python 3.10+**
- [**uv**](https://docs.astral.sh/uv/) (recommended) or `pip`

---

## 📦 Installation

### With uv (recommended)

```bash
git clone https://github.com/your-user/scrap-service.git
cd scrap-service
uv sync
```

### With pip

```bash
git clone https://github.com/your-user/scrap-service.git
cd scrap-service
python -m venv .venv
source .venv/bin/activate      # On Windows: .venv\Scripts\activate
pip install -e .
```

---

## 🚀 Usage

### Run the full pipeline

```bash
uv run python -m scrap_service.collector
```

Or if your file has a different name:

```bash
uv run python scrap_service/collector.py
```

### With verbose logging

```bash
uv run python -m scrap_service.collector --verbose
```

### From code

```python
from scrap_service.collector import update_data

results = update_data()
for house, result in results.items():
    print(f"{house}: {'OK' if result.ok else result.error}")
```

---

## 📁 Project structure

```
scrap-service/
├── scrap_service/
│   ├── __init__.py
│   ├── collector.py           ← orchestrator (this script)
│   └── repository/
│       ├── __init__.py
│       └── currency.py        ← CurrencyRepository
├── scrapers/                  ← (gitignored if private)
│   ├── __init__.py
│   ├── central_bank.py
│   ├── exchange_house_x.py
│   └── ...
├── data/
│   └── market-rates.json
├── tests/
│   └── test_collector.py
├── .env.example
├── .gitignore
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## 🧩 How to add a scraper

Create a `.py` file inside `scrapers/`. It must expose a
`get_cotization()` function that returns a dictionary shaped like this:

```python
# scrapers/my_exchange_house.py

def get_cotization() -> dict[str, dict]:
    """
    Returns the rates for this source.

    Returns
    -------
    dict
        Example:
        {
            "USD": {"buy": 1000.0, "sell": 1050.0, "source": "my_house"},
            "EUR": {"buy": 1100.0, "sell": 1150.0, "source": "my_house"},
        }
    """
    return {
        "USD": {"buy": 1000.0, "sell": 1050.0},
        "EUR": {"buy": 1100.0, "sell": 1150.0},
    }
```

### Rules

- The file name is used as the source identifier.
- Files starting with `_` (e.g. `__init__.py`, `_helpers.py`) are ignored.
- If a scraper raises an exception, it's logged but **won't break** the
  rest of the pipeline.
- If it returns `None` or `{}`, it's marked as empty and processing continues.

---

## 🔐 Environment variables

Copy `.env.example` to `.env` and fill it in:

```bash
cp .env.example .env
```

```env
# .env.example
DATABASE_URL=postgresql://user:pass@localhost:5432/rates
API_KEY=your_api_key_here
LOG_LEVEL=INFO
```

> ⚠️ **Never** commit your real `.env`. It's already in `.gitignore`.

---

## 🧪 Tests

```bash
uv run pytest
```

With coverage:

```bash
uv run pytest --cov=scrap_service
```

---

## 🤝 Contributing

1. Fork the repo.
2. Create a branch: `git checkout -b feature/new-scraper`
3. Commit: `git commit -m "add scraper for X"`
4. Push: `git push origin feature/new-scraper`
5. Open a Pull Request.

### Adding a new scraper via PR

- One file per source in `scrapers/`.
- Add a test in `tests/scrapers/` if possible.
- Document in the docstring which site it scrapes.

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 🗺️ Roadmap

- [ ] Support for more configurable currencies via `.env`
- [ ] Retry with exponential backoff per scraper
- [ ] Dry-run mode (`--dry-run`) to skip persistence
- [ ] Per-scraper duration metrics