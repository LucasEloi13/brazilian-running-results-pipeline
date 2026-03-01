"""
Example usage of the SIMPLIFIED global logger configuration.

Call setup_global_logger() ONCE at the start of your app (e.g., in main.py),
then use logging.info(), logging.debug(), etc. anywhere in your code.

ALL logs go to a SINGLE FILE with class/module names included automatically.
"""

import logging
from config.logger_config import setup_global_logger


# ============================================================================
# STEP 1: Initialize logging ONCE at the start of your application
# ============================================================================
# Put this in your main.py:

def initialize_app_logging():
    """Call this once at the start of your application."""
    setup_global_logger(
        log_level=logging.INFO,  # Change to DEBUG for more details
        log_filename="app.log",  # Single log file for everything
        log_dir="logs",
        console_output=True,
        detailed_format=False  # Set True to see filename:line_number
    )


# ============================================================================
# STEP 2: Use logging normally throughout your code
# ============================================================================

# In your extractors:
class EventNameExtractor:
    """Example showing how to use logging in your class."""
    
    def __init__(self, config: dict):
        self.config = config
        # Just use logging.info() directly - no self.logger needed!
        logging.info(f"{self.__class__.__name__} initialized")
    
    def extract(self, pages: int):
        """Extract data with simple logging."""
        logging.info(f"Starting extraction of {pages} pages")
        
        try:
            for page in range(1, pages + 1):
                logging.debug(f"Processing page {page}/{pages}")
                # Your extraction logic here
                logging.info(f"Page {page} processed successfully")
            
            logging.info(f"Extraction completed: {pages} pages processed")
            
        except Exception as e:
            logging.error(f"Error during extraction: {e}", exc_info=True)
            raise


# In any module/function:
def my_parser_function(html: str):
    """Example function using logging."""
    logging.debug("Starting HTML parsing")
    
    try:
        # Your parsing logic
        events = []
        logging.info(f"Parsed {len(events)} events")
        return events
    except Exception as e:
        logging.error(f"Parse error: {e}", exc_info=True)
        raise


# ============================================================================
# MAIN EXAMPLE
# ============================================================================
if __name__ == "__main__":
    # Initialize logging ONCE
    initialize_app_logging()
    
    # Now use logging anywhere
    logging.info("Application started")
    
    # Create objects - they all log to the same file
    extractor = EventNameExtractor({"test": "config"})
    extractor.extract(3)
    
    # Call functions - all in same log
    my_parser_function("<html></html>")
    
    logging.info("Application finished")
    
    print("\n" + "="*70)
    print("Check logs/app.log to see ALL logs in ONE file!")
    print("="*70)
