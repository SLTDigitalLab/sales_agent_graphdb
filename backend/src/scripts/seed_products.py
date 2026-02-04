import csv
import os
import sys

sys.path.append(os.getcwd())

from src.api.db.sessions import SessionLocal 
from src.api.db.models import Product

def seed_products():
    csv_file_path = "products.csv"
    
    if not os.path.exists(csv_file_path):
        print(f"Error: Could not find {csv_file_path}")
        return

    db = SessionLocal()
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            added_count = 0
            skipped_count = 0
            
            print("--- Starting Database Seed ---")
            
            for row in reader:
                sku = row['sku']
                name = row['product_name']
                price = float(row['price'].replace(',', ''))
                category = row['category_name']
                url = row['url']
                
                # Check if Product exists
                existing_product = db.query(Product).filter(Product.sku == sku).first()
                
                if existing_product:
                    skipped_count += 1
                else:
                    # Create new Product Record
                    new_product = Product(
                        sku=sku,
                        name=name,
                        price=price,
                        category=category,
                        product_url=url,
                        image_url=None,      
                        stock_quantity=50     
                    )
                    db.add(new_product)
                    added_count += 1
            
            # Commit all changes
            db.commit()
            print("--------------------------------")
            print(f"✅ Seeding Complete!")
            print(f"Added:   {added_count} new products")
            print(f"Skipped: {skipped_count} existing products")
            
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_products()