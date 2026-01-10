import smtplib
import os
from email.mime.text import MIMEText
import textwrap
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from typing import Dict, Any

# IMPORT LOGGER
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

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
        logger.error("Email configuration is missing in environment variables.")
        return {"status": "error", "message": "Email configuration is missing."}

    # Extract items and customer info once to use in both emails
    items = request_data.get('items', [])
    customer_name = request_data.get('customer_name', 'Valued Customer')
    customer_email = request_data.get('customer_email')
    customer_phone = request_data.get('customer_phone', 'N/A')
    customer_address = request_data.get('customer_address', 'N/A')
    notes = request_data.get('notes', 'N/A')

    items_body = ""
    for item in items:
        items_body += f"- {item.get('product_name', 'Unknown Product')} (Quantity: {item.get('quantity', 1)})\n"

    try:
        # Establish the connection ONCE for both emails
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls() 
        server.login(SENDER_EMAIL, SENDER_PASSWORD)

        # SEND NOTIFICATION EMAIL TO SALES TEAM 
        msg_internal = MIMEMultipart()
        msg_internal['From'] = SENDER_EMAIL
        msg_internal['To'] = TARGET_EMAIL
        msg_internal['Subject'] = f"New Order Request: {customer_name}"

        # Order notification email body
        internal_body = textwrap.dedent(f"""
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
        """)
        
        msg_internal.attach(MIMEText(internal_body, 'plain'))
        server.sendmail(SENDER_EMAIL, TARGET_EMAIL, msg_internal.as_string())
        logger.info(f"Internal order notification sent to {TARGET_EMAIL}")

        # SEND CUSTOMER CONFIRMATION EMAIL 
        if customer_email and "@" in customer_email:
            msg_customer = MIMEMultipart()
            msg_customer['From'] = SENDER_EMAIL
            msg_customer['To'] = customer_email
            msg_customer['Subject'] = "Order Request Received - SLT-MOBITEL AI Assistant"

            # Customer email body
            customer_body = textwrap.dedent(f"""
            Dear {customer_name},

            Thank you for your interest in our products. 
            
            We have received your request for the following items:
            {items_body}

            Our sales team has been notified. They will review your request and contact you at {customer_phone} to finalize the order.

            Thank you.
            """)
            
            msg_customer.attach(MIMEText(customer_body, 'plain'))
            server.sendmail(SENDER_EMAIL, customer_email, msg_customer.as_string())
            logger.info(f"Customer confirmation sent to {customer_email}")
        else:
            logger.warning("Skipping customer email: Invalid or missing email address.")

        # Close connection
        server.quit()

        return {"status": "success", "message": "Order request processed and emails sent."}

    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP Authentication Error: Check your email address and App Password.")
        return {"status": "error", "message": "Authentication failed. Check email settings."}
    except smtplib.SMTPRecipientsRefused:
        logger.error(f"Recipient address refused.")
        return {"status": "error", "message": "Recipient address refused."}
    except Exception as e:
        logger.error(f"Error sending email: {e}", exc_info=True)
        return {"status": "error", "message": f"An error occurred: {str(e)}"}