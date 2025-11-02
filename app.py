from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import json
import os
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = 'lumlens_secret_key_2024'
CORS(app)

# File paths for JSON databases
PRODUCTS_FILE = 'products.json'
ORDERS_FILE = 'orders.json'
CART_FILE = 'cart.json'

# Helper functions to read/write JSON files
def read_json(filename):
    """Read data from JSON file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def write_json(filename, data):
    """Write data to JSON file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

# Routes
@app.route('/')
def index():
    """Main page"""
    return render_template('shop.html')

@app.route('/api/products', methods=['GET'])
def get_products():
    """Get all products or filtered products"""
    data = read_json(PRODUCTS_FILE)
    products = data.get('products', [])
    
    # Get query parameters
    category = request.args.get('category', '').lower()
    search = request.args.get('search', '').lower()
    sort_by = request.args.get('sort', 'name')
    
    # Filter by category
    if category and category != 'all':
        products = [p for p in products if p['category'].lower() == category]
    
    # Filter by search term
    if search:
        products = [p for p in products if 
                   search in p['name'].lower() or 
                   search in p['description'].lower() or
                   search in p['category'].lower()]
    
    # Sort products
    if sort_by == 'price_low':
        products.sort(key=lambda x: x['price'])
    elif sort_by == 'price_high':
        products.sort(key=lambda x: x['price'], reverse=True)
    elif sort_by == 'rating':
        products.sort(key=lambda x: x.get('rating', 0), reverse=True)
    else:
        products.sort(key=lambda x: x['name'])
    
    return jsonify({'products': products, 'count': len(products)})

@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Get single product by ID"""
    data = read_json(PRODUCTS_FILE)
    products = data.get('products', [])
    
    product = next((p for p in products if p['id'] == product_id), None)
    
    if product:
        return jsonify(product)
    else:
        return jsonify({'error': 'Product not found'}), 404

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all unique categories"""
    data = read_json(PRODUCTS_FILE)
    products = data.get('products', [])
    
    categories = list(set(p['category'] for p in products))
    categories.sort()
    
    return jsonify({'categories': categories})

@app.route('/api/cart', methods=['GET'])
def get_cart():
    """Get cart items for current session"""
    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    
    cart_data = read_json(CART_FILE)
    cart_items = cart_data.get('carts', {}).get(session_id, [])
    
    # Calculate total
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    
    return jsonify({
        'items': cart_items,
        'total': round(total, 2),
        'count': len(cart_items)
    })

@app.route('/api/cart/add', methods=['POST'])
def add_to_cart():
    """Add item to cart"""
    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    
    data = request.json
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    # Get product details
    products_data = read_json(PRODUCTS_FILE)
    products = products_data.get('products', [])
    product = next((p for p in products if p['id'] == product_id), None)
    
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    # Load cart
    cart_data = read_json(CART_FILE)
    if 'carts' not in cart_data:
        cart_data['carts'] = {}
    
    if session_id not in cart_data['carts']:
        cart_data['carts'][session_id] = []
    
    cart = cart_data['carts'][session_id]
    
    # Check if product already in cart
    existing_item = next((item for item in cart if item['id'] == product_id), None)
    
    if existing_item:
        existing_item['quantity'] += quantity
    else:
        cart.append({
            'id': product['id'],
            'name': product['name'],
            'price': product['price'],
            'image': product['image'],
            'quantity': quantity
        })
    
    write_json(CART_FILE, cart_data)
    
    return jsonify({'message': 'Product added to cart', 'cart_count': len(cart)})

@app.route('/api/cart/update', methods=['POST'])
def update_cart():
    """Update cart item quantity"""
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'error': 'No cart found'}), 404
    
    data = request.json
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    cart_data = read_json(CART_FILE)
    cart = cart_data.get('carts', {}).get(session_id, [])
    
    item = next((item for item in cart if item['id'] == product_id), None)
    
    if item:
        if quantity <= 0:
            cart.remove(item)
        else:
            item['quantity'] = quantity
        
        cart_data['carts'][session_id] = cart
        write_json(CART_FILE, cart_data)
        
        return jsonify({'message': 'Cart updated'})
    else:
        return jsonify({'error': 'Item not found in cart'}), 404

@app.route('/api/cart/remove', methods=['POST'])
def remove_from_cart():
    """Remove item from cart"""
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'error': 'No cart found'}), 404
    
    data = request.json
    product_id = data.get('product_id')
    
    cart_data = read_json(CART_FILE)
    cart = cart_data.get('carts', {}).get(session_id, [])
    
    cart = [item for item in cart if item['id'] != product_id]
    cart_data['carts'][session_id] = cart
    write_json(CART_FILE, cart_data)
    
    return jsonify({'message': 'Item removed from cart'})

@app.route('/api/cart/clear', methods=['POST'])
def clear_cart():
    """Clear all items from cart"""
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'error': 'No cart found'}), 404
    
    cart_data = read_json(CART_FILE)
    cart_data['carts'][session_id] = []
    write_json(CART_FILE, cart_data)
    
    return jsonify({'message': 'Cart cleared'})

@app.route('/api/orders', methods=['POST'])
def create_order():
    """Create new order"""
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'error': 'No cart found'}), 404
    
    data = request.json
    
    # Get cart items
    cart_data = read_json(CART_FILE)
    cart_items = cart_data.get('carts', {}).get(session_id, [])
    
    if not cart_items:
        return jsonify({'error': 'Cart is empty'}), 400
    
    # Calculate total
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    
    # Create order
    order = {
        'order_id': str(uuid.uuid4()),
        'customer_name': data.get('name'),
        'email': data.get('email'),
        'phone': data.get('phone'),
        'address': data.get('address'),
        'city': data.get('city'),
        'state': data.get('state'),
        'zip_code': data.get('zip_code'),
        'country': data.get('country'),
        'location': data.get('location', {}),
        'items': cart_items,
        'total': round(total, 2),
        'status': 'pending',
        'created_at': datetime.now().isoformat(),
        'payment_method': data.get('payment_method', 'cash_on_delivery')
    }
    
    # Save order
    orders_data = read_json(ORDERS_FILE)
    if 'orders' not in orders_data:
        orders_data['orders'] = []
    
    orders_data['orders'].append(order)
    write_json(ORDERS_FILE, orders_data)
    
    # Clear cart
    cart_data['carts'][session_id] = []
    write_json(CART_FILE, cart_data)
    
    return jsonify({
        'message': 'Order placed successfully',
        'order_id': order['order_id'],
        'order': order
    })

@app.route('/api/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    """Get order by ID"""
    orders_data = read_json(ORDERS_FILE)
    orders = orders_data.get('orders', [])
    
    order = next((o for o in orders if o['order_id'] == order_id), None)
    
    if order:
        return jsonify(order)
    else:
        return jsonify({'error': 'Order not found'}), 404

@app.route('/api/orders', methods=['GET'])
def get_all_orders():
    """Get all orders"""
    orders_data = read_json(ORDERS_FILE)
    orders = orders_data.get('orders', [])
    
    # Sort by created_at descending
    orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return jsonify({'orders': orders, 'count': len(orders)})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get platform statistics"""
    products_data = read_json(PRODUCTS_FILE)
    orders_data = read_json(ORDERS_FILE)
    
    products = products_data.get('products', [])
    orders = orders_data.get('orders', [])
    
    total_revenue = sum(order['total'] for order in orders)
    
    stats = {
        'total_products': len(products),
        'total_orders': len(orders),
        'total_revenue': round(total_revenue, 2),
        'categories': len(set(p['category'] for p in products))
    }
    
    return jsonify(stats)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
