import requests

BASE_URL = "http://127.0.0.1:8000"

def test_get_translations():
    url = f"{BASE_URL}/translations"
    response = requests.get(url)
    print("GET /translations")
    print("Status Code:", response.status_code)
    print("Response:", response.json())

def test_get_books(translation):
    url = f"{BASE_URL}/translations/{translation}/books"
    response = requests.get(url)
    print(f"GET /translations/{translation}/books")
    print("Status Code:", response.status_code)
    print("Response:", response.json())

def test_get_chapter_counts(translation, book_id):
    url = f"{BASE_URL}/translations/{translation}/books/{book_id}/chapters"
    response = requests.get(url)
    print(f"GET /translations/{translation}/books/{book_id}/chapters")
    print("Status Code:", response.status_code)
    print("Response:", response.json())

def test_get_verses(translation, book_id, chapter):
    url = f"{BASE_URL}/translations/{translation}/books/{book_id}/chapters/{chapter}/verses"
    response = requests.get(url)
    print(f"GET /translations/{translation}/books/{book_id}/chapters/{chapter}/verses")
    print("Status Code:", response.status_code)
    print("Response:", response.json())

def test_get_single_verse(translation, book_id, chapter, verse):
    url = f"{BASE_URL}/translations/{translation}/books/{book_id}/chapters/{chapter}/verses/{verse}"
    response = requests.get(url)
    print(f"GET /translations/{translation}/books/{book_id}/chapters/{chapter}/verses/{verse}")
    print("Status Code:", response.status_code)
    print("Response:", response.json())

if __name__ == "__main__":
    # Test the /translations endpoint
    test_get_translations()

    # Replace the following parameters with valid values from your databases:
    sample_translation = "KJV"  # for example
    sample_book_id = 1          # e.g., Genesis (if id=1)
    sample_chapter = 1
    sample_verse = 1

    # Test other endpoints
    test_get_books(sample_translation)
    test_get_chapter_counts(sample_translation, sample_book_id)
    test_get_verses(sample_translation, sample_book_id, sample_chapter)
    test_get_single_verse(sample_translation, sample_book_id, sample_chapter, sample_verse)
