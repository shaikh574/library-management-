
from flask import Flask, request, jsonify, render_template
import requests
import sqlite3

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS books
                 (id INTEGER PRIMARY KEY, title TEXT, author TEXT, isbn TEXT, quantity INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS members
                 (id INTEGER PRIMARY KEY, name TEXT, email TEXT, debt REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY, book_id INTEGER, member_id INTEGER, issue_date TEXT, return_date TEXT, fee REAL)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/books', methods=['GET', 'POST'])
def books():
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        c.execute("INSERT INTO books (title, author, isbn, quantity) VALUES (?, ?, ?, ?)",
                  (data['title'], data['author'], data['isbn'], data['quantity']))
        conn.commit()
        book_id = c.lastrowid
        conn.close()
        return jsonify({"id": book_id, **data}), 201
    
    elif request.method == 'GET':
        c.execute("SELECT * FROM books")
        books = [{"id": row[0], "title": row[1], "author": row[2], "isbn": row[3], "quantity": row[4]} for row in c.fetchall()]
        conn.close()
        return jsonify(books)

@app.route('/api/members', methods=['GET', 'POST'])
def members():
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        c.execute("INSERT INTO members (name, email, debt) VALUES (?, ?, ?)",
                  (data['name'], data['email'], 0))
        conn.commit()
        member_id = c.lastrowid
        conn.close()
        return jsonify({"id": member_id, **data, "debt": 0}), 201
    
    elif request.method == 'GET':
        c.execute("SELECT * FROM members")
        members = [{"id": row[0], "name": row[1], "email": row[2], "debt": row[3]} for row in c.fetchall()]
        conn.close()
        return jsonify(members)

@app.route('/api/issue_book', methods=['POST'])
def issue_book():
    data = request.json
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    

    c.execute("SELECT debt FROM members WHERE id = ?", (data['member_id'],))
    member_debt = c.fetchone()[0]
    if member_debt >= 500:
        conn.close()
        return jsonify({"error": "Member's debt is too high"}), 400
    

    c.execute("SELECT quantity FROM books WHERE id = ?", (data['book_id'],))
    book_quantity = c.fetchone()[0]
    if book_quantity <= 0:
        conn.close()
        return jsonify({"error": "Book is not available"}), 400
    
    
    c.execute("UPDATE books SET quantity = quantity - 1 WHERE id = ?", (data['book_id'],))
    c.execute("INSERT INTO transactions (book_id, member_id, issue_date) VALUES (?, ?, date('now'))",
              (data['book_id'], data['member_id']))
    conn.commit()
    conn.close()
    return jsonify({"message": "Book issued successfully"}), 200

@app.route('/api/return_book', methods=['POST'])
def return_book():
    data = request.json
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    

    c.execute("UPDATE books SET quantity = quantity + 1 WHERE id = ?", (data['book_id'],))
    c.execute("UPDATE transactions SET return_date = date('now'), fee = ? WHERE book_id = ? AND member_id = ? AND return_date IS NULL",
              (data['fee'], data['book_id'], data['member_id']))
    c.execute("UPDATE members SET debt = debt + ? WHERE id = ?", (data['fee'], data['member_id']))
    conn.commit()
    conn.close()
    return jsonify({"message": "Book returned successfully"}), 200

@app.route('/api/search_books', methods=['GET'])
def search_books():
    query = request.args.get('query', '')
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    c.execute("SELECT * FROM books WHERE title LIKE ? OR author LIKE ?", ('%'+query+'%', '%'+query+'%'))
    books = [{"id": row[0], "title": row[1], "author": row[2], "isbn": row[3], "quantity": row[4]} for row in c.fetchall()]
    conn.close()
    return jsonify(books)

@app.route('/api/import_books', methods=['POST'])
def import_books():
    data = request.json
    url = f"https://frappe.io/api/method/frappe-library?page=1&title={data.get('title', '')}&author={data.get('author', '')}"
    response = requests.get(url)
    books = response.json()['message']
    
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    for book in books[:int(data.get('count', 20))]:
        c.execute("INSERT INTO books (title, author, isbn, quantity) VALUES (?, ?, ?, ?)",
                  (book['title'], book['authors'], book['isbn'], 1))
    conn.commit()
    conn.close()
    
    return jsonify({"message": f"Imported {len(books)} books successfully"}), 200

if __name__ == '__main__':
    app.run(debug=True)