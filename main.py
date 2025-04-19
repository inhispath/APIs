import os
import sqlite3
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import subprocess
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests

# Base directory for the databases (adjust if needed)
BASE_DB_PATH = os.path.join("bible_databases", "formats", "sqlite")
# Global database (assumed to contain the translations and cross_references tables)
GLOBAL_DB_FILE = os.path.join(BASE_DB_PATH, "translations.db")

def rename_files_to_uppercase():
    try:
        subprocess.run(["python", "uppercase.py"], check=True)
        print("Files renamed to uppercase successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error during file renaming: {e}")

rename_files_to_uppercase()

app = FastAPI(
    title="Bible Databases API",
    description="API to provide access to the Scrollmapper Bible databases (using sqlite) with full functionality.",
    version="1.0.0"
)

# Allow CORS for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# A simple in-memory store for user annotations
ANNOTATIONS = []
annotation_id_counter = 1

# ------------------------
# Utility Database Functions
# ------------------------
def get_db_connection(db_path: str) -> sqlite3.Connection:
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail=f"Database file {db_path} not found")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def get_translation_db(translation_id: str) -> sqlite3.Connection:
    # Assume the file is named <translation_id>.db (case-insensitive match)
    file_name = f"{translation_id.upper()}.db"
    db_file = os.path.join(BASE_DB_PATH, file_name)
    return get_db_connection(db_file)

# ------------------------
# Data Models
# ------------------------
class Translation(BaseModel):
    translation: str
    title: str
    license: Optional[str]

class Book(BaseModel):
    id: int
    name: str

class ChapterInfo(BaseModel):
    chapter: int
    verse_count: int

class Verse(BaseModel):
    verse: int
    text: str

class Passage(BaseModel):
    translation: str
    book: str
    start_chapter: int
    start_verse: int
    end_chapter: int
    end_verse: int

class Annotation(BaseModel):
    id: int
    translation: str
    book: str
    chapter: int
    verse: int
    note: str

# ------------------------
# Global Endpoints
# ------------------------
@app.get("/translations", response_model=List[Translation])
def get_all_translations():
    """
    Returns a list of available Bible translations.
    Iterates over all .db files in the BASE_DB_PATH and reads the
    single row in the "translations" table from each.
    """
    translations_list = []
    for filename in os.listdir(BASE_DB_PATH):
        if filename.endswith(".db"):
            db_path = os.path.join(BASE_DB_PATH, filename)
            try:
                conn = get_db_connection(db_path)
                cursor = conn.cursor()
                # Assuming there is only one row in the translations table of each DB:
                cursor.execute("SELECT translation, title, license FROM translations LIMIT 1")
                row = cursor.fetchone()
                if row:
                    translations_list.append(Translation(**dict(row)))
            except Exception as e:
                # Optionally log the error and continue with other files
                print(f"Error reading {filename}: {e}")
            finally:
                if 'conn' in locals():
                    conn.close()
    if not translations_list:
        raise HTTPException(status_code=404, detail="No translations found")
    return translations_list


# ------------------------
# Translation-Specific Endpoints
# ------------------------
@app.get("/translations/{translation_id}/books", response_model=List[Book])
def get_books_for_translation(translation_id: str):
    """
    Returns the list of books for the given translation.
    Assumes that the books table is named '<translation_id>_books' in the DB.
    """
    conn = get_translation_db(translation_id)
    table_name = f"{translation_id.upper()}_books"
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT id, name FROM {table_name} ORDER BY id")
        rows = cursor.fetchall()
        

        books = [Book(id=row["id"], name=row["name"]) for row in rows]
        return books
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Error fetching books: {e}")
    finally:
        conn.close()

@app.get("/translations/{translation_id}/books/{book_id}/chapters", response_model=Dict[int, int])
def get_chapter_counts(translation_id: str, book_id: int):
    """
    Returns chapter information for a specified book.
    Query the verses table for count of verses per chapter.
    Assumes verses table is named '<translation_id>_verses'
    """
    conn = get_translation_db(translation_id)
    table_name = f"{translation_id.upper()}_verses"
    cursor = conn.cursor()
    try:
        query = f"""
            SELECT chapter, COUNT(*) as verse_count
            FROM {table_name}
            WHERE book_id = ?
            GROUP BY chapter
            ORDER BY chapter
        """
        cursor.execute(query, (book_id,))
        rows = cursor.fetchall()
        # Return as dictionary: chapter -> verse_count
        result = {row["chapter"]: row["verse_count"] for row in rows}
        if not result:
            raise HTTPException(status_code=404, detail="No chapters found for given book")
        return result
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Error fetching chapters: {e}")
    finally:
        conn.close()

@app.get("/translations/{translation_id}/books/{book_id}/chapters/{chapter}/verses", response_model=List[Verse])
def get_verses_in_chapter(translation_id: str, book_id: int, chapter: int):
    """
    Returns all verses in a given chapter for a given book/translation.
    """
    conn = get_translation_db(translation_id)
    table_name = f"{translation_id.upper()}_verses"
    cursor = conn.cursor()
    try:
        query = f"""
            SELECT verse, text
            FROM {table_name}
            WHERE book_id = ? AND chapter = ?
            ORDER BY verse
        """
        cursor.execute(query, (book_id, chapter))
        rows = cursor.fetchall()
        verses = [Verse(verse=row["verse"], text=row["text"]) for row in rows]
        if not verses:
            raise HTTPException(status_code=404, detail="No verses found for given chapter")
        return verses
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Error fetching verses: {e}")
    finally:
        conn.close()

@app.get("/translations/{translation_id}/books/{book_id}/chapters/{chapter}/verses/{verse}", response_model=Verse)
def get_single_verse(translation_id: str, book_id: int, chapter: int, verse: int):
    """
    Returns a specific verse.
    """
    conn = get_translation_db(translation_id)
    table_name = f"{translation_id.upper()}_verses"
    cursor = conn.cursor()
    try:
        query = f"""
            SELECT verse, text
            FROM {table_name}
            WHERE book_id = ? AND chapter = ? AND verse = ?
        """
        cursor.execute(query, (book_id, chapter, verse))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Verse not found")
        return Verse(verse=row["verse"], text=row["text"])
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Error fetching verse: {e}")
    finally:
        conn.close()

# ------------------------
# Additional Endpoints
# ------------------------

@app.get("/search", response_model=List[Verse])
def search_verses(
    translation: str = Query(..., description="Translation identifier"),
    query: str = Query(..., description="Search keyword or phrase"),
    book: Optional[int] = Query(None, description="Optional book id to narrow search"),
):
    """
    Searches for verses matching a keyword/phrase.
    The search is run on the 'text' field of the verses.
    """
    conn = get_translation_db(translation)
    table_name = f"{translation.upper()}_verses"
    cursor = conn.cursor()
    try:
        sql = f"SELECT verse, text FROM {table_name} WHERE text LIKE ?"
        params = [f"%{query}%"]
        if book is not None:
            sql += " AND book_id = ?"
            params.append(book)
        sql += " ORDER BY chapter, verse LIMIT 100"
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        verses = [Verse(verse=row["verse"], text=row["text"]) for row in rows]
        return verses
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Error in search: {e}")
    finally:
        conn.close()

@app.get("/passage", response_model=List[Verse])
def get_passage(
    translation: str = Query(..., description="Translation identifier"),
    book: int = Query(..., description="Book id"),
    start_chapter: int = Query(..., description="Start chapter"),
    start_verse: int = Query(..., description="Start verse"),
    end_chapter: int = Query(..., description="End chapter"),
    end_verse: int = Query(..., description="End verse")
):
    """
    Returns a passage spanning one or more chapters.
    Assumes verses are stored in order. This endpoint returns all verses from the
    starting position to the ending position (inclusive).
    """
    conn = get_translation_db(translation)
    table_name = f"{translation.upper()}_verses"
    cursor = conn.cursor()
    try:
        # If the passage is within one chapter
        if start_chapter == end_chapter:
            query = f"""
                SELECT chapter, verse, text
                FROM {table_name}
                WHERE book_id = ? AND chapter = ? AND verse BETWEEN ? AND ?
                ORDER BY verse
            """
            cursor.execute(query, (book, start_chapter, start_verse, end_verse))
        else:
            # Passage across chapters: get verses in start_chapter, middle chapters, and end_chapter.
            query = f"""
                SELECT chapter, verse, text
                FROM {table_name}
                WHERE book_id = ? AND (
                    (chapter = ? AND verse >= ?) OR
                    (chapter > ? AND chapter < ?) OR
                    (chapter = ? AND verse <= ?)
                )
                ORDER BY chapter, verse
            """
            cursor.execute(query, (book, start_chapter, start_verse, start_chapter, end_chapter, end_chapter, end_verse))
        rows = cursor.fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail="Passage not found")
        verses = [Verse(verse=row["verse"], text=row["text"]) for row in rows]
        return verses
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Error fetching passage: {e}")
    finally:
        conn.close()

@app.get("/translations/{translation_id}/books/{book_id}/chapters/{chapter}/verses/{verse}/crossreferences")
def get_cross_references(translation_id: str, book_id: int, chapter: int, verse: int):
    """
    Returns cross-references for a given verse.
    Uses the global cross_references table in the translations.db.
    Note: The cross_references table stores data using book abbreviations.
    You might need to map the numeric book_id to a book abbreviation.
    For simplicity, this implementation assumes 'book_id' equals the abbreviation,
    or you implement your own mapping.
    """
    # For demonstration, we assume the book abbreviation is the same as the book_id string.
    # In practice, you should look up the book abbreviation from the books table.
    from_book = str(book_id)
    conn = get_db_connection(GLOBAL_DB_FILE)
    cursor = conn.cursor()
    try:
        query = """
            SELECT from_book, from_chapter, from_verse,
                   to_book, to_chapter, to_verse_start, to_verse_end, votes
            FROM cross_references
            WHERE from_book = ? AND from_chapter = ? AND from_verse = ?
            ORDER BY votes DESC
        """
        cursor.execute(query, (from_book, chapter, verse))
        rows = cursor.fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail="No cross references found")
        # Return list of dicts
        results = [dict(row) for row in rows]
        return results
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Error fetching cross references: {e}")
    finally:
        conn.close()

@app.get("/translations/{translation_id}/stats")
def get_translation_stats(translation_id: str):
    """
    Returns statistics for a translation: number of books, total chapters, total verses.
    """
    # Get books count from the translation database
    conn = get_translation_db(translation_id)
    cursor = conn.cursor()
    books_table = f"{translation_id.upper()}_books"
    verses_table = f"{translation_id.upper()}_verses"
    try:
        cursor.execute(f"SELECT COUNT(*) as count FROM {books_table}")
        books_count = cursor.fetchone()["count"]

        # Total chapters: distinct chapters count across all books
        cursor.execute(f"SELECT COUNT(DISTINCT chapter) as count FROM {verses_table}")
        chapters_count = cursor.fetchone()["count"]

        # Total verses: sum of verses
        cursor.execute(f"SELECT COUNT(*) as count FROM {verses_table}")
        verses_count = cursor.fetchone()["count"]

        stats = {
            "books_count": books_count,
            "chapters_count": chapters_count,
            "verses_count": verses_count
        }
        return stats
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {e}")
    finally:
        conn.close()

@app.get("/compare")
def compare_translations(
    translation1: str = Query(..., description="First translation identifier"),
    translation2: str = Query(..., description="Second translation identifier"),
    book: int = Query(..., description="Book id"),
    chapter: int = Query(..., description="Chapter number"),
    verse: Optional[int] = Query(None, description="Optional verse number for comparison")
):
    """
    Compares a verse (or an entire chapter) between two translations.
    Returns a side-by-side result.
    """
    result = {}
    for t in [translation1, translation2]:
        conn = get_translation_db(t)
        table_name = f"{t.upper()}_verses"
        cursor = conn.cursor()
        try:
            if verse:
                query = f"""
                    SELECT verse, text
                    FROM {table_name}
                    WHERE book_id = ? AND chapter = ? AND verse = ?
                """
                cursor.execute(query, (book, chapter, verse))
                row = cursor.fetchone()
                result[t.upper()] = dict(row) if row else "Verse not found"
            else:
                query = f"""
                    SELECT chapter, verse, text
                    FROM {table_name}
                    WHERE book_id = ? AND chapter = ?
                    ORDER BY verse
                """
                cursor.execute(query, (book, chapter))
                rows = cursor.fetchall()
                result[t.upper()] = [dict(r) for r in rows]
        except sqlite3.Error as e:
            result[t.upper()] = f"Error: {e}"
        finally:
            conn.close()
    return result

# ------------------------
# User Annotations Endpoints (In-Memory)
# ------------------------
@app.post("/annotations", response_model=Annotation)
def add_annotation(translation: str, book: int, chapter: int, verse: int, note: str):
    """
    Add an annotation for a specific verse.
    (This implementation stores annotations in memory.)
    """
    global annotation_id_counter
    new_annotation = {
        "id": annotation_id_counter,
        "translation": translation.upper(),
        "book": str(book),  # ideally this would be a book abbreviation
        "chapter": chapter,
        "verse": verse,
        "note": note
    }
    ANNOTATIONS.append(new_annotation)
    annotation_id_counter += 1
    return new_annotation

@app.get("/annotations", response_model=List[Annotation])
def get_annotations(
    translation: Optional[str] = Query(None, description="Filter by translation"),
    book: Optional[int] = Query(None, description="Filter by book"),
    chapter: Optional[int] = Query(None, description="Filter by chapter"),
    verse: Optional[int] = Query(None, description="Filter by verse")
):
    """
    Returns all annotations (optionally filtered by translation, book, chapter, or verse).
    """
    filtered = ANNOTATIONS
    if translation:
        filtered = [a for a in filtered if a["translation"] == translation.upper()]
    if book is not None:
        filtered = [a for a in filtered if int(a["book"]) == book]
    if chapter is not None:
        filtered = [a for a in filtered if a["chapter"] == chapter]
    if verse is not None:
        filtered = [a for a in filtered if a["verse"] == verse]
    return filtered


@app.get("/translations/{translation_id}/books/{book_id}/chapters/{chapter}/verses/{verse}/quote-image")
def get_verse_quote_image(translation_id: str, book_id: int, chapter: int, verse: int):
    """
    Returns a verse as a quote image (1200x630 pixels).
    Gets the same verse as the single verse endpoint but returns it as an image with
    the verse text overlaid on the Michelangelo Creation of Adam painting.
    """
    # Get the verse text using the existing functionality
    conn = get_translation_db(translation_id)
    table_name = f"{translation_id.upper()}_verses"
    books_table = f"{translation_id.upper()}_books"
    cursor = conn.cursor()
    try:
        # Get the verse text
        query = f"""
            SELECT verse, text
            FROM {table_name}
            WHERE book_id = ? AND chapter = ? AND verse = ?
        """
        cursor.execute(query, (book_id, chapter, verse))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Verse not found")
        
        verse_text = row["text"]
        
        # Get the book name
        query = f"""
            SELECT name
            FROM {books_table}
            WHERE id = ?
        """
        cursor.execute(query, (book_id,))
        book_row = cursor.fetchone()
        book_name = book_row["name"] if book_row else f"Book {book_id}"
        
        # Create the image dimensions
        img_width, img_height = 1200, 630
        
        # Get the background image
        background_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Michelangelo_-_Creation_of_Adam_%28cropped%29.jpg/960px-Michelangelo_-_Creation_of_Adam_%28cropped%29.jpg"
        try:
            response = requests.get(background_url, stream=True)
            response.raise_for_status()
            bg_img = Image.open(BytesIO(response.content))
            # Resize and crop to fit our dimensions
            bg_ratio = bg_img.width / bg_img.height
            target_ratio = img_width / img_height
            
            if bg_ratio > target_ratio:
                # Background is wider, crop width
                new_width = int(bg_img.height * target_ratio)
                left = (bg_img.width - new_width) // 2
                bg_img = bg_img.crop((left, 0, left + new_width, bg_img.height))
            else:
                # Background is taller, crop height
                new_height = int(bg_img.width / target_ratio)
                top = (bg_img.height - new_height) // 2
                bg_img = bg_img.crop((0, top, bg_img.width, top + new_height))
            
            # Resize to our target dimensions
            bg_img = bg_img.resize((img_width, img_height), Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS)
            
            # Create a new image from the background
            img = bg_img.copy()
        except Exception as e:
            # If there's any issue with the background, create a solid color background
            print(f"Error loading background image: {e}")
            img = Image.new('RGB', (img_width, img_height), color="#FFFBF7")
        
        # Create a semi-transparent overlay for better text visibility
        overlay = Image.new('RGBA', (img_width, img_height), (255, 255, 255, 180))
        img = Image.alpha_composite(img.convert('RGBA'), overlay)
        img = img.convert('RGB')  # Convert back to RGB for drawing text
        
        draw = ImageDraw.Draw(img)
        
        # Try to load nice fonts, fall back to default if not available
        try:
            title_font = ImageFont.truetype("AlbertSans-Bold.ttf", 48)
            verse_font = ImageFont.truetype("AlbertSans-Regular.ttf", 36)
            button_font = ImageFont.truetype("AlbertSans-Regular.ttf", 24)
        except IOError:
            title_font = ImageFont.load_default()
            verse_font = ImageFont.load_default()
            button_font = ImageFont.load_default()
        
        # Draw the title (book name, chapter, verse)
        title_text = f"{book_name} {chapter}:{verse}"
        title_width = draw.textlength(title_text, font=title_font)
        title_x = (img_width - title_width) // 2
        title_y = 220  # Position from top
        draw.text((title_x, title_y), title_text, font=title_font, fill="#000000")
        
        # Wrap and draw the verse text in italics
        max_width = img_width * 0.8  # Use 80% of the image width for text
        lines = []
        words = verse_text.split()
        current_line = words[0]
        
        for word in words[1:]:
            test_line = current_line + " " + word
            text_width = draw.textlength(test_line, font=verse_font)
            if text_width <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        
        lines.append(current_line)  # Add the last line
        
        # Calculate position to center the verse text block
        verse_y = img_height // 2 - (len(lines) * 50) // 2 + 30
        
        # Draw each line centered with italic styling
        for line in lines:
            text_width = draw.textlength(line, font=verse_font)
            text_x = (img_width - text_width) // 2
            draw.text((text_x, verse_y), line, font=verse_font, fill="#000000")
            verse_y += 50  # Line spacing

        # Add a watermark
        watermark_text = "inhispath.com"
        watermark_width = draw.textlength(watermark_text, font=button_font)
        watermark_x = img_width - watermark_width - 20
        watermark_y = img_height - 40
        draw.text((watermark_x, watermark_y), watermark_text, font=button_font, fill="#333")
        
        # Convert the image to bytes
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        # Return the image
        return Response(content=img_byte_arr.getvalue(), media_type="image/png")
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Error generating quote image: {e}")
    finally:
        conn.close()

# ------------------------
# Run the App
# ------------------------
# To run the app, use: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)