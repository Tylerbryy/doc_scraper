from playwright.sync_api import sync_playwright
import os
import markdown
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

def is_same_domain(url1, url2):
    """Check if two URLs belong to the same domain."""
    return urlparse(url1).netloc == urlparse(url2).netloc

def clean_markdown(text):
    """Clean and format markdown text."""
    # Remove extra whitespace and newlines
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'\s+$', '', text, flags=re.MULTILINE)
    return text

def html_to_markdown(html_content):
    """Convert HTML content to Markdown format."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove unwanted elements
    for element in soup.select('script, style, nav, footer, header, .cookie-notice, [role="navigation"]'):
        element.decompose()
    
    # Remove navigation menus and common UI elements
    for element in soup.find_all(class_=lambda x: x and any(term in str(x).lower() for term in [
        'menu', 'nav', 'header', 'footer', 'cookie', 'banner', 'popup'
    ])):
        element.decompose()
    
    # Extract main content (adjust selectors based on site structure)
    main_content = soup.find('main') or soup.find(id='content') or soup
    
    # Get text and clean it
    text = main_content.get_text(separator='\n', strip=True)
    
    # Clean the text
    text = re.sub(r'\n{3,}', '\n\n', text)  # Replace multiple newlines with double newline
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
    text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)  # Trim lines
    text = re.sub(r'(?<=[.!?])\s+', '\n\n', text)  # Add paragraph breaks after sentences
    
    return text

def save_markdown(content, url, output_file):
    """Append markdown content to a single file."""
    with open(output_file, 'a', encoding='utf-8') as f:
        # Add URL as header and content with separation
        f.write(f"\n\n# {url}\n\n")
        f.write(content)
        f.write("\n\n---\n")  # Add separator between pages
    
    return output_file

def scrape_docs(start_url, output_file='documentation.md'):
    """Main function to scrape documentation and convert to markdown."""
    visited_urls = set()
    
    # Create or clear the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# Documentation\nScraped from {start_url}\n\n---\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        def process_page(url):
            if url in visited_urls or not is_same_domain(start_url, url):
                return
            
            visited_urls.add(url)
            
            try:
                page.goto(url)
                page.wait_for_load_state('networkidle')
                
                # Get page content
                content = page.content()
                
                # Convert to markdown
                markdown_content = html_to_markdown(content)
                
                # Append to the single markdown file
                saved_path = save_markdown(markdown_content, url, output_file)
                print(f"Saved: {url}")
                
                # Find all links on the page
                links = page.eval_on_selector_all('a[href]', """
                    elements => elements.map(el => el.href)
                """)
                
                # Process each link
                for link in links:
                    if link.startswith('http') and is_same_domain(start_url, link):
                        process_page(link)
                        
            except Exception as e:
                print(f"Error processing {url}: {str(e)}")
        
        # Start processing from the initial URL
        process_page(start_url)
        browser.close()

if __name__ == "__main__":

    
    start_url = "https://supabase.com/docs"
    scrape_docs(start_url)
