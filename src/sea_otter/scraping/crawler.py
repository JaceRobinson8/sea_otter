import requests
import os
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin, urlparse
import re
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class Config:
    """Configuration for the CISA Advisory Crawler"""
    
    def __init__(self):
        self.data_path = Path.home() / "sea_otter" / "data"
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        # Starting URL for CISA Advisories (type 65)
        self.start_url = 'https://www.cisa.gov/news-events/cybersecurity-advisories?f%5B0%5D=advisory_type%3A65'
        
        # File types to download
        self.target_extensions = ('.pdf', '.json', '.stix')
        
        # Text patterns that indicate generic download links
        self.generic_link_text = {"download", "file", "pdf", "json", "stix", "report", "click", "here"}
        
        # Rate limiting
        self.page_delay = 2  # Delay between listing pages (seconds)
        self.file_delay = 0.5  # Delay between file downloads (seconds)


class FileUtils:
    """Utilities for file handling and name processing"""
    
    @staticmethod
    def sanitize_filename(name):
        """Removes invalid characters for filenames and strips whitespace."""
        name = re.sub(r'[\\/*?:"<>|]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Prevent excessively long filenames
        max_len = 200
        if len(name) > max_len:
            base, ext = os.path.splitext(name)
            name = base[:max_len - len(ext) - 3] + "..." + ext
            
        return name
    
    @staticmethod
    def get_file_extension(url):
        """Extracts the file extension from a URL."""
        try:
            path = urlparse(url).path
            return os.path.splitext(path)[1].lower()
        except Exception:
            return ""
    
    @staticmethod
    def get_filename_from_link(link_tag, file_url, generic_terms):
        """Attempts to extract a meaningful filename from the link's text."""
        link_text = link_tag.get_text(strip=True)
        
        if link_text:
            words = set(re.split(r'\s|\(|\)|\[|\]', link_text.lower())) - {''}
            # Check if text is meaningful (not just generic terms)
            is_generic = words.issubset(generic_terms) or \
                         re.match(r'^\(?(PDF|JSON|STIX)\s*,?\s*[\d.]+?\s*(KB|MB|GB)\)?$', 
                                 link_text, re.IGNORECASE)
            
            if not is_generic and len(link_text) > 4:
                logging.debug(f"Using link text: '{link_text}' for {file_url}")
                # Remove trailing file size indicators
                cleaned_text = re.sub(r'\s*\((PDF|JSON|STIX)\s*,?\s*[\d.]+?\s*(KB|MB|GB)\)$', 
                                     '', link_text, flags=re.IGNORECASE).strip()
                return cleaned_text
        
        # Fallback: Use the filename from the URL path
        try:
            url_path = urlparse(file_url).path
            url_filename = os.path.basename(url_path)
            if url_filename:
                logging.debug(f"Falling back to URL basename: '{url_filename}' for {file_url}")
                return os.path.splitext(url_filename)[0]  # Remove extension
        except Exception as e:
            logging.warning(f"Error parsing URL basename for {file_url}: {e}")
        
        logging.warning(f"Could not determine a filename for URL: {file_url}")
        return None
    
    @staticmethod
    def resolve_filename_collision(base_name, extension, existing_files):
        """Resolves filename collisions by adding a numerical suffix."""
        final_filename = f"{base_name}{extension}"
        
        collision_counter = 1
        while final_filename in existing_files:
            final_filename = f"{base_name}_{collision_counter}{extension}"
            collision_counter += 1
            if collision_counter > 100:
                logging.error(f"Too many filename collisions for base: {base_name}")
                return None
                
        return final_filename


class HTMLParser:
    """HTML parsing utilities for extracting relevant content from web pages"""
    
    @staticmethod
    def find_advisory_links(soup, base_url):
        """Find all advisory links on a list page."""
        # Primary selector based on observed CISA structure
        advisory_links = soup.select('.c-view__row .c-teaser__title a[href]')
        
        if not advisory_links:
            # Broader fallback if primary fails
            logging.warning("Primary selector found no links, trying broader search.")
            advisory_links = soup.find_all('a', href=re.compile(
                r'/news-events/(cybersecurity-advisories|analysis-reports)/ar\d{2}-\d{3}'))
                
        result_links = []
        for link in advisory_links:
            page_url = urljoin(base_url, link['href'])
            
            # Basic check to avoid crawling unrelated domains
            if not urlparse(page_url).netloc == urlparse(base_url).netloc:
                logging.debug(f"Skipping external URL: {page_url}")
                continue
                
            result_links.append(page_url)
            
        return result_links
    
    @staticmethod
    def find_file_links(soup, page_url, target_extensions):
        """Find all downloadable file links on an advisory page."""
        file_links = []
        
        for file_link in soup.find_all('a', href=True):
            file_url = urljoin(page_url, file_link['href'])
            file_ext = FileUtils.get_file_extension(file_url)
            
            if file_ext in target_extensions:
                file_links.append((file_link, file_url, file_ext))
        
        return file_links
    
    @staticmethod
    def find_next_page(soup, current_url):
        """Find the next page link using multiple strategies."""
        # First try the main selector (CISA's pagination)
        next_page_link_tag = soup.select_one('li.pager__item--next a[href]')
        
        # If not found, try more specific CISA pager patterns
        if not next_page_link_tag:
            next_page_link_tag = soup.select_one('nav.pager ul.pager__items li.pager__item--next a[href]')
        
        # If a standard next link was found, use it
        if next_page_link_tag:
            next_page_href = next_page_link_tag['href']
            return urljoin(current_url, next_page_href)
        
        # Otherwise, try to construct pagination manually
        current_url_parts = urlparse(current_url)
        query_params = current_url_parts.query.split('&')
        
        # Look for page parameter in current URL
        for param in query_params:
            if param.startswith('page='):
                current_page = int(param.split('=')[1])
                next_page_param = f'page={current_page + 1}'
                
                # Replace page parameter with next page
                new_query_params = [p if not p.startswith('page=') else next_page_param 
                                   for p in query_params]
                new_query = '&'.join(new_query_params)
                
                # Construct next page URL
                return current_url_parts._replace(query=new_query).geturl()
        
        # If no page parameter found, add it
        separator = '&' if current_url_parts.query else '?'
        return f"{current_url}{separator}page=1"
        
        # Last resort: try alternative selectors (text-based approach)
        next_page_candidates = soup.select('a[href]')
        for a_tag in next_page_candidates:
            if (a_tag.get('rel') == 'next' or 
                'next' in a_tag.get('class', []) or 
                a_tag.get_text(strip=True).lower() == 'next' or
                a_tag.get_text(strip=True).lower() == '›' or
                a_tag.get_text(strip=True).lower() == '»'):
                return urljoin(current_url, a_tag['href'])
        
        # If all strategies fail, return None
        return None


class CISAAdvisoryCrawler:
    """Crawler for CISA cybersecurity advisories"""
    
    def __init__(self):
        self.config = Config()
        self.session = requests.Session()
        
        # Track downloaded files and processed URLs
        self.downloaded_files = set()
        self.processed_advisory_urls = set()
        
        # Statistics
        self.page_num = 1
        self.total_files_downloaded = 0
        
        logging.info(f"Data will be saved to: {self.config.data_path}")
    
    def download_file(self, file_url, file_path, final_filename):
        """Download a file from the given URL."""
        try:
            # Add a small delay before each download request
            time.sleep(self.config.file_delay)
            
            file_response = self.session.get(file_url, timeout=60, stream=True)
            file_response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                for chunk in file_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logging.info(f"Saved to: {file_path}")
            self.downloaded_files.add(final_filename)
            self.total_files_downloaded += 1
            return True
            
        except requests.exceptions.RequestException as dl_e:
            logging.error(f"Failed to download {file_url}: {dl_e}")
            if file_path.exists():  # Clean up potentially incomplete file
                try: 
                    file_path.unlink()
                except OSError: 
                    pass
            return False
        except IOError as io_e:
            logging.error(f"Failed to save file {file_path}: {io_e}")
            return False
    
    def process_file_link(self, file_link, file_url, file_ext):
        """Process a file link and download the file if appropriate."""
        base_name = FileUtils.get_filename_from_link(
            file_link, file_url, self.config.generic_link_text)
        
        if not base_name:
            logging.warning(f"Could not determine usable filename for {file_url}")
            return False
        
        clean_base_name = FileUtils.sanitize_filename(base_name)
        final_filename = FileUtils.resolve_filename_collision(
            clean_base_name, file_ext, self.downloaded_files)
        
        if not final_filename:
            return False
        
        file_path = self.config.data_path / final_filename
        if file_path.exists():
            logging.info(f"Skipping download, file already exists: {file_path}")
            self.downloaded_files.add(final_filename)
            return True
        
        logging.info(f"Downloading: '{final_filename}' from {file_url}")
        return self.download_file(file_url, file_path, final_filename)
    
    def process_advisory_page(self, page_url):
        """Process a single advisory page and download linked files."""
        if page_url in self.processed_advisory_urls:
            logging.debug(f"Skipping already processed advisory: {page_url}")
            return 0
        
        try:
            logging.info(f"Processing advisory page: {page_url}")
            page_response = self.session.get(page_url, timeout=30)
            page_response.raise_for_status()
            page_soup = BeautifulSoup(page_response.text, 'html.parser')
            self.processed_advisory_urls.add(page_url)
            
            files_found = 0
            file_links = HTMLParser.find_file_links(
                page_soup, page_url, self.config.target_extensions)
            
            for file_link, file_url, file_ext in file_links:
                success = self.process_file_link(file_link, file_url, file_ext)
                if success:
                    files_found += 1
            
            if files_found == 0:
                logging.info(f"No target files found on advisory page: {page_url}")
            
            return files_found
            
        except requests.exceptions.RequestException as page_e:
            logging.error(f"Error fetching advisory page {page_url}: {page_e}")
            return 0
        except Exception as e:
            logging.error(f"Error processing advisory {page_url}: {e}", exc_info=True)
            return 0
    
    def process_listing_page(self, list_url):
        """Process a single listing page with advisory links."""
        try:
            logging.info(f"--- Processing List Page {self.page_num}: {list_url} ---")
            main_response = self.session.get(list_url, timeout=30)
            main_response.raise_for_status()
            main_soup = BeautifulSoup(main_response.text, 'html.parser')
            
            # Find advisory links on this page
            advisory_links = HTMLParser.find_advisory_links(main_soup, list_url)
            logging.info(f"Found {len(advisory_links)} potential advisory links on page {self.page_num}")
            
            advisories_processed = 0
            for page_url in advisory_links:
                files_found = self.process_advisory_page(page_url)
                if files_found > 0:
                    advisories_processed += 1
            
            if advisories_processed == 0 and len(advisory_links) > 0:
                logging.warning(f"Found {len(advisory_links)} links, but none seemed to be new advisories")
            
            # Find the next page link
            next_page_url = HTMLParser.find_next_page(main_soup, list_url)
            
            if next_page_url:
                self.page_num += 1
                logging.info(f"Found next page link: {next_page_url}")
                logging.info(f"Waiting {self.config.page_delay} seconds before next page...")
                time.sleep(self.config.page_delay)
            
            return next_page_url
            
        except requests.exceptions.RequestException as list_e:
            logging.error(f"Failed to fetch list page {list_url}: {list_e}")
            return None
        except Exception as e:
            logging.error(f"Error processing list page {list_url}: {e}", exc_info=True)
            return None
    
    def crawl(self):
        """Main crawling function."""
        current_list_url = self.config.start_url
        
        while current_list_url:
            current_list_url = self.process_listing_page(current_list_url)
        
        self.generate_report()
    
    def generate_report(self):
        """Generate a summary report of the crawling results."""
        logging.info("--- Script Finished ---")
        logging.info(f"Processed {self.page_num} list page(s)")
        logging.info(f"Processed {len(self.processed_advisory_urls)} unique advisory pages")
        logging.info(f"Total unique files downloaded in this run: {self.total_files_downloaded}")
        logging.info(f"Total unique filenames tracked: {len(self.downloaded_files)}")
        
        logging.info("Downloaded files by extension:")
        pdf_count = sum(1 for f in self.downloaded_files if f.lower().endswith('.pdf'))
        json_count = sum(1 for f in self.downloaded_files if f.lower().endswith('.json'))
        stix_count = sum(1 for f in self.downloaded_files if f.lower().endswith('.stix'))
        
        logging.info(f"  - PDF files: {pdf_count}")
        logging.info(f"  - JSON files: {json_count}")
        logging.info(f"  - STIX files: {stix_count}")
        logging.info(f"Data saved in: {self.config.data_path}")


if __name__ == "__main__":
    crawler = CISAAdvisoryCrawler()
    crawler.crawl()