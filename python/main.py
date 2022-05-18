import os
import logging
import pathlib
import json
import sqlite3
import hashlib
from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

DBPATH = '../db/mercari.sqlite3'

app = FastAPI()
logger = logging.getLogger("uvicorn")
logger.level = logging.DEBUG
images = pathlib.Path(__file__).parent.resolve() / "image"
origins = [ os.environ.get('FRONT_URL', 'http://localhost:3000') ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET","POST","PUT","DELETE"],
    allow_headers=["*"],
)

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]

    return d

def sha256_filename(filename):
    logger.info(f"Image filename: {filename}")

    filename = os.path.splitext(filename)[0]
    result = hashlib.sha256(filename.encode("utf-8")).hexdigest()
    return result

@app.get("/")
def root():
    return {"message": "Hello, world!"}

@app.post("/items")
def add_item(name: str = Form(...), category: str = Form(...), image: UploadFile = Form(...)):

    logger.info(f"Receive item: {name} in {category}")

    #hash image filename by sha256
    hash_filename = sha256_filename(image.filename) + '.jpg'

    #fetch category id
    conn = sqlite3.connect(DBPATH)
    c = conn.cursor()
    category_id = c.execute("SELECT id FROM category WHERE name=?", (category,)).fetchone()

    if category_id is None:
        c.execute("INSERT INTO category(name) VALUES(?)", (category,))
        conn.commit()
        category_id = c.execute("SELECT id FROM category WHERE name=?", (category,)).fetchone()


    #new item
    item = (name, category_id[0], hash_filename)
    c.execute("INSERT INTO items VALUES (NULL,?,?,?)", item)
    conn.commit()

    conn.close()

    return {"message": f"item received: {name}"}

@app.get("/items")
def get_item():
    logger.info("List all items")
    conn = sqlite3.connect(DBPATH)
    conn.row_factory = dict_factory
    c = conn.cursor()
    c.execute("SELECT items.name, category.name AS category, items.image_filename FROM items INNER JOIN category ON items.category_id = category.id")
    items = c.fetchall()

    return {"item":items}

@app.get("/items/{item_id}")
def get_item_info(item_id):
    logger.info(f"List info of item {item_id}")
    conn = sqlite3.connect(DBPATH)
    conn.row_factory = dict_factory
    c = conn.cursor()
    c.execute("SELECT items.name, category.name AS category, items.image_filename FROM items INNER JOIN category ON items.category_id = category.id WHERE items.id = ?;", [item_id])
    item = c.fetchone()

    return item

@app.get("/search")
def get_item(keyword):
    logger.info(f"Search {keyword} items")
    conn = sqlite3.connect(DBPATH)
    conn.row_factory = dict_factory
    c = conn.cursor()
    c.execute("SELECT items.name, category.name AS category, items.image_filename FROM items INNER JOIN category ON items.category_id = category.id WHERE items.name LIKE ?;", ('%'+keyword+'%',))
    items = c.fetchall()

    return {"item":items}

@app.get("/image/{image_filename}")
async def get_image(image_filename):
    # Create image path
    image = images / image_filename

    if not image_filename.endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Image path does not end with .jpg")

    if not image.exists():
        logger.debug(f"Image not found: {image}")
        image = images / "default.jpg"

    return FileResponse(image)
