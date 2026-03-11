import os
import csv
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from datetime import date
import json
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
BASE_URL = "https://silvertechsafe.com"
DATA_FILE = 'data/data.csv'
TEMPLATES_DIR = 'templates'
OUTPUT_DIR = 'dist'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

class SEOAuditor:
    """Scans generated HTML for E-E-A-T and SEO compliance."""
    def __init__(self, directory):
        self.directory = directory
        self.issues = []

    def audit(self):
        print("\n--- Running Pre-Launch SEO Audit ---")
        for filename in os.listdir(self.directory):
            if filename.endswith(".html"):
                self.check_file(os.path.join(self.directory, filename))

        if not self.issues:
            print("✅ Audit Passed: Site is ready for production.")
        else:
            print(f"⚠️ Found {len(self.issues)} issues:")
            for issue in self.issues:
                print(f"  - {issue}")

    def check_file(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
            text = soup.get_text().lower()
            
            if not soup.find('meta', attrs={'name': 'description'}):
                self.issues.append(f"{os.path.basename(filepath)}: Missing Meta Description.")
            
            if "affiliate" not in text:
                self.issues.append(f"{os.path.basename(filepath)}: Missing Affiliate Disclosure statement.")

def build_site():
    print("Starting site build process...")
    
    # 1. LOAD DATA
    try:
        # Fill missing values with empty strings to prevent 'nan' showing up in HTML
        df = pd.read_csv(DATA_FILE).fillna('')
        print(f"Loaded {len(df)} products from CSV.")
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return

    # 2. DATA PREPARATION (Grouping for Hubs)
    categories = df['Category'].unique()
    solution_map = {}
    for cat in categories:
        cat_items = df[df['Category'] == cat][['Problem_ID', 'Product_Solution', 'Caregiver_Hook']].to_dict('records')
        solution_map[cat] = cat_items

    # 3. GENERATE PAGES
    
    # --- BLOCK 4: PRODUCT PAGES LOOP (FUTURE-PROOFED FOR THICK CONTENT) ---
    print("Generating product pages...")
    try:
        prod_temp = env.get_template('master_layout.html')
        for _, row in df.iterrows():
            problem_id = str(row['Problem_ID']).strip()
            file_path = os.path.join(OUTPUT_DIR, f"{problem_id}.html")
            
            # FUTURE-PROOFING: Convert the entire row to a dictionary
            # Every column in your CSV automatically becomes a variable like {{ Column_Name }}
            context = row.to_dict()
            
            # Add computed variables
            context.update({
                "product": row['Product_Solution'], 
                "category_slug": str(row['Category']).lower().replace(' ', '-'),
                "current_date": date.today().strftime("%B %Y"),
                "BASE_URL": BASE_URL
            })
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(prod_temp.render(context))
    except Exception as e:
        print(f"❌ Error in product loop: {e}")

    # --- BLOCK 5: CATEGORY HUB PAGES ---
    try:
        cat_temp = env.get_template('category_layout.html')
        for cat in categories:
            cat_slug = str(cat).lower().replace(' ', '-')
            products_for_hub = df[df['Category'] == cat].to_dict('records')
            
            hub_data = {
                "category": cat,
                "category_slug": cat_slug,
                "problem": f"Common {cat} Issues",
                "category_products": products_for_hub,
                "BASE_URL": BASE_URL
            }
            
            output_path = os.path.join(OUTPUT_DIR, f"category-{cat_slug}.html")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(cat_temp.render(hub_data))
            print(f"✅ Generated Hub: category-{cat_slug}.html")
    except Exception as e:
        print(f"❌ Error rendering category hubs: {e}")

    # --- BLOCK 6: STATIC & TRUST PAGES (FIXED LOGIC) ---
    print("Generating static and trust pages...")
    trust_pages = [
        {'template': 'home_layout.html', 'output': 'index.html'},
        {'template': 'legal_layout.html', 'output': 'about.html'},
        {'template': 'legal_layout.html', 'output': 'privacy.html'},
        {'template': 'contact_layout.html', 'output': 'contact.html'}
    ]

    for page in trust_pages:
        try:
            temp = env.get_template(page['template'])
            # Pass categories so navigation links can be generated on the homepage
            with open(os.path.join(OUTPUT_DIR, page['output']), "w", encoding="utf-8") as f:
                f.write(temp.render(BASE_URL=BASE_URL, categories=categories))
            print(f"✅ Generated Trust Page: {page['output']}")
        except Exception as e:
            # Removed the "silent pass" so you can actually see what breaks
            print(f"❌ Error rendering {page['output']}: {e}")

    # 4. SITEMAP
    try:
        today = date.today().isoformat()
        with open(os.path.join(OUTPUT_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
            
            # Static pages
            for page in ['index.html', 'about.html', 'contact.html', 'privacy.html']:
                f.write(f'<url><loc>{BASE_URL}/{page}</loc><lastmod>{today}</lastmod></url>')
            
            # Category Hubs
            for cat in categories:
                cat_slug = str(cat).lower().replace(' ', '-')
                f.write(f'<url><loc>{BASE_URL}/category-{cat_slug}.html</loc><lastmod>{today}</lastmod></url>')
            
            # Product Pages
            for _, row in df.iterrows():
                f.write(f'<url><loc>{BASE_URL}/{str(row["Problem_ID"]).strip()}.html</loc><lastmod>{today}</lastmod></url>')
                
            f.write('</urlset>')
        print("✅ Sitemap generated successfully.")
    except Exception as e:
        print(f"❌ Error generating sitemap: {e}")

if __name__ == "__main__":
    build_site()
    # Run the SEO Auditor on the output folder
    auditor = SEOAuditor(OUTPUT_DIR)
    auditor.audit()