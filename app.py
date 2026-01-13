"""
Advanced Vehicle Search & CRM Application
With Apify Mobile.de Scraper Integration
PostgreSQL Database, PDF Generation, and Offer Management
"""

import os
import logging
import json
import re
from datetime import datetime
from io import BytesIO
from urllib.parse import urlparse
from flask import Flask, render_template_string, request, jsonify, send_file
from dotenv import load_dotenv
from apify_client import ApifyClient
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors

# Try to import psycopg2 for PostgreSQL, fall back to sqlite3 for local development
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_POSTGRES = True
except ImportError:
    import sqlite3
    HAS_POSTGRES = False

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='statics', static_url_path='/static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# Initialize Apify client
APIFY_API_KEY = os.getenv('APIFY_API_KEY')
apify_client = ApifyClient(APIFY_API_KEY) if APIFY_API_KEY else None

# Database setup - PostgreSQL for production, SQLite for local development
DATABASE_URL = os.getenv('DATABASE_URL')

# Fix Heroku's postgres:// URL to postgresql://
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Fallback to SQLite for local development
SQLITE_PATH = 'vehicle_crm.db'

def get_db_connection():
    """Get database connection - PostgreSQL for production, SQLite for local"""
    if DATABASE_URL and HAS_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn, 'postgres'
    else:
        conn = sqlite3.connect(SQLITE_PATH)
        return conn, 'sqlite'

# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_email(email: str) -> bool:
    """Validate email format using regex"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# ============================================================================
# DATABASE SETUP
# ============================================================================

def init_database():
    """Initialize database for CRM - PostgreSQL or SQLite"""
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    
    if db_type == 'postgres':
        # PostgreSQL tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                price TEXT,
                mileage TEXT,
                year TEXT,
                fuel TEXT,
                transmission TEXT,
                power TEXT,
                url TEXT UNIQUE,
                properties TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offers (
                id SERIAL PRIMARY KEY,
                vehicle_id INTEGER NOT NULL,
                client_email TEXT NOT NULL,
                client_name TEXT,
                offered_price TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (id) ON DELETE CASCADE
            )
        ''')
        logger.info('PostgreSQL database initialized')
    else:
        # SQLite tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                price TEXT,
                mileage TEXT,
                year TEXT,
                fuel TEXT,
                transmission TEXT,
                power TEXT,
                url TEXT UNIQUE,
                properties TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                client_email TEXT NOT NULL,
                client_name TEXT,
                offered_price TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
            )
        ''')
        logger.info('SQLite database initialized')
    
    conn.commit()
    conn.close()

def save_vehicle_to_db(vehicle_data: dict) -> int:
    """Save vehicle data to database and return vehicle ID"""
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    
    try:
        properties_json = json.dumps(vehicle_data.get('properties', {})) if vehicle_data.get('properties') else None
        url = vehicle_data.get('url', '')
        
        # Check if vehicle already exists by URL
        if url:
            if db_type == 'postgres':
                cursor.execute('SELECT id FROM vehicles WHERE url = %s', (url,))
            else:
                cursor.execute('SELECT id FROM vehicles WHERE url = ?', (url,))
            existing = cursor.fetchone()
            if existing:
                logger.info(f'Vehicle already exists with ID: {existing[0]}')
                return existing[0]
        
        if db_type == 'postgres':
            cursor.execute('''
                INSERT INTO vehicles 
                (title, price, mileage, year, fuel, transmission, power, url, properties)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                vehicle_data.get('title'),
                vehicle_data.get('price'),
                vehicle_data.get('mileage'),
                vehicle_data.get('year'),
                vehicle_data.get('fuel'),
                vehicle_data.get('transmission'),
                vehicle_data.get('power'),
                url,
                properties_json
            ))
            vehicle_id = cursor.fetchone()[0]
        else:
            cursor.execute('''
                INSERT INTO vehicles 
                (title, price, mileage, year, fuel, transmission, power, url, properties)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                vehicle_data.get('title'),
                vehicle_data.get('price'),
                vehicle_data.get('mileage'),
                vehicle_data.get('year'),
                vehicle_data.get('fuel'),
                vehicle_data.get('transmission'),
                vehicle_data.get('power'),
                url,
                properties_json
            ))
            vehicle_id = cursor.lastrowid
        
        conn.commit()
        logger.info(f'Vehicle saved to database with ID: {vehicle_id}')
        return vehicle_id
        
    except Exception as e:
        logger.error(f'Error saving vehicle to database: {str(e)}')
        return None
    finally:
        conn.close()

def save_offer_to_db(offer_data: dict) -> int:
    """Save offer data to database and return offer ID"""
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if db_type == 'postgres':
            cursor.execute('''
                INSERT INTO offers 
                (vehicle_id, client_email, client_name, offered_price, notes)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                offer_data.get('vehicle_id'),
                offer_data.get('client_email'),
                offer_data.get('client_name'),
                offer_data.get('offered_price'),
                offer_data.get('notes')
            ))
            offer_id = cursor.fetchone()[0]
        else:
            cursor.execute('''
                INSERT INTO offers 
                (vehicle_id, client_email, client_name, offered_price, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                offer_data.get('vehicle_id'),
                offer_data.get('client_email'),
                offer_data.get('client_name'),
                offer_data.get('offered_price'),
                offer_data.get('notes')
            ))
            offer_id = cursor.lastrowid
        
        conn.commit()
        logger.info(f'Offer saved to database with ID: {offer_id}')
        return offer_id
        
    except Exception as e:
        logger.error(f'Error saving offer to database: {str(e)}')
        return None
    finally:
        conn.close()

def get_vehicle_by_id(vehicle_id: int) -> dict:
    """Get vehicle data from database"""
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if db_type == 'postgres':
            cursor.execute('''
                SELECT id, title, price, mileage, year, fuel, transmission, power, url, properties
                FROM vehicles WHERE id = %s
            ''', (vehicle_id,))
        else:
            cursor.execute('''
                SELECT id, title, price, mileage, year, fuel, transmission, power, url, properties
                FROM vehicles WHERE id = ?
            ''', (vehicle_id,))
        
        result = cursor.fetchone()
        if result:
            return {
                'id': result[0],
                'title': result[1],
                'price': result[2],
                'mileage': result[3],
                'year': result[4],
                'fuel': result[5],
                'transmission': result[6],
                'power': result[7],
                'url': result[8],
                'properties': json.loads(result[9]) if result[9] else {}
            }
    except Exception as e:
        logger.error(f'Error fetching vehicle from database: {str(e)}')
    finally:
        conn.close()
    
    return None

# ============================================================================
# CRUD FUNCTIONS FOR ADMIN DASHBOARD
# ============================================================================

def get_all_vehicles() -> list:
    """Get all vehicles from database"""
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, title, price, mileage, year, fuel, transmission, power, url, created_at
            FROM vehicles ORDER BY created_at DESC
        ''')
        
        results = cursor.fetchall()
        vehicles = []
        for row in results:
            created_at = row[9]
            if created_at and hasattr(created_at, 'isoformat'):
                created_at = created_at.isoformat()
            vehicles.append({
                'id': row[0],
                'title': row[1],
                'price': row[2],
                'mileage': row[3],
                'year': row[4],
                'fuel': row[5],
                'transmission': row[6],
                'power': row[7],
                'url': row[8],
                'created_at': str(created_at) if created_at else None
            })
        return vehicles
    except Exception as e:
        logger.error(f'Error fetching vehicles: {str(e)}')
        return []
    finally:
        conn.close()

def get_all_offers() -> list:
    """Get all offers with vehicle info from database"""
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT o.id, o.vehicle_id, o.client_email, o.client_name, o.offered_price, 
                   o.notes, o.created_at, v.title as vehicle_title
            FROM offers o
            LEFT JOIN vehicles v ON o.vehicle_id = v.id
            ORDER BY o.created_at DESC
        ''')
        
        results = cursor.fetchall()
        offers = []
        for row in results:
            created_at = row[6]
            if created_at and hasattr(created_at, 'isoformat'):
                created_at = created_at.isoformat()
            offers.append({
                'id': row[0],
                'vehicle_id': row[1],
                'client_email': row[2],
                'client_name': row[3],
                'offered_price': row[4],
                'notes': row[5],
                'created_at': str(created_at) if created_at else None,
                'vehicle_title': row[7]
            })
        return offers
    except Exception as e:
        logger.error(f'Error fetching offers: {str(e)}')
        return []
    finally:
        conn.close()

def update_vehicle(vehicle_id: int, data: dict) -> bool:
    """Update vehicle in database"""
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if db_type == 'postgres':
            cursor.execute('''
                UPDATE vehicles 
                SET title = %s, price = %s, mileage = %s, year = %s, fuel = %s, 
                    transmission = %s, power = %s, url = %s
                WHERE id = %s
            ''', (
                data.get('title'),
                data.get('price'),
                data.get('mileage'),
                data.get('year'),
                data.get('fuel'),
                data.get('transmission'),
                data.get('power'),
                data.get('url'),
                vehicle_id
            ))
        else:
            cursor.execute('''
                UPDATE vehicles 
                SET title = ?, price = ?, mileage = ?, year = ?, fuel = ?, 
                    transmission = ?, power = ?, url = ?
                WHERE id = ?
            ''', (
                data.get('title'),
                data.get('price'),
                data.get('mileage'),
                data.get('year'),
                data.get('fuel'),
                data.get('transmission'),
                data.get('power'),
                data.get('url'),
                vehicle_id
            ))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f'Error updating vehicle: {str(e)}')
        return False
    finally:
        conn.close()

def update_offer(offer_id: int, data: dict) -> bool:
    """Update offer in database"""
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if db_type == 'postgres':
            cursor.execute('''
                UPDATE offers 
                SET client_email = %s, client_name = %s, offered_price = %s, notes = %s
                WHERE id = %s
            ''', (
                data.get('client_email'),
                data.get('client_name'),
                data.get('offered_price'),
                data.get('notes'),
                offer_id
            ))
        else:
            cursor.execute('''
                UPDATE offers 
                SET client_email = ?, client_name = ?, offered_price = ?, notes = ?
                WHERE id = ?
            ''', (
                data.get('client_email'),
                data.get('client_name'),
                data.get('offered_price'),
                data.get('notes'),
                offer_id
            ))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f'Error updating offer: {str(e)}')
        return False
    finally:
        conn.close()

def delete_vehicle(vehicle_id: int) -> bool:
    """Delete vehicle from database"""
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if db_type == 'postgres':
            # First delete related offers
            cursor.execute('DELETE FROM offers WHERE vehicle_id = %s', (vehicle_id,))
            # Then delete vehicle
            cursor.execute('DELETE FROM vehicles WHERE id = %s', (vehicle_id,))
        else:
            # First delete related offers
            cursor.execute('DELETE FROM offers WHERE vehicle_id = ?', (vehicle_id,))
            # Then delete vehicle
            cursor.execute('DELETE FROM vehicles WHERE id = ?', (vehicle_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f'Error deleting vehicle: {str(e)}')
        return False
    finally:
        conn.close()

def delete_offer(offer_id: int) -> bool:
    """Delete offer from database"""
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if db_type == 'postgres':
            cursor.execute('DELETE FROM offers WHERE id = %s', (offer_id,))
        else:
            cursor.execute('DELETE FROM offers WHERE id = ?', (offer_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f'Error deleting offer: {str(e)}')
        return False
    finally:
        conn.close()

def get_offer_by_id(offer_id: int) -> dict:
    """Get offer data from database"""
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if db_type == 'postgres':
            cursor.execute('''
                SELECT o.id, o.vehicle_id, o.client_email, o.client_name, o.offered_price, 
                       o.notes, o.created_at, v.title as vehicle_title
                FROM offers o
                LEFT JOIN vehicles v ON o.vehicle_id = v.id
                WHERE o.id = %s
            ''', (offer_id,))
        else:
            cursor.execute('''
                SELECT o.id, o.vehicle_id, o.client_email, o.client_name, o.offered_price, 
                       o.notes, o.created_at, v.title as vehicle_title
                FROM offers o
                LEFT JOIN vehicles v ON o.vehicle_id = v.id
                WHERE o.id = ?
            ''', (offer_id,))
        
        row = cursor.fetchone()
        if row:
            created_at = row[6]
            if created_at and hasattr(created_at, 'isoformat'):
                created_at = created_at.isoformat()
            return {
                'id': row[0],
                'vehicle_id': row[1],
                'client_email': row[2],
                'client_name': row[3],
                'offered_price': row[4],
                'notes': row[5],
                'created_at': str(created_at) if created_at else None,
                'vehicle_title': row[7]
            }
    except Exception as e:
        logger.error(f'Error fetching offer: {str(e)}')
    finally:
        conn.close()
    
    return None

def get_dashboard_stats() -> dict:
    """Get statistics for admin dashboard"""
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT COUNT(*) FROM vehicles')
        total_vehicles = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM offers')
        total_offers = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT client_email) FROM offers')
        unique_clients = cursor.fetchone()[0]
        
        return {
            'total_vehicles': total_vehicles,
            'total_offers': total_offers,
            'unique_clients': unique_clients
        }
    except Exception as e:
        logger.error(f'Error fetching stats: {str(e)}')
        return {'total_vehicles': 0, 'total_offers': 0, 'unique_clients': 0}
    finally:
        conn.close()

# ============================================================================
# PDF GENERATION
# ============================================================================

# Logo path - update this to match your logo file location
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'statics', 'images', 'logo_automaritea.png')

def generate_offer_pdf(vehicle_data: dict, offer_data: dict, client_email: str) -> bytes:
    """Generate PDF offer document"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#007bff'),
        spaceAfter=30,
        alignment=1
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#007bff'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    # Build document
    elements = []
    
    # Add logo at top left if it exists
    if os.path.exists(LOGO_PATH):
        try:
            # Get image dimensions to maintain aspect ratio
            from PIL import Image as PILImage
            with PILImage.open(LOGO_PATH) as img:
                img_width, img_height = img.size
                aspect_ratio = img_width / img_height
            
            # Set desired width and calculate height to maintain aspect ratio
            logo_width = 2.5 * inch
            logo_height = logo_width / aspect_ratio
            
            logo = Image(LOGO_PATH, width=logo_width, height=logo_height)
            logo.hAlign = 'LEFT'
            elements.append(logo)
            elements.append(Spacer(1, 0.3*inch))
        except Exception as e:
            logger.warning(f'Could not load logo: {str(e)}')
    
    # Title
    elements.append(Paragraph('VEHICLE OFFER', title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Offer details
    offer_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    elements.append(Paragraph(f'<b>Offer Date:</b> {offer_date}', styles['Normal']))
    elements.append(Paragraph(f'<b>Client Email:</b> {client_email}', styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))
    
    # Vehicle Information (removed Original Price)
    elements.append(Paragraph('VEHICLE INFORMATION', heading_style))
    vehicle_data_list = [
        ['Field', 'Value'],
        ['Title', vehicle_data.get('title', 'N/A')],
        ['Offered Price', str(offer_data.get('offered_price', 'N/A')) + ' €'],
        ['Mileage', vehicle_data.get('mileage', 'N/A')],
        ['Year', vehicle_data.get('year', 'N/A')],
        ['Fuel Type', vehicle_data.get('fuel', 'N/A')],
        ['Transmission', vehicle_data.get('transmission', 'N/A')],
        ['Power', vehicle_data.get('power', 'N/A')],
        ['URL', vehicle_data.get('url', 'N/A')[:50] + '...'],
    ]
    
    vehicle_table = Table(vehicle_data_list, colWidths=[2*inch, 4*inch])
    vehicle_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    elements.append(vehicle_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Technical Data
    if vehicle_data.get('properties'):
        elements.append(Paragraph('TECHNICAL DATA', heading_style))
        tech_data_list = [['Property', 'Value']]
        for key, value in vehicle_data.get('properties', {}).items():
            if value and value != 'N/A':
                tech_data_list.append([key, str(value)[:50]])
        
        if len(tech_data_list) > 1:
            tech_table = Table(tech_data_list, colWidths=[2*inch, 4*inch])
            tech_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            elements.append(tech_table)
            elements.append(Spacer(1, 0.2*inch))
    
    # Notes
    if offer_data.get('notes'):
        elements.append(Paragraph('NOTES', heading_style))
        elements.append(Paragraph(offer_data.get('notes', ''), styles['Normal']))
    
    # Footer
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph('---', styles['Normal']))
    elements.append(Paragraph(
        'This is an automated offer generated by Vehicle Search & CRM System',
        ParagraphStyle('footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey)
    ))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# ============================================================================
# VEHICLE DATABASE
# ============================================================================

VEHICLES = {
    'volvo': {
        'name': 'Volvo',
        'models': {
            'xc60': {
                'name': 'XC60',
                'url': 'https://suchen.mobile.de/fahrzeuge/search.html?dam=false&isSearchRequest=true&ms=25100%3B40%3B%3B&ref=quickSearch&s=Car&sb=rel&vc=Car'
            },
            'xc90': {
                'name': 'XC90',
                'url': 'https://suchen.mobile.de/fahrzeuge/search.html?dam=false&isSearchRequest=true&ms=25100%3B37%3B%3B&ref=quickSearch&s=Car&sb=rel&vc=Car'
            }
        }
    },
    'ferrari': {
        'name': 'Ferrari',
        'models': {
            '308': {
                'name': '308',
                'url': 'https://suchen.mobile.de/fahrzeuge/search.html?dam=false&isSearchRequest=true&ms=8600%3B9%3B%3B&ref=quickSearch&s=Car&sb=rel&vc=Car'
            }
        }
    },
    'mclaren': {
        'name': 'McLaren',
        'models': {
            '750s': {
                'name': '750S',
                'url': 'https://suchen.mobile.de/fahrzeuge/search.html?dam=false&isSearchRequest=true&ms=137%3B18%3B%3B&ref=quickSearch&s=Car&sb=rel&vc=Car'
            }
        }
    }
}

# Features list
FEATURES = [
    'ABS', 'Adaptive Cruise Control', 'Air suspension', 'Alarm system', 'Alloy wheels',
    'Ambient lighting', 'Android Auto', 'Apple CarPlay', 'Arm rest', 'Autom. dimming interior mirror',
    'Auxiliary heating', 'Blind spot assist', 'Bluetooth', 'Cargo barrier', 'Central locking',
    'DAB radio', 'Digital cockpit', 'Distance warning system', 'Electric seat adjustment', 'Electric side mirror',
    'Electric tailgate', 'Electric windows', 'Eletric seat adjustment with memory function', 'Emergency brake assist', 'Emergency call system',
    'Emergency tyre repair kit', 'ESP', 'Fatigue warning system', 'Folding exterior mirrors', 'Four-wheel drive',
    'Glare-free high beam headlights', 'Hands-free kit', 'Headlight washer system', 'Head-up display', 'Heated rear seats',
    'Heated seats', 'Heated steering wheel', 'High beam assist', 'Hill-start assist', 'Immobilizer',
    'Induction charging for smartphones', 'Integrated music streaming', 'Isofix', 'Lane change assist', 'LED headlights',
    'LED running lights', 'Light sensor', 'Lumbar support', 'Multifunction steering wheel', 'Navigation system',
    'On-board computer', 'Panoramic roof', 'Particulate filter', 'Power Assisted Steering', 'Rain sensor',
    'Roof rack', 'Sound system', 'Speed limit control system', 'Start-stop system', 'Sunroof',
    'Tinted windows', 'Traction control', 'Traffic sign recognition', 'Tuner/radio', 'Tyre pressure monitoring',
    'USB port', 'Winter package', 'WLAN / Wi-Fi hotspot'
]

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Advanced Vehicle Search & CRM</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { background: white; padding: 30px; border-radius: 8px; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header h1 { color: #333; margin-bottom: 10px; }
        .form-container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .form-section { margin-bottom: 30px; }
        .section-title { font-size: 18px; font-weight: 600; color: #333; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #007bff; }
        .form-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .form-group { display: flex; flex-direction: column; }
        label { font-weight: 600; color: #333; margin-bottom: 8px; font-size: 14px; }
        input[type="text"], input[type="number"], input[type="email"], select, textarea { padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
        input[type="text"]:focus, input[type="number"]:focus, input[type="email"]:focus, select:focus, textarea:focus { outline: none; border-color: #007bff; box-shadow: 0 0 0 3px rgba(0,123,255,0.1); }
        .features-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; }
        .feature-checkbox { display: flex; align-items: center; }
        .feature-checkbox input[type="checkbox"] { margin-right: 10px; cursor: pointer; width: 18px; height: 18px; }
        .feature-checkbox label { margin: 0; cursor: pointer; font-weight: 400; }
        .button-group { display: flex; gap: 10px; margin-top: 30px; flex-wrap: wrap; }
        button { padding: 12px 30px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: 600; }
        .btn-primary { background: #007bff; color: white; }
        .btn-primary:hover { background: #0056b3; }
        .btn-secondary { background: #6c757d; color: white; }
        .btn-secondary:hover { background: #5a6268; }
        .btn-success { background: #28a745; color: white; }
        .btn-success:hover { background: #218838; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-danger:hover { background: #c82333; }
        .results { background: white; padding: 30px; border-radius: 8px; margin-top: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); display: none; }
        .result-item { border-bottom: 1px solid #eee; padding: 20px 0; }
        .result-item:last-child { border-bottom: none; }
        .result-title { font-weight: 600; color: #333; margin-bottom: 10px; font-size: 16px; }
        .result-details { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; margin-bottom: 15px; }
        .detail-item { color: #666; font-size: 14px; }
        .detail-label { font-weight: 600; color: #333; }
        .result-link { display: inline-block; margin-top: 10px; padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin-right: 10px; }
        .result-link:hover { background: #0056b3; }
        .btn-details { display: inline-block; margin-top: 10px; padding: 8px 16px; background: #28a745; color: white; text-decoration: none; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
        .btn-details:hover { background: #218838; }
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); }
        .modal-content { background-color: white; margin: 5% auto; padding: 30px; border-radius: 8px; width: 90%; max-width: 900px; max-height: 80vh; overflow-y: auto; box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 2px solid #007bff; padding-bottom: 15px; }
        .modal-header h2 { margin: 0; color: #333; }
        .modal-close { font-size: 28px; font-weight: bold; color: #999; cursor: pointer; background: none; border: none; padding: 0; }
        .modal-close:hover { color: #333; }
        .detail-section { margin-bottom: 30px; }
        .detail-section-title { font-size: 16px; font-weight: 600; color: #007bff; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #ddd; }
        .detail-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .detail-field { background: #f9f9f9; padding: 15px; border-radius: 4px; border-left: 4px solid #007bff; }
        .detail-field-label { font-weight: 600; color: #333; font-size: 12px; text-transform: uppercase; margin-bottom: 5px; }
        .detail-field-value { color: #666; font-size: 14px; word-break: break-word; }
        .loading { text-align: center; padding: 40px 20px; display: none; }
        .loading .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #007bff; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 20px; }
        .loading p { color: #666; margin-top: 10px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .message { padding: 15px; border-radius: 4px; margin-bottom: 20px; }
        .message.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .message.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .message.info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .modal-buttons { display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap; }
        .modal-buttons button { flex: 1; min-width: 150px; }
        textarea { resize: vertical; min-height: 100px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
                <div style="display: flex; align-items: center; gap: 15px;">
                    <img src="/static/images/logo_automaritea.png" alt="Logo" style="height: 50px; width: auto;">
                    <div>
                        <h1 style="margin: 0;">Advanced Vehicle Search & CRM</h1>
                        <p style="margin: 5px 0 0 0;">Search for vehicles, create offers, and manage your CRM</p>
                    </div>
                </div>
                <a href="/admin" style="background: #1a1a2e; color: white; padding: 10px 20px; border-radius: 5px; text-decoration: none; font-weight: 500;">Admin Dashboard</a>
            </div>
        </div>

        <div class="form-container">
            <form id="searchForm">
                <!-- Basic Information -->
                <div class="form-section">
                    <div class="section-title">Basic Information</div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="make">Car Brand *</label>
                            <select id="make" required>
                                <option value="">Select Brand...</option>
                                {% for make_key, make_data in vehicles.items() %}
                                    <option value="{{ make_key }}">{{ make_data.name }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="model">Car Model *</label>
                            <select id="model" required>
                                <option value="">Select Model...</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="carType">Car Type</label>
                            <select id="carType">
                                <option value="">Any</option>
                                <option value="sedan">Sedan</option>
                                <option value="suv">SUV</option>
                                <option value="coupe">Coupe</option>
                                <option value="convertible">Convertible</option>
                                <option value="wagon">Wagon</option>
                                <option value="hatchback">Hatchback</option>
                                <option value="van">Van</option>
                            </select>
                        </div>
                    </div>
                </div>

                <!-- Price & Mileage -->
                <div class="form-section">
                    <div class="section-title">Price & Mileage</div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="price">Max Price (€)</label>
                            <input type="number" id="price" placeholder="e.g., 50000">
                        </div>
                        <div class="form-group">
                            <label for="mileage">Max Mileage (km)</label>
                            <input type="number" id="mileage" placeholder="e.g., 100000">
                        </div>
                        <div class="form-group">
                            <label for="modelYear">Min Year</label>
                            <input type="number" id="modelYear" placeholder="e.g., 2018">
                        </div>
                    </div>
                </div>

                <!-- Engine & Performance -->
                <div class="form-section">
                    <div class="section-title">Engine & Performance</div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="power">Power (kW)</label>
                            <input type="number" id="power" placeholder="e.g., 100">
                        </div>
                        <div class="form-group">
                            <label for="cylinders">Cylinders</label>
                            <input type="number" id="cylinders" placeholder="e.g., 4">
                        </div>
                        <div class="form-group">
                            <label for="cubicCapacity">Cubic Capacity (ccm)</label>
                            <input type="number" id="cubicCapacity" placeholder="e.g., 2000">
                        </div>
                    </div>
                </div>

                <!-- Fuel & Transmission -->
                <div class="form-section">
                    <div class="section-title">Fuel & Transmission</div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="fuel">Fuel Type</label>
                            <select id="fuel">
                                <option value="">Any</option>
                                <option value="petrol">Petrol</option>
                                <option value="diesel">Diesel</option>
                                <option value="hybrid">Hybrid</option>
                                <option value="electric">Electric</option>
                                <option value="lpg">LPG</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="transmission">Transmission</label>
                            <select id="transmission">
                                <option value="">Any</option>
                                <option value="manual">Manual</option>
                                <option value="automatic">Automatic</option>
                                <option value="cvt">CVT</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="driveType">Drive Type</label>
                            <select id="driveType">
                                <option value="">Any</option>
                                <option value="fwd">Front-wheel Drive</option>
                                <option value="rwd">Rear-wheel Drive</option>
                                <option value="awd">All-wheel Drive</option>
                            </select>
                        </div>
                    </div>
                </div>

                <!-- Electric Vehicle Options -->
                <div class="form-section">
                    <div class="section-title">Electric Vehicle Options</div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="batteryCapacity">Battery Capacity (kWh)</label>
                            <input type="number" id="batteryCapacity" placeholder="e.g., 60">
                        </div>
                        <div class="form-group">
                            <label for="fastChargeTime">Fast Charge Time (min)</label>
                            <input type="number" id="fastChargeTime" placeholder="e.g., 30">
                        </div>
                    </div>
                </div>

                <!-- Interior & Comfort -->
                <div class="form-section">
                    <div class="section-title">Interior & Comfort</div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="seats">Number of Seats</label>
                            <input type="number" id="seats" placeholder="e.g., 5">
                        </div>
                        <div class="form-group">
                            <label for="doors">Number of Doors</label>
                            <input type="number" id="doors" placeholder="e.g., 4">
                        </div>
                        <div class="form-group">
                            <label for="colour">Colour</label>
                            <select id="colour">
                                <option value="">Any</option>
                                <option value="black">Black</option>
                                <option value="white">White</option>
                                <option value="silver">Silver</option>
                                <option value="grey">Grey</option>
                                <option value="red">Red</option>
                                <option value="blue">Blue</option>
                                <option value="green">Green</option>
                                <option value="brown">Brown</option>
                                <option value="beige">Beige</option>
                                <option value="gold">Gold</option>
                            </select>
                        </div>
                    </div>
                </div>

                <!-- Additional Options -->
                <div class="form-section">
                    <div class="section-title">Additional Options</div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="interiorDesign">Interior Design</label>
                            <input type="text" id="interiorDesign" placeholder="e.g., Leather">
                        </div>
                        <div class="form-group">
                            <label for="trimLine">Trim Line</label>
                            <input type="text" id="trimLine" placeholder="e.g., Sport">
                        </div>
                        <div class="form-group">
                            <label for="vehicleCondition">Vehicle Condition</label>
                            <select id="vehicleCondition">
                                <option value="">Any</option>
                                <option value="new">New</option>
                                <option value="used">Used</option>
                                <option value="damaged">Damaged</option>
                            </select>
                        </div>
                    </div>
                </div>

                <!-- Environmental & Safety -->
                <div class="form-section">
                    <div class="section-title">Environmental & Safety</div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="emissionClass">Emission Class</label>
                            <select id="emissionClass">
                                <option value="">Any</option>
                                <option value="euro1">Euro 1</option>
                                <option value="euro2">Euro 2</option>
                                <option value="euro3">Euro 3</option>
                                <option value="euro4">Euro 4</option>
                                <option value="euro5">Euro 5</option>
                                <option value="euro6">Euro 6</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="climatisation">Climatisation</label>
                            <select id="climatisation">
                                <option value="">Any</option>
                                <option value="none">None</option>
                                <option value="manual">Manual</option>
                                <option value="automatic">Automatic</option>
                                <option value="dual">Dual Zone</option>
                                <option value="multi">Multi Zone</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="parkingSensors">Parking Sensors</label>
                            <select id="parkingSensors">
                                <option value="">Any</option>
                                <option value="none">None</option>
                                <option value="front">Front</option>
                                <option value="rear">Rear</option>
                                <option value="both">Front & Rear</option>
                            </select>
                        </div>
                    </div>
                </div>

                <!-- Safety Features -->
                <div class="form-section">
                    <div class="section-title">Safety Features</div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="airbags">Airbags</label>
                            <input type="number" id="airbags" placeholder="e.g., 6">
                        </div>
                        <div class="form-group">
                            <label for="specialFeatures">Special Features</label>
                            <input type="text" id="specialFeatures" placeholder="e.g., Panoramic Roof">
                        </div>
                    </div>
                </div>

                <!-- Features -->
                <div class="form-section">
                    <div class="section-title">Vehicle Features</div>
                    <div class="features-grid">
                        {% for feature in features %}
                            <div class="feature-checkbox">
                                <input type="checkbox" id="feature_{{ loop.index }}" name="features" value="{{ feature }}">
                                <label for="feature_{{ loop.index }}">{{ feature }}</label>
                            </div>
                        {% endfor %}
                    </div>
                </div>

                <!-- Buttons -->
                <div class="button-group">
                    <button type="submit" class="btn-primary">🔍 Search</button>
                    <button type="reset" class="btn-secondary">Clear Form</button>
                </div>
            </form>
        </div>

        <div id="message"></div>
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Searching... This may take 1-3 minutes</p>
        </div>

        <div class="results" id="results">
            <h2>Results</h2>
            <div id="resultsList"></div>
        </div>
    </div>

    <!-- Details Modal -->
    <div id="detailsModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="detailsTitle">Vehicle Details</h2>
                <button class="modal-close" onclick="closeDetailsModal()">&times;</button>
            </div>
            <div id="detailsContent"></div>
            <div class="modal-buttons">
                <button class="btn-primary" onclick="closeDetailsModal()">Close</button>
                <button class="btn-success" id="createOfferBtn" onclick="openCreateOfferModal()">Create Offer</button>
            </div>
        </div>
    </div>

    <!-- Create Offer Modal -->
    <div id="createOfferModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Create Offer</h2>
                <button class="modal-close" onclick="closeCreateOfferModal()">&times;</button>
            </div>
            <form id="offerForm">
                <div class="form-section">
                    <div class="section-title">Client Information</div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="clientEmail">Client Email *</label>
                            <input type="email" id="clientEmail" required placeholder="client@example.com">
                        </div>
                        <div class="form-group">
                            <label for="clientName">Client Name</label>
                            <input type="text" id="clientName" placeholder="John Doe">
                        </div>
                    </div>
                </div>

                <div class="form-section">
                    <div class="section-title">Offer Details</div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="offeredPrice">Offered Price (€) *</label>
                            <input type="number" id="offeredPrice" required placeholder="e.g., 25000">
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="offerNotes">Notes</label>
                            <textarea id="offerNotes" placeholder="Additional notes about the offer..."></textarea>
                        </div>
                    </div>
                </div>

                <div class="modal-buttons">
                    <button type="button" class="btn-secondary" onclick="closeCreateOfferModal()">Cancel</button>
                    <button type="button" class="btn-success" onclick="submitOffer()">Create & Download PDF</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        const vehicles = {{ vehicles_json|safe }};
        let currentVehicleData = null;
        let currentVehicleId = null;

        const makeSelect = document.getElementById('make');
        const modelSelect = document.getElementById('model');
        const searchForm = document.getElementById('searchForm');
        const loading = document.getElementById('loading');
        const results = document.getElementById('results');
        const resultsList = document.getElementById('resultsList');
        const message = document.getElementById('message');

        // Update models when make changes
        makeSelect.addEventListener('change', function() {
            modelSelect.innerHTML = '<option value="">Select Model...</option>';
            if (this.value && vehicles[this.value]) {
                const models = vehicles[this.value].models;
                for (const [key, model] of Object.entries(models)) {
                    const option = document.createElement('option');
                    option.value = key;
                    option.textContent = model.name;
                    modelSelect.appendChild(option);
                }
            }
        });

        // Handle search
        searchForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = {
                make: document.getElementById('make').value,
                model: document.getElementById('model').value,
                carType: document.getElementById('carType').value,
                modelYear: document.getElementById('modelYear').value,
                mileage: document.getElementById('mileage').value,
                price: document.getElementById('price').value,
                power: document.getElementById('power').value,
                cylinders: document.getElementById('cylinders').value,
                cubicCapacity: document.getElementById('cubicCapacity').value,
                fuel: document.getElementById('fuel').value,
                transmission: document.getElementById('transmission').value,
                driveType: document.getElementById('driveType').value,
                fastChargeTime: document.getElementById('fastChargeTime').value,
                batteryCapacity: document.getElementById('batteryCapacity').value,
                seats: document.getElementById('seats').value,
                doors: document.getElementById('doors').value,
                colour: document.getElementById('colour').value,
                interiorDesign: document.getElementById('interiorDesign').value,
                trimLine: document.getElementById('trimLine').value,
                vehicleCondition: document.getElementById('vehicleCondition').value,
                emissionClass: document.getElementById('emissionClass').value,
                climatisation: document.getElementById('climatisation').value,
                parkingSensors: document.getElementById('parkingSensors').value,
                airbags: document.getElementById('airbags').value,
                specialFeatures: document.getElementById('specialFeatures').value,
                features: Array.from(document.querySelectorAll('input[name="features"]:checked')).map(cb => cb.value)
            };

            if (!formData.make || !formData.model) {
                showMessage('Please select both brand and model', 'error');
                return;
            }

            loading.style.display = 'block';
            results.style.display = 'none';
            message.innerHTML = '';

            try {
                const response = await fetch('/api/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });

                const data = await response.json();
                loading.style.display = 'none';

                if (data.success) {
                    displayResults(data.listings, data.total);
                    showMessage(`Found ${data.total} vehicles!`, 'success');
                } else {
                    showMessage(data.error || 'Search failed', 'error');
                }
            } catch (error) {
                loading.style.display = 'none';
                showMessage('Error: ' + error.message, 'error');
            }
        });

        function displayResults(listings, total) {
            resultsList.innerHTML = '';
            if (!listings || listings.length === 0) {
                resultsList.innerHTML = '<p>No results found</p>';
                results.style.display = 'block';
                return;
            }

            listings.forEach((item, index) => {
                const div = document.createElement('div');
                div.className = 'result-item';
                div.innerHTML = `
                    <div class="result-title">${item.title || 'Vehicle'}</div>
                    <div class="result-details">
                        <div class="detail-item">
                            <div class="detail-label">Price</div>
                            ${item.price || 'N/A'}
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Mileage</div>
                            ${item.mileage || 'N/A'}
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Year</div>
                            ${item.year || 'N/A'}
                        </div>
                    </div>
                    <div>
                        <button class="btn-details" data-title="${item.title || 'Vehicle'}" data-url="${item.url || ''}">View Details</button>
                        ${item.url ? `<a href="${item.url}" target="_blank" class="result-link">View on Mobile.de</a>` : ''}
                    </div>
                `;
                resultsList.appendChild(div);
                
                const button = div.querySelector('.btn-details');
                button.addEventListener('click', function() {
                    showDetailsModal({
                        title: this.getAttribute('data-title'),
                        url: this.getAttribute('data-url')
                    });
                });
            });
            results.style.display = 'block';
        }

        function showMessage(text, type) {
            message.innerHTML = `<div class="message ${type}">${text}</div>`;
        }

        function showDetailsModal(item) {
            const modal = document.getElementById('detailsModal');
            const title = document.getElementById('detailsTitle');
            const content = document.getElementById('detailsContent');
            
            title.textContent = item.title || 'Vehicle Details';
            
            content.innerHTML = '<div class="loading" style="display: block;"><div class="spinner"></div><p>Loading vehicle details...</p></div>';
            modal.style.display = 'block';
            
            if (item.url) {
                fetch('/api/vehicle-details', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: item.url })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        currentVehicleData = data.details;
                        currentVehicleId = data.vehicle_id;
                        displayVehicleDetails(data.details);
                    } else {
                        content.innerHTML = `<div class="message error">Error loading details: ${data.error}</div>`;
                    }
                })
                .catch(error => {
                    content.innerHTML = `<div class="message error">Error: ${error.message}</div>`;
                });
            } else {
                content.innerHTML = '<div class="message error">No URL available for this vehicle</div>';
            }
        }
        
        function displayVehicleDetails(details) {
            const content = document.getElementById('detailsContent');
            let html = '';
            
            html += `
                <div class="detail-section">
                    <div class="detail-section-title">Basic Information</div>
                    <div class="detail-grid">
                        <div class="detail-field">
                            <div class="detail-field-label">Title</div>
                            <div class="detail-field-value">${details.title || 'N/A'}</div>
                        </div>
                        <div class="detail-field">
                            <div class="detail-field-label">Price</div>
                            <div class="detail-field-value">${details.price || 'N/A'}</div>
                        </div>
                        <div class="detail-field">
                            <div class="detail-field-label">Mileage</div>
                            <div class="detail-field-value">${details.mileage || 'N/A'}</div>
                        </div>
                        <div class="detail-field">
                            <div class="detail-field-label">Year</div>
                            <div class="detail-field-value">${details.year || 'N/A'}</div>
                        </div>
                    </div>
                </div>
            `;
            
            if (details.fuel || details.transmission || details.power) {
                html += `
                    <div class="detail-section">
                        <div class="detail-section-title">Engine & Transmission</div>
                        <div class="detail-grid">
                            ${details.fuel ? `<div class="detail-field"><div class="detail-field-label">Fuel Type</div><div class="detail-field-value">${details.fuel}</div></div>` : ''}
                            ${details.transmission ? `<div class="detail-field"><div class="detail-field-label">Transmission</div><div class="detail-field-value">${details.transmission}</div></div>` : ''}
                            ${details.power ? `<div class="detail-field"><div class="detail-field-label">Power</div><div class="detail-field-value">${details.power}</div></div>` : ''}
                        </div>
                    </div>
                `;
            }
            
            if (details.properties && Object.keys(details.properties).length > 0) {
                let propsHtml = '';
                for (const [key, value] of Object.entries(details.properties)) {
                    if (value && value !== 'N/A') {
                        const label = key.replace(/([A-Z])/g, ' $1').trim();
                        const displayValue = typeof value === 'object' ? JSON.stringify(value) : value;
                        propsHtml += `
                            <div class="detail-field">
                                <div class="detail-field-label">${label}</div>
                                <div class="detail-field-value">${displayValue}</div>
                            </div>
                        `;
                    }
                }
                
                if (propsHtml) {
                    html += `
                        <div class="detail-section">
                            <div class="detail-section-title">Technical Data</div>
                            <div class="detail-grid">
                                ${propsHtml}
                            </div>
                        </div>
                    `;
                }
            }
            
            html += `
                <div class="detail-section">
                    <a href="${details.url}" target="_blank" class="result-link">View on Mobile.de</a>
                </div>
            `;
            
            content.innerHTML = html;
        }
        
        function closeDetailsModal() {
            document.getElementById('detailsModal').style.display = 'none';
        }

        function openCreateOfferModal() {
            if (!currentVehicleData) {
                showMessage('Vehicle data not loaded', 'error');
                return;
            }
            document.getElementById('createOfferModal').style.display = 'block';
            const priceValue = currentVehicleData.price ? currentVehicleData.price.replace(/[^0-9]/g, '') : '';
            document.getElementById('offeredPrice').value = priceValue;
        }

        function closeCreateOfferModal() {
            document.getElementById('createOfferModal').style.display = 'none';
            document.getElementById('offerForm').reset();
        }

        function submitOffer() {
            const clientEmail = document.getElementById('clientEmail').value;
            const clientName = document.getElementById('clientName').value;
            const offeredPrice = document.getElementById('offeredPrice').value;
            const offerNotes = document.getElementById('offerNotes').value;

            if (!clientEmail || !offeredPrice) {
                showMessage('Please fill in required fields', 'error');
                return;
            }

            fetch('/api/create-offer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    vehicle_data: currentVehicleData,
                    client_email: clientEmail,
                    client_name: clientName,
                    offered_price: offeredPrice,
                    notes: offerNotes
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showMessage('Offer created successfully!', 'success');
                    downloadOfferPDF(data.offer_id);
                    closeCreateOfferModal();
                } else {
                    showMessage(data.error || 'Failed to create offer', 'error');
                }
            })
            .catch(error => {
                showMessage('Error: ' + error.message, 'error');
            });
        }

        function downloadOfferPDF(offerId) {
            const link = document.createElement('a');
            link.href = `/api/download-offer-pdf/${offerId}`;
            link.download = `offer_${offerId}.pdf`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
        
        window.onclick = function(event) {
            const detailsModal = document.getElementById('detailsModal');
            const createOfferModal = document.getElementById('createOfferModal');
            if (event.target == detailsModal) {
                detailsModal.style.display = 'none';
            }
            if (event.target == createOfferModal) {
                createOfferModal.style.display = 'none';
            }
        }
    </script>
</body>
</html>
'''

# ============================================================================
# ADMIN DASHBOARD TEMPLATE
# ============================================================================

ADMIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - CRM</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        
        .navbar {
            background: #2ecc71;
            color: white;
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .navbar-brand {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .navbar-brand img { height: 40px; }
        .navbar-brand h1 { font-size: 1.3rem; }
        .navbar-links a {
            color: white;
            text-decoration: none;
            margin-left: 20px;
            padding: 8px 16px;
            border-radius: 5px;
            transition: background 0.3s;
        }
        .navbar-links a:hover { background: rgba(255,255,255,0.2); }
        .navbar-links a.active { background: #27ae60; }
        
        .container { max-width: 1400px; margin: 0 auto; padding: 30px; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            border-radius: 10px;
            padding: 25px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .stat-card h3 { color: #666; font-size: 0.9rem; margin-bottom: 10px; }
        .stat-card .value { font-size: 2.5rem; font-weight: bold; color: #007bff; }
        
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab-btn {
            padding: 12px 24px;
            border: none;
            background: white;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.3s;
        }
        .tab-btn.active { background: #007bff; color: white; }
        .tab-btn:hover:not(.active) { background: #e9ecef; }
        
        .data-section {
            background: white;
            border-radius: 10px;
            padding: 25px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .section-header h2 { color: #333; }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.3s;
        }
        .btn-primary { background: #007bff; color: white; }
        .btn-primary:hover { background: #0056b3; }
        .btn-success { background: #28a745; color: white; }
        .btn-success:hover { background: #1e7e34; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-danger:hover { background: #c82333; }
        .btn-secondary { background: #6c757d; color: white; }
        .btn-secondary:hover { background: #545b62; }
        .btn-sm { padding: 5px 10px; font-size: 0.8rem; }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th { background: #f8f9fa; font-weight: 600; color: #333; }
        tr:hover { background: #f8f9fa; }
        
        .actions { display: flex; gap: 5px; }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal.active { display: flex; }
        .modal-content {
            background: white;
            border-radius: 10px;
            padding: 30px;
            max-width: 600px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .modal-header h2 { color: #333; }
        .close-btn {
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: #666;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: #333;
        }
        .form-group input, .form-group textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 1rem;
        }
        .form-group textarea { resize: vertical; min-height: 80px; }
        
        .form-actions {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            margin-top: 20px;
        }
        
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        .empty-state {
            text-align: center;
            padding: 50px;
            color: #666;
        }
        .empty-state h3 { margin-bottom: 10px; }
        
        .truncate {
            max-width: 200px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        .badge-success { background: #d4edda; color: #155724; }
        .badge-info { background: #d1ecf1; color: #0c5460; }
        
        .message {
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .message.success { background: #d4edda; color: #155724; }
        .message.error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="navbar-brand">
            <img src="/static/images/logo_automaritea.png" alt="Logo">
            <h1>Admin Dashboard</h1>
        </div>
        <div class="navbar-links">
            <a href="/">Vehicle Search</a>
            <a href="/admin" class="active">Admin Dashboard</a>
        </div>
    </nav>
    
    <div class="container">
        <div id="messageArea"></div>
        
        <!-- Stats Cards -->
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Vehicles</h3>
                <div class="value" id="totalVehicles">{{ stats.total_vehicles }}</div>
            </div>
            <div class="stat-card">
                <h3>Total Offers</h3>
                <div class="value" id="totalOffers">{{ stats.total_offers }}</div>
            </div>
            <div class="stat-card">
                <h3>Unique Clients</h3>
                <div class="value" id="uniqueClients">{{ stats.unique_clients }}</div>
            </div>
        </div>
        
        <!-- Tabs -->
        <div class="tabs">
            <button class="tab-btn active" onclick="showTab('vehicles')">Vehicles</button>
            <button class="tab-btn" onclick="showTab('offers')">Offers</button>
        </div>
        
        <!-- Vehicles Tab -->
        <div id="vehiclesTab" class="tab-content active">
            <div class="data-section">
                <div class="section-header">
                    <h2>Vehicles</h2>
                    <button class="btn btn-primary" onclick="openAddVehicleModal()">+ Add Vehicle</button>
                </div>
                <table id="vehiclesTable">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Title</th>
                            <th>Price</th>
                            <th>Mileage</th>
                            <th>Year</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="vehiclesBody">
                        {% for vehicle in vehicles %}
                        <tr data-id="{{ vehicle.id }}">
                            <td>{{ vehicle.id }}</td>
                            <td class="truncate" title="{{ vehicle.title }}">{{ vehicle.title }}</td>
                            <td>{{ vehicle.price }}</td>
                            <td>{{ vehicle.mileage }}</td>
                            <td>{{ vehicle.year }}</td>
                            <td>{{ vehicle.created_at }}</td>
                            <td class="actions">
                                <button class="btn btn-sm btn-secondary" onclick="editVehicle({{ vehicle.id }})">Edit</button>
                                <button class="btn btn-sm btn-danger" onclick="deleteVehicle({{ vehicle.id }})">Delete</button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% if not vehicles %}
                <div class="empty-state">
                    <h3>No vehicles yet</h3>
                    <p>Vehicles will appear here when you search and create offers.</p>
                </div>
                {% endif %}
            </div>
        </div>
        
        <!-- Offers Tab -->
        <div id="offersTab" class="tab-content">
            <div class="data-section">
                <div class="section-header">
                    <h2>Offers</h2>
                </div>
                <table id="offersTable">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Vehicle</th>
                            <th>Client Email</th>
                            <th>Client Name</th>
                            <th>Offered Price</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="offersBody">
                        {% for offer in offers %}
                        <tr data-id="{{ offer.id }}">
                            <td>{{ offer.id }}</td>
                            <td class="truncate" title="{{ offer.vehicle_title }}">{{ offer.vehicle_title }}</td>
                            <td>{{ offer.client_email }}</td>
                            <td>{{ offer.client_name or '-' }}</td>
                            <td>{{ offer.offered_price }} &euro;</td>
                            <td>{{ offer.created_at }}</td>
                            <td class="actions">
                                <button class="btn btn-sm btn-success" onclick="downloadOfferPDF({{ offer.id }})">PDF</button>
                                <button class="btn btn-sm btn-secondary" onclick="editOffer({{ offer.id }})">Edit</button>
                                <button class="btn btn-sm btn-danger" onclick="deleteOffer({{ offer.id }})">Delete</button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% if not offers %}
                <div class="empty-state">
                    <h3>No offers yet</h3>
                    <p>Offers will appear here when you create them from vehicle details.</p>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
    
    <!-- Edit Vehicle Modal -->
    <div id="vehicleModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="vehicleModalTitle">Edit Vehicle</h2>
                <button class="close-btn" onclick="closeModal('vehicleModal')">&times;</button>
            </div>
            <form id="vehicleForm">
                <input type="hidden" id="vehicleId">
                <div class="form-group">
                    <label for="vehicleTitle">Title</label>
                    <input type="text" id="vehicleTitle" required>
                </div>
                <div class="form-group">
                    <label for="vehiclePrice">Price</label>
                    <input type="text" id="vehiclePrice">
                </div>
                <div class="form-group">
                    <label for="vehicleMileage">Mileage</label>
                    <input type="text" id="vehicleMileage">
                </div>
                <div class="form-group">
                    <label for="vehicleYear">Year</label>
                    <input type="text" id="vehicleYear">
                </div>
                <div class="form-group">
                    <label for="vehicleFuel">Fuel Type</label>
                    <input type="text" id="vehicleFuel">
                </div>
                <div class="form-group">
                    <label for="vehicleTransmission">Transmission</label>
                    <input type="text" id="vehicleTransmission">
                </div>
                <div class="form-group">
                    <label for="vehiclePower">Power</label>
                    <input type="text" id="vehiclePower">
                </div>
                <div class="form-group">
                    <label for="vehicleUrl">URL</label>
                    <input type="text" id="vehicleUrl">
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal('vehicleModal')">Cancel</button>
                    <button type="submit" class="btn btn-primary">Save</button>
                </div>
            </form>
        </div>
    </div>
    
    <!-- Edit Offer Modal -->
    <div id="offerModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Edit Offer</h2>
                <button class="close-btn" onclick="closeModal('offerModal')">&times;</button>
            </div>
            <form id="offerForm">
                <input type="hidden" id="offerId">
                <div class="form-group">
                    <label for="offerClientEmail">Client Email</label>
                    <input type="email" id="offerClientEmail" required>
                </div>
                <div class="form-group">
                    <label for="offerClientName">Client Name</label>
                    <input type="text" id="offerClientName">
                </div>
                <div class="form-group">
                    <label for="offerPrice">Offered Price (&euro;)</label>
                    <input type="text" id="offerPrice" required>
                </div>
                <div class="form-group">
                    <label for="offerNotes">Notes</label>
                    <textarea id="offerNotes"></textarea>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal('offerModal')">Cancel</button>
                    <button type="submit" class="btn btn-primary">Save</button>
                </div>
            </form>
        </div>
    </div>
    
    <script>
        // Store data
        let vehiclesData = {{ vehicles_json | safe }};
        let offersData = {{ offers_json | safe }};
        
        // Tab switching
        function showTab(tab) {
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            event.target.classList.add('active');
            document.getElementById(tab + 'Tab').classList.add('active');
        }
        
        // Modal functions
        function openModal(modalId) {
            document.getElementById(modalId).classList.add('active');
        }
        
        function closeModal(modalId) {
            document.getElementById(modalId).classList.remove('active');
        }
        
        // Show message
        function showMessage(text, type) {
            const area = document.getElementById('messageArea');
            area.innerHTML = `<div class="message ${type}">${text}</div>`;
            setTimeout(() => area.innerHTML = '', 5000);
        }
        
        // Vehicle CRUD
        function openAddVehicleModal() {
            document.getElementById('vehicleModalTitle').textContent = 'Add Vehicle';
            document.getElementById('vehicleForm').reset();
            document.getElementById('vehicleId').value = '';
            openModal('vehicleModal');
        }
        
        function editVehicle(id) {
            fetch(`/api/admin/vehicles/${id}`)
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        const v = data.vehicle;
                        document.getElementById('vehicleModalTitle').textContent = 'Edit Vehicle';
                        document.getElementById('vehicleId').value = v.id;
                        document.getElementById('vehicleTitle').value = v.title || '';
                        document.getElementById('vehiclePrice').value = v.price || '';
                        document.getElementById('vehicleMileage').value = v.mileage || '';
                        document.getElementById('vehicleYear').value = v.year || '';
                        document.getElementById('vehicleFuel').value = v.fuel || '';
                        document.getElementById('vehicleTransmission').value = v.transmission || '';
                        document.getElementById('vehiclePower').value = v.power || '';
                        document.getElementById('vehicleUrl').value = v.url || '';
                        openModal('vehicleModal');
                    }
                });
        }
        
        function deleteVehicle(id) {
            if (confirm('Are you sure you want to delete this vehicle? This will also delete all related offers.')) {
                fetch(`/api/admin/vehicles/${id}`, { method: 'DELETE' })
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            showMessage('Vehicle deleted successfully', 'success');
                            location.reload();
                        } else {
                            showMessage(data.error || 'Failed to delete vehicle', 'error');
                        }
                    });
            }
        }
        
        document.getElementById('vehicleForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const id = document.getElementById('vehicleId').value;
            const data = {
                title: document.getElementById('vehicleTitle').value,
                price: document.getElementById('vehiclePrice').value,
                mileage: document.getElementById('vehicleMileage').value,
                year: document.getElementById('vehicleYear').value,
                fuel: document.getElementById('vehicleFuel').value,
                transmission: document.getElementById('vehicleTransmission').value,
                power: document.getElementById('vehiclePower').value,
                url: document.getElementById('vehicleUrl').value
            };
            
            const url = id ? `/api/admin/vehicles/${id}` : '/api/admin/vehicles';
            const method = id ? 'PUT' : 'POST';
            
            fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showMessage('Vehicle saved successfully', 'success');
                    closeModal('vehicleModal');
                    location.reload();
                } else {
                    showMessage(data.error || 'Failed to save vehicle', 'error');
                }
            });
        });
        
        // Offer CRUD
        function editOffer(id) {
            fetch(`/api/admin/offers/${id}`)
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        const o = data.offer;
                        document.getElementById('offerId').value = o.id;
                        document.getElementById('offerClientEmail').value = o.client_email || '';
                        document.getElementById('offerClientName').value = o.client_name || '';
                        document.getElementById('offerPrice').value = o.offered_price || '';
                        document.getElementById('offerNotes').value = o.notes || '';
                        openModal('offerModal');
                    }
                });
        }
        
        function deleteOffer(id) {
            if (confirm('Are you sure you want to delete this offer?')) {
                fetch(`/api/admin/offers/${id}`, { method: 'DELETE' })
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            showMessage('Offer deleted successfully', 'success');
                            location.reload();
                        } else {
                            showMessage(data.error || 'Failed to delete offer', 'error');
                        }
                    });
            }
        }
        
        function downloadOfferPDF(id) {
            window.open(`/api/download-offer-pdf/${id}`, '_blank');
        }
        
        document.getElementById('offerForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const id = document.getElementById('offerId').value;
            const data = {
                client_email: document.getElementById('offerClientEmail').value,
                client_name: document.getElementById('offerClientName').value,
                offered_price: document.getElementById('offerPrice').value,
                notes: document.getElementById('offerNotes').value
            };
            
            fetch(`/api/admin/offers/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showMessage('Offer updated successfully', 'success');
                    closeModal('offerModal');
                    location.reload();
                } else {
                    showMessage(data.error || 'Failed to update offer', 'error');
                }
            });
        });
        
        // Close modal on outside click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', function(e) {
                if (e.target === this) closeModal(this.id);
            });
        });
    </script>
</body>
</html>
'''

def parse_number(value_str):
    """Parse a number string that may contain European formatting (commas, dots, spaces)"""
    if not value_str or value_str == 'N/A':
        return None
    
    # Convert to string and clean up
    s = str(value_str)
    
    # Remove common suffixes and prefixes
    s = s.replace('km', '').replace('€', '').replace('EUR', '')
    
    # Remove all types of spaces (including non-breaking space \xa0)
    s = s.replace(' ', '').replace('\xa0', '').replace('\u00a0', '')
    
    # Remove thousand separators (both comma and dot can be used)
    # European format: 110.000 or 110,000
    # We need to detect which is the decimal separator
    
    # If there's both comma and dot, the last one is likely decimal
    # For mileage/price, we typically don't have decimals, so remove both
    s = s.replace(',', '').replace('.', '')
    
    # Strip any remaining whitespace
    s = s.strip()
    
    # Try to convert to integer
    try:
        return int(s) if s else None
    except ValueError:
        # Try to extract just digits
        digits = ''.join(c for c in s if c.isdigit())
        return int(digits) if digits else None

def filter_listings(listings, criteria):
    """Filter listings based on search criteria"""
    filtered = []
    
    for item in listings:
        try:
            # Parse year
            year_str = item.get('year', '')
            if year_str and year_str != 'N/A':
                year = int(year_str.split('/')[-1]) if '/' in str(year_str) else int(year_str)
            else:
                year = None
            
            # Parse mileage using the robust parser
            mileage = parse_number(item.get('mileage', ''))
            
            # Parse price using the robust parser
            price = parse_number(item.get('price', ''))
            
            # Log for debugging
            logger.debug(f'Filtering: {item.get("title", "Unknown")} - mileage={mileage}, price={price}, year={year}')
            
            # Apply year filter
            if criteria.get('modelYear'):
                min_year = int(criteria['modelYear'])
                if year and year < min_year:
                    logger.debug(f'Filtered out by year: {year} < {min_year}')
                    continue
            
            # Apply mileage filter
            if criteria.get('mileage'):
                max_mileage = int(criteria['mileage'])
                if mileage is not None and mileage > max_mileage:
                    logger.debug(f'Filtered out by mileage: {mileage} > {max_mileage}')
                    continue
            
            # Apply price filter
            if criteria.get('price'):
                max_price = int(criteria['price'])
                if price is not None and price > max_price:
                    logger.debug(f'Filtered out by price: {price} > {max_price}')
                    continue
            
            filtered.append(item)
        except Exception as e:
            logger.warning(f'Error filtering item {item.get("title")}: {str(e)}')
            filtered.append(item)
    
    return filtered

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, 
                                 vehicles=VEHICLES,
                                 vehicles_json=json.dumps(VEHICLES),
                                 features=FEATURES)

@app.route('/api/vehicle-details', methods=['POST'])
def get_vehicle_details():
    """Fetch detailed vehicle information from Mobile.de URL"""
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            logger.error('No URL provided')
            return jsonify({'success': False, 'error': 'URL not provided'}), 400
        
        logger.info(f'Fetching vehicle details from: {url}')
        
        if not apify_client:
            logger.error('Apify API key not configured')
            return jsonify({'success': False, 'error': 'Apify API key not configured'}), 500
        
        run_input = {
            "maxRecords": 1,
            "urls": [{"url": url}]
        }
        
        logger.info(f'Starting Apify run with input: {run_input}')
        run = apify_client.actor("ivanvs/mobile-de-scraper").call(run_input=run_input)
        logger.info(f'Apify run result: {run}')
        
        if run:
            dataset_id = run.get('defaultDatasetId') or run.get('datasetId')
            logger.info(f'Dataset ID: {dataset_id}')
            
            if dataset_id:
                try:
                    dataset_items = apify_client.dataset(dataset_id).list_items()
                    logger.info(f'Got {len(dataset_items.items)} items from dataset')
                    
                    if dataset_items.items:
                        item = dataset_items.items[0]
                        logger.info(f'Got vehicle details: {item.get("title")}')
                        
                        price = item.get('price', 'N/A')
                        if isinstance(price, dict):
                            price = price.get('amount', 'N/A')
                        
                        properties = item.get('properties', {})
                        mileage = properties.get('milage', item.get('mileage', 'N/A'))
                        year = properties.get('firstRegistration', item.get('year', 'N/A'))
                        
                        details = {
                            'title': item.get('title', 'N/A'),
                            'price': str(price) if price != 'N/A' else 'N/A',
                            'url': item.get('url', url),
                            'mileage': str(mileage) if mileage != 'N/A' else 'N/A',
                            'year': str(year) if year != 'N/A' else 'N/A',
                            'fuel': item.get('fuel', 'N/A'),
                            'transmission': item.get('transmission', 'N/A'),
                            'power': item.get('power', 'N/A'),
                            'properties': properties
                        }
                        
                        try:
                            vehicle_id = save_vehicle_to_db(details)
                            
                            logger.info(f'Returning details: {details}')
                            return jsonify({
                                'success': True,
                                'details': details,
                                'vehicle_id': vehicle_id
                            })
                        except Exception as e:
                            logger.error(f'Error saving vehicle: {str(e)}')
                            return jsonify({
                                'success': True,
                                'details': details,
                                'vehicle_id': None
                            })
                    else:
                        logger.error('No items in dataset')
                except Exception as e:
                    logger.error(f'Error fetching dataset: {str(e)}', exc_info=True)
            else:
                logger.error('No dataset ID found in run result')
        else:
            logger.error('No run result from Apify')
        
        return jsonify({'success': False, 'error': 'Could not fetch vehicle details'}), 500
        
    except Exception as e:
        logger.error(f'Vehicle details error: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/create-offer', methods=['POST'])
def create_offer():
    """Create an offer and save to database"""
    try:
        data = request.json
        vehicle_data = data.get('vehicle_data')
        client_email = data.get('client_email')
        client_name = data.get('client_name')
        offered_price = data.get('offered_price')
        notes = data.get('notes')
        
        logger.info(f'Creating offer for {client_email}')
        logger.info(f'Vehicle data received: {vehicle_data}')
        
        if not vehicle_data:
            return jsonify({'success': False, 'error': 'Vehicle data is missing'}), 400
        
        if not isinstance(vehicle_data, dict):
            return jsonify({'success': False, 'error': 'Vehicle data must be a dictionary'}), 400
        
        if not validate_email(client_email):
            return jsonify({'success': False, 'error': 'Invalid email address'}), 400
        
        # Ensure vehicle_data has required fields
        vehicle_dict = {
            'title': vehicle_data.get('title', 'N/A'),
            'price': vehicle_data.get('price', 'N/A'),
            'mileage': vehicle_data.get('mileage', 'N/A'),
            'year': vehicle_data.get('year', 'N/A'),
            'fuel': vehicle_data.get('fuel', 'N/A'),
            'transmission': vehicle_data.get('transmission', 'N/A'),
            'power': vehicle_data.get('power', 'N/A'),
            'url': vehicle_data.get('url', ''),
            'properties': vehicle_data.get('properties', {})
        }
        
        logger.info(f'Processed vehicle dict: {vehicle_dict}')
        
        try:
            vehicle_id = save_vehicle_to_db(vehicle_dict)
        except Exception as e:
            logger.error(f'Error saving vehicle: {str(e)}', exc_info=True)
            vehicle_id = None
        
        if not vehicle_id:
            return jsonify({'success': False, 'error': 'Could not save vehicle data'}), 500
        
        offer_dict = {
            'vehicle_id': vehicle_id,
            'client_email': client_email,
            'client_name': client_name,
            'offered_price': offered_price,
            'notes': notes
        }
        
        offer_id = save_offer_to_db(offer_dict)
        
        if not offer_id:
            return jsonify({'success': False, 'error': 'Could not create offer'}), 500
        
        logger.info(f'Offer created with ID: {offer_id}')
        
        return jsonify({
            'success': True,
            'offer_id': offer_id,
            'vehicle_id': vehicle_id
        })
        
    except Exception as e:
        logger.error(f'Error creating offer: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download-offer-pdf/<int:offer_id>', methods=['GET'])
def download_offer_pdf(offer_id):
    """Generate and download PDF for an offer"""
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgres':
            cursor.execute('''
                SELECT o.vehicle_id, o.client_email, o.client_name, o.offered_price, o.notes
                FROM offers o WHERE o.id = %s
            ''', (offer_id,))
        else:
            cursor.execute('''
                SELECT o.vehicle_id, o.client_email, o.client_name, o.offered_price, o.notes
                FROM offers o WHERE o.id = ?
            ''', (offer_id,))
        
        offer_row = cursor.fetchone()
        if not offer_row:
            conn.close()
            return jsonify({'success': False, 'error': 'Offer not found'}), 404
        
        vehicle_id, client_email, client_name, offered_price, notes = offer_row
        
        if db_type == 'postgres':
            cursor.execute('''
                SELECT title, price, mileage, year, fuel, transmission, power, url, properties
                FROM vehicles WHERE id = %s
            ''', (vehicle_id,))
        else:
            cursor.execute('''
                SELECT title, price, mileage, year, fuel, transmission, power, url, properties
                FROM vehicles WHERE id = ?
            ''', (vehicle_id,))
        
        vehicle_row = cursor.fetchone()
        conn.close()
        
        if not vehicle_row:
            return jsonify({'success': False, 'error': 'Vehicle not found'}), 404
        
        vehicle_data = {
            'title': vehicle_row[0],
            'price': vehicle_row[1],
            'mileage': vehicle_row[2],
            'year': vehicle_row[3],
            'fuel': vehicle_row[4],
            'transmission': vehicle_row[5],
            'power': vehicle_row[6],
            'url': vehicle_row[7],
            'properties': json.loads(vehicle_row[8]) if vehicle_row[8] else {}
        }
        
        offer_data = {
            'offered_price': offered_price,
            'notes': notes
        }
        
        pdf_bytes = generate_offer_pdf(vehicle_data, offer_data, client_email)
        
        return send_file(
            BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'offer_{offer_id}.pdf'
        )
        
    except Exception as e:
        logger.error(f'Error downloading PDF: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# ADMIN API ENDPOINTS
# ============================================================================

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard page"""
    vehicles = get_all_vehicles()
    offers = get_all_offers()
    stats = get_dashboard_stats()
    
    return render_template_string(ADMIN_TEMPLATE,
                                 vehicles=vehicles,
                                 offers=offers,
                                 stats=stats,
                                 vehicles_json=json.dumps(vehicles),
                                 offers_json=json.dumps(offers))

@app.route('/api/admin/vehicles', methods=['GET'])
def api_get_vehicles():
    """Get all vehicles"""
    vehicles = get_all_vehicles()
    return jsonify({'success': True, 'vehicles': vehicles})

@app.route('/api/admin/vehicles/<int:vehicle_id>', methods=['GET'])
def api_get_vehicle(vehicle_id):
    """Get single vehicle"""
    vehicle = get_vehicle_by_id(vehicle_id)
    if vehicle:
        return jsonify({'success': True, 'vehicle': vehicle})
    return jsonify({'success': False, 'error': 'Vehicle not found'}), 404

@app.route('/api/admin/vehicles', methods=['POST'])
def api_create_vehicle():
    """Create new vehicle"""
    try:
        data = request.json
        vehicle_id = save_vehicle_to_db(data)
        if vehicle_id:
            return jsonify({'success': True, 'vehicle_id': vehicle_id})
        return jsonify({'success': False, 'error': 'Failed to create vehicle'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/vehicles/<int:vehicle_id>', methods=['PUT'])
def api_update_vehicle(vehicle_id):
    """Update vehicle"""
    try:
        data = request.json
        if update_vehicle(vehicle_id, data):
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Failed to update vehicle'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/vehicles/<int:vehicle_id>', methods=['DELETE'])
def api_delete_vehicle(vehicle_id):
    """Delete vehicle"""
    try:
        if delete_vehicle(vehicle_id):
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Failed to delete vehicle'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/offers', methods=['GET'])
def api_get_offers():
    """Get all offers"""
    offers = get_all_offers()
    return jsonify({'success': True, 'offers': offers})

@app.route('/api/admin/offers/<int:offer_id>', methods=['GET'])
def api_get_offer(offer_id):
    """Get single offer"""
    offer = get_offer_by_id(offer_id)
    if offer:
        return jsonify({'success': True, 'offer': offer})
    return jsonify({'success': False, 'error': 'Offer not found'}), 404

@app.route('/api/admin/offers/<int:offer_id>', methods=['PUT'])
def api_update_offer(offer_id):
    """Update offer"""
    try:
        data = request.json
        if update_offer(offer_id, data):
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Failed to update offer'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/offers/<int:offer_id>', methods=['DELETE'])
def api_delete_offer(offer_id):
    """Delete offer"""
    try:
        if delete_offer(offer_id):
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Failed to delete offer'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/stats', methods=['GET'])
def api_get_stats():
    """Get dashboard statistics"""
    stats = get_dashboard_stats()
    return jsonify({'success': True, 'stats': stats})

@app.route('/api/search', methods=['POST'])
def search():
    """Search for vehicles using Apify"""
    try:
        data = request.json
        make = data.get('make', '').lower()
        model = data.get('model', '').lower()

        logger.info(f'Searching for {make} {model}')
        logger.info(f'Form data: {json.dumps(data, indent=2)}')

        if make not in VEHICLES or model not in VEHICLES[make]['models']:
            return jsonify({'success': False, 'error': 'Vehicle not found'}), 404

        search_url = VEHICLES[make]['models'][model]['url']
        logger.info(f'Using URL: {search_url}')

        if not apify_client:
            return jsonify({'success': False, 'error': 'Apify API key not configured'}), 500

        max_records = 20 if os.getenv('FLASK_ENV') == 'development' else 50
        logger.info(f'Scraping with max {max_records} results')

        run_input = {
            "maxRecords": max_records,
            "urls": [{"url": search_url}]
        }

        run = apify_client.actor("ivanvs/mobile-de-scraper").call(run_input=run_input)
        
        listings = []
        if run:
            logger.info(f'Apify run completed')
            if 'defaultDatasetId' in run:
                dataset_id = run['defaultDatasetId']
            elif 'datasetId' in run:
                dataset_id = run['datasetId']
            else:
                dataset_id = None
            
            if dataset_id:
                logger.info(f'Fetching results from dataset: {dataset_id}')
                try:
                    dataset_items = apify_client.dataset(dataset_id).list_items()
                    logger.info(f'Got {len(dataset_items.items)} items from Apify')
                    for item in dataset_items.items:
                        price = item.get('price', 'N/A')
                        if isinstance(price, dict):
                            price = price.get('amount', 'N/A')
                        
                        properties = item.get('properties', {})
                        mileage = properties.get('milage', 'N/A')
                        year = properties.get('firstRegistration', 'N/A')
                        
                        listing = {
                            'title': item.get('title', item.get('name', 'Vehicle')),
                            'price': str(price) if price != 'N/A' else 'N/A',
                            'mileage': str(mileage) if mileage != 'N/A' else 'N/A',
                            'year': str(year) if year != 'N/A' else 'N/A',
                            'url': item.get('url', item.get('link', ''))
                        }
                        listings.append(listing)
                except Exception as e:
                    logger.error(f'Error fetching dataset: {str(e)}')

        filtered_listings = filter_listings(listings, data)
        logger.info(f'After filtering: {len(filtered_listings)} listings (from {len(listings)} total)')
        
        return jsonify({
            'success': True,
            'total': len(filtered_listings),
            'listings': filtered_listings,
            'filters_applied': data
        })

    except Exception as e:
        logger.error(f'Search error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

# Initialize database on import (for gunicorn)
init_database()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    logger.info(f'Starting app on port {port} (debug={debug_mode})')
    app.run(debug=debug_mode, port=port, host='0.0.0.0')
