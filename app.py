from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import sqlite3
import uuid
import os

app = Flask(__name__)
CORS(app)

DATABASE = 'expenses.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id TEXT PRIMARY KEY,
            amount DECIMAL(10,2) NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")

init_db()

def validate_expense_data(data):
    errors = []
    
    if 'amount' not in data:
        errors.append('Amount is required')
    else:
        try:
            amount = float(data['amount'])
            if amount <= 0:
                errors.append('Amount must be greater than 0')
            if amount > 9999999.99:
                errors.append('Amount is too large')
        except (ValueError, TypeError):
            errors.append('Invalid amount format')
    
    valid_categories = ['Food', 'Transport', 'Entertainment', 'Bills', 'Shopping', 'Healthcare', 'Other']
    if 'category' not in data:
        errors.append('Category is required')
    elif data['category'] not in valid_categories:
        errors.append(f'Invalid category. Must be one of: {", ".join(valid_categories)}')
    
    if 'description' not in data:
        errors.append('Description is required')
    elif len(data['description'].strip()) < 1:
        errors.append('Description must not be empty')
    elif len(data['description']) > 200:
        errors.append('Description must be less than 200 characters')
    
    if 'date' not in data:
        errors.append('Date is required')
    else:
        try:
            date_obj = datetime.strptime(data['date'], '%Y-%m-%d')
            if date_obj > datetime.now():
                errors.append('Date cannot be in the future')
        except ValueError:
            errors.append('Invalid date format. Use YYYY-MM-DD')
    
    return errors

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Server is running'}), 200

@app.route('/expenses', methods=['POST'])
def create_expense():
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    errors = validate_expense_data(data)
    if errors:
        return jsonify({'errors': errors}), 400
    
    expense_id = str(uuid.uuid4())
    conn = get_db()
    
    try:
        conn.execute(
            '''INSERT INTO expenses (id, amount, category, description, date, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (expense_id, float(data['amount']), data['category'], 
             data['description'].strip(), data['date'], datetime.now().isoformat(), datetime.now().isoformat())
        )
        conn.commit()
        
        expense = conn.execute('SELECT * FROM expenses WHERE id = ?', (expense_id,)).fetchone()
        conn.close()
        
        return jsonify(dict(expense)), 201
    
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/expenses', methods=['GET'])
def get_expenses():
    category = request.args.get('category')
    sort = request.args.get('sort', 'date_desc')
    
    conn = get_db()
    
    query = 'SELECT * FROM expenses'
    params = []
    
    if category and category != 'All' and category != '':
        query += ' WHERE category = ?'
        params.append(category)
    
    if sort == 'date_desc':
        query += ' ORDER BY date DESC, created_at DESC'
    else:
        query += ' ORDER BY date ASC, created_at ASC'
    
    try:
        expenses = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify([dict(expense) for expense in expenses])
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/expenses/<id>', methods=['PUT'])
def update_expense(id):
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    errors = validate_expense_data(data)
    if errors:
        return jsonify({'errors': errors}), 400
    
    conn = get_db()
    
    try:
        result = conn.execute(
            '''UPDATE expenses 
               SET amount = ?, category = ?, description = ?, date = ?, updated_at = ?
               WHERE id = ?''',
            (float(data['amount']), data['category'], data['description'].strip(), 
             data['date'], datetime.now().isoformat(), id)
        )
        conn.commit()
        
        if result.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Expense not found'}), 404
        
        expense = conn.execute('SELECT * FROM expenses WHERE id = ?', (id,)).fetchone()
        conn.close()
        
        return jsonify(dict(expense)), 200
    
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/expenses/<id>', methods=['DELETE'])
def delete_expense(id):
    conn = get_db()
    
    try:
        result = conn.execute('DELETE FROM expenses WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        
        if result.rowcount == 0:
            return jsonify({'error': 'Expense not found'}), 404
        
        return jsonify({'message': 'Expense deleted successfully'}), 200
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*50)
    print("Expense Tracker Backend Server")
    print("="*50)
    print("Server running at: http://localhost:5000")
    print("Endpoints:")
    print("  GET  /health")
    print("  POST /expenses")
    print("  GET  /expenses")
    print("  PUT  /expenses/<id>")
    print("  DELETE /expenses/<id>")
    print("="*50 + "\n")
    app.run(debug=True, port=5000, host='localhost')
