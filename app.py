import os
from flask import Flask, request, jsonify, render_template, send_from_directory
from fpdf import FPDF
import json
from datetime import datetime

app = Flask(__name__)

# Base directory for saving invoices (on the Desktop)
BASE_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "hotel_invoices")
os.makedirs(BASE_DIR, exist_ok=True)

# Custom PDF class for invoice
class InvoicePDF(FPDF):
    def header(self):
        # Set font to Arial (normal font)
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'APR grand Invoice', ln=True, align='C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', '', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def invoice_body(self, customer_name, room_details, total_amount, advance_amount, balance_amount, checkin_date, checkout_date):
        self.set_font('Arial', '', 12)
        
        # Customer and Stay Information
        self.cell(0, 10, f'Customer Name: {customer_name}', ln=True)
        self.cell(0, 10, f'Check-in Date: {checkin_date}', ln=True)
        self.cell(0, 10, f'Checkout Date: {checkout_date}', ln=True)
        self.ln(5)

        # Room Details Table
        self.set_font('Arial', 'B', 12)
        self.cell(40, 10, 'Room Type', 1, 0, 'C')
        self.cell(30, 10, 'Quantity', 1, 0, 'C')
        self.cell(30, 10, 'Days', 1, 0, 'C')
        self.cell(30, 10, 'Price/Day', 1, 0, 'C')
        self.cell(40, 10, 'Total Price', 1, 1, 'C')

        self.set_font('Arial', '', 12)
        for room in room_details:
            room_type = room.get('room_type', 'N/A')
            quantity = room.get('quantity', 0)
            days = room.get('days', 1)  # Default to 1 if not provided
            price = room.get('price', 0)
            total_price = room.get('total_price', 0)

            self.cell(40, 10, room_type, 1, 0, 'C')
            self.cell(30, 10, str(quantity), 1, 0, 'C')
            self.cell(30, 10, str(days), 1, 0, 'C')
            self.cell(30, 10, f'Rs {price}', 1, 0, 'C')
            self.cell(40, 10, f'Rs {total_price}', 1, 1, 'C')

        self.ln(5)

        # Total Amount Section
        self.set_font('Arial', 'B', 12)
        self.cell(130, 10, 'Total Amount:', 0, 0, 'R')
        self.set_font('Arial', '', 12)
        self.cell(40, 10, f'Rs {total_amount}', 0, 1, 'C')

        self.set_font('Arial', 'B', 12)
        self.cell(130, 10, 'Advance Amount:', 0, 0, 'R')
        self.set_font('Arial', '', 12)
        self.cell(40, 10, f'Rs {advance_amount}', 0, 1, 'C')

        self.set_font('Arial', 'B', 12)
        self.cell(130, 10, 'Balance Amount:', 0, 0, 'R')
        self.set_font('Arial', '', 12)
        self.cell(40, 10, f'Rs {balance_amount}', 0, 1, 'C')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate_invoice', methods=['POST'])
def generate_invoice():
    try:
        # Retrieve data from form
        customer_name = request.form.get('customer_name', 'Unknown Customer')
        checkin_date = request.form.get('checkin_date', datetime.now().strftime('%Y-%m-%d'))
        checkout_date = request.form.get('checkout_date', datetime.now().strftime('%Y-%m-%d'))
        room_details = request.form.get('room_details', '[]')
        total_amount = float(request.form.get('total_amount', 0))
        advance_amount = float(request.form.get('advance_amount', 0))

        # Ensure no negative numbers for amounts
        if total_amount < 0 or advance_amount < 0:
            return jsonify({"error": "Amounts cannot be negative"}), 400

        # Calculate balance amount
        balance_amount = total_amount - advance_amount
        if balance_amount < 0:
            return jsonify({"error": "Advance amount cannot exceed total amount"}), 400

        # Parse room details
        try:
            room_details = json.loads(room_details)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON format for room details"}), 400

        # Create a folder for check-in date if not already existing
        folder_name = checkin_date
        folder_path = os.path.join(BASE_DIR, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        # Create invoice PDF
        pdf = InvoicePDF()
        pdf.add_page()
        pdf.invoice_body(customer_name, room_details, total_amount, advance_amount, balance_amount, checkin_date, checkout_date)

        # Save the PDF to a file with customer name and total amount
        filename = f'{customer_name.replace(" ", "_")}_{total_amount}_invoice.pdf'
        file_path = os.path.join(folder_path, filename)
        pdf.output(file_path)

        # Return a link to the generated PDF file
        return jsonify({
            "message": "Invoice generated successfully",
            "file_path": f"/download/{folder_name}/{filename}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/view_invoice/<folder_name>/<filename>')
def view_invoice(folder_name, filename):
    file_path = os.path.join(BASE_DIR, folder_name, filename)
    if os.path.exists(file_path):
        return send_from_directory(directory=os.path.dirname(file_path), path=filename)
    else:
        return jsonify({"error": "File not found"}), 404

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
