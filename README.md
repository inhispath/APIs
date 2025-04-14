# Bible API (SQLite-based)

This is a fully functional Python REST API for accessing Bible data using SQLite databases from the [Scrollmapper Bible Databases](https://github.com/scrollmapper/bible_databases) project.

It provides endpoints for retrieving available translations, books, chapters, and verses across multiple versions of the Bible.

## 🔧 Features

- 📖 List all available translations (acronym, title, license)
- 📚 Get all books from a specific translation
- 🔢 Get number of chapters for a book in a given translation
- 📝 Get all verses from a specific chapter
- 🔍 Get a specific verse


## 🚀 Getting Started

### 1. Clone the Bible Databases

```bash
git clone https://github.com/scrollmapper/bible_databases.git
```

Ensure the `bible_databases/formats/sqlite` folder contains `.db` files like `KJV.db`.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the API

```bash
uvicorn main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for the interactive Swagger documentation.

## 🛠️ Endpoints

| Method | Endpoint                                                                 | Description |
|--------|--------------------------------------------------------------------------|-------------|
| GET    | `/translations`                                                         | Returns all available Bible translations |
| GET    | `/translations/{translation}/books`                                     | Returns list of books for a translation |
| GET    | `/translations/{translation}/books/{book_id}/chapters`                 | Returns the number of chapters in a book |
| GET    | `/translations/{translation}/books/{book_id}/chapters/{chapter}/verses`| Returns all verses in a chapter |
| GET    | `/translations/{translation}/books/{book_id}/chapters/{chapter}/verses/{verse}` | Returns a specific verse |

## 🧪 Testing the API

Run the test script:

```bash
python test_api.py
```

Modify `sample_translation`, `sample_book_id`, `sample_chapter`, and `sample_verse` as needed for your data.

## 📜 License

This project utilizes public domain Bible databases from [Scrollmapper](https://github.com/scrollmapper/bible_databases). See their repo for license info per translation.

---

Happy reading ✨📖
