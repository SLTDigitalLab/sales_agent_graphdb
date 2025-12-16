import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv() 

# Retrieve email settings from environment variables
SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER")
SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", 587))
SENDER_EMAIL = os.getenv("EMAIL_ADDRESS")
SENDER_PASSWORD = os.getenv("EMAIL_PASSWORD")
TARGET_EMAIL = os.getenv("EMAIL_TARGET_ADDRESS")

def send_order_request_email(request_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Sends two emails:
    1. A notification to the internal team (TARGET_EMAIL).
    2. A confirmation receipt to the customer (customer_email).

    Args:
        request_data: A dictionary containing items (list of product/quantity), customer info, etc.

    Returns:
        A dictionary indicating success or failure.
    """
    if not all([SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, TARGET_EMAIL]):
        print("Email configuration is missing in environment variables.")
        return {"status": "error", "message": "Email configuration is missing."}

    # Extract items and customer info once to use in both emails
    items = request_data.get('items', [])
    customer_name = request_data.get('customer_name', 'Valued Customer')
    customer_email = request_data.get('customer_email')
    customer_phone = request_data.get('customer_phone', 'N/A')
    customer_address = request_data.get('customer_address', 'N/A')
    notes = request_data.get('notes', 'N/A')

    # Format the list of items for the email body
    items_body = ""
    for item in items:
        items_body += f"  - {item.get('product_name', 'Unknown Product')} (Qty: {item.get('quantity', 1)})\n"

    try:
        # Establish the connection ONCE for both emails
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls() 
        server.login(SENDER_EMAIL, SENDER_PASSWORD)

        # SEND INTERNAL NOTIFICATION EMAIL 
        msg_internal = MIMEMultipart()
        msg_internal['From'] = SENDER_EMAIL
        msg_internal['To'] = TARGET_EMAIL
        msg_internal['Subject'] = f"New Order Request: {customer_name}"

        internal_body = f"""
        A new order request has been submitted via the AI Agent.

        Requested Items:
        {items_body}

        Customer Details:
        - Name: {customer_name}
        - Email: {customer_email}
        - Phone: {customer_phone}
        - Address: {customer_address}
        - Notes: {notes}

        Please contact the customer to confirm this order.
        """
        msg_internal.attach(MIMEText(internal_body, 'plain'))
        server.sendmail(SENDER_EMAIL, TARGET_EMAIL, msg_internal.as_string())
        print(f"Internal order notification sent to {TARGET_EMAIL}")

        # SEND CUSTOMER CONFIRMATION EMAIL
        # Only attempt if have a valid looking customer email
        if customer_email and "@" in customer_email:
            msg_customer = MIMEMultipart()
            msg_customer['From'] = SENDER_EMAIL
            msg_customer['To'] = customer_email
            msg_customer['Subject'] = "Order Request Received - SLT-MOBITEL AI Assistant"

            customer_body = f"""
            Dear {customer_name},

            Thank you for your interest in our products. 
            
            We have received your request for the following items:
            {items_body}

            Our sales team has been notified. They will review your request and contact you shortly at {customer_phone} to finalize the order.

            Thank you,
            The SLT-MOBITEL Team
            """
            msg_customer.attach(MIMEText(customer_body, 'plain'))
            server.sendmail(SENDER_EMAIL, customer_email, msg_customer.as_string())
            print(f"Customer confirmation sent to {customer_email}")
        else:
            print("Skipping customer email: Invalid or missing email address.")

        # Close connection
        server.quit()

        return {"status": "success", "message": "Order request processed and emails sent."}

    except smtplib.SMTPAuthenticationError:
        print("SMTP Authentication Error: Check your email address and App Password.")
        return {"status": "error", "message": "Authentication failed. Check email settings."}
    except smtplib.SMTPRecipientsRefused:
        print(f"Recipient address rejected.")
        return {"status": "error", "message": "Recipient address refused."}
    except Exception as e:
        print(f"Error sending email: {e}")
        return {"status": "error", "message": f"An error occurred: {str(e)}"}