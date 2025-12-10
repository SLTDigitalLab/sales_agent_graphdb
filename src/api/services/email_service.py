import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv() # Load environment variables

# Retrieve email settings from environment variables
SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER")
SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", 587))
SENDER_EMAIL = os.getenv("EMAIL_ADDRESS")
SENDER_PASSWORD = os.getenv("EMAIL_PASSWORD")
TARGET_EMAIL = os.getenv("EMAIL_TARGET_ADDRESS")

def send_order_request_email(request_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Sends an email containing the order request details, including multiple items.

    Args:
        request_ A dictionary containing items (list of product/quantity), customer info, etc.

    Returns:
        A dictionary indicating success or failure.
    """
    if not all([SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, TARGET_EMAIL]):
        print("Email configuration is missing in environment variables.")
        return {"status": "error", "message": "Email configuration is missing."}

    try:
        # Create the email message
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = TARGET_EMAIL
        msg['Subject'] = f"New Multi-Product Order Request from AI Agent User: {request_data.get('customer_name', 'Unknown')}"

        # Extract items and customer info
        items = request_data.get('items', [])
        customer_name = request_data.get('customer_name', 'N/A')
        customer_email = request_data.get('customer_email', 'N/A')
        customer_phone = request_data.get('customer_phone', 'N/A')
        customer_address = request_data.get('customer_address', 'N/A')
        notes = request_data.get('notes', 'N/A')

        # Create the email body
        # List the items first
        items_body = "Items Requested:\n"
        for item in items:
            items_body += f"  - Product: {item.get('product_name', 'N/A')}, Quantity: {item.get('quantity', 'N/A')}\n"

        body = f"""
        A new multi-product order request has been submitted via the AI Enterprise Agent.

        {items_body}

        Customer Details:
        - Customer Name: {customer_name}
        - Customer Email: {customer_email}
        - Customer Phone: {customer_phone}
        - Customer Address: {customer_address}
        - Additional Notes: {notes}

        Please contact the customer using the provided details.
        """
        msg.attach(MIMEText(body, 'plain'))

        # Connect to the server and send the email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Enable encryption
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, TARGET_EMAIL, text)
        server.quit()

        print(f"Multi-product order request email sent successfully to {TARGET_EMAIL}")
        return {"status": "success", "message": "Multi-product order request sent successfully."}

    except smtplib.SMTPAuthenticationError:
        print("SMTP Authentication Error: Check your email address and App Password.")
        return {"status": "error", "message": "Authentication failed. Check email settings."}
    except smtplib.SMTPRecipientsRefused:
        print(f"Recipient address rejected: {TARGET_EMAIL}")
        return {"status": "error", "message": f"Recipient address refused: {TARGET_EMAIL}"}
    except Exception as e:
        print(f"Error sending email: {e}")
        return {"status": "error", "message": f"An error occurred: {str(e)}"}

# Example usage (for testing purposes):
# if __name__ == "__main__":
#     sample_data = {
#         "items": [ # Note the 'items' key containing a list
#             {"product_name": "Tenda Mx3 2 Pack Mesh Wi-Fi 6 System", "quantity": 2},
#             {"product_name": "Power Adaptor for Motorola Cordless Phone", "quantity": 1}
#         ],
#         "customer_name": "John Doe",
#         "customer_email": "johndoe@example.com",
#         "customer_phone": "+94123456789",
#         "customer_address": "123 Main St, City, Country",
#         "notes": "Please deliver ASAP."
#     }
#     result = send_order_request_email(sample_data)
#     print(result)