import os
import logging
import pathlib
import json
import sqlite3
import hashlib
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

DBPATH = '../db/mercari.sqlite3'

app = FastAPI()
logger = logging.getLogger("uvicorn")
logger.level = logging.INFO
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
        if col[0] == 'id':
            continue
        d[col[0]] = row[idx]

    return d

def sha256_filename(filepath):
    logger.info(f"Image path: {filepath}")

    filepath = os.path.splitext(filepath)[0]
    result = hashlib.sha256(filepath.encode("utf-8")).hexdigest()
    return result

@app.get("/")
def root():
    return {"message": "Hello, world!"}

@app.post("/items")
def add_item(name: str = Form(...), category: str = Form(...), image: str = Form(...)):
    logger.info(f"Receive item: {name} in {category}")

    #hash image file name by sha256
    hash_img = sha256_filename(image) + '.jpg'

    #new item
    item = (name, category, hash_img)

    conn = sqlite3.connect(DBPATH)
    c = conn.cursor()
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
    c.execute("SELECT * FROM items")
    items = c.fetchall()

    return {"item":items}

@app.get("/search")
def get_item(keyword):
    logger.info(f"Search {keyword} items")
    conn = sqlite3.connect(DBPATH)
    conn.row_factory = dict_factory
    c = conn.cursor()
    c.execute("SELECT name, category FROM items WHERE name LIKE ?;", ('%'+keyword+'%',))
    items = c.fetchall()

    return {"item":items}

@app.get("/image/{items_image}")
async def get_image(items_image):
    # Create image path
    image = images / items_image

    if not items_image.endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Image path does not end with .jpg")

    if not image.exists():
        logger.debug(f"Image not found: {image}")
        image = images / "default.jpg"

    return FileResponse(image)
