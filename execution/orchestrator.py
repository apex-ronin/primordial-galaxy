import time
import json
import logging
from datetime import datetime
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/orchestrator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Orchestrator")

class Orchestrator:
    def __init__(self):
        self.results = []
        self.errors = []
        self.max_retries = 3
        self.backoff_factor = 2

    def run_module(self, name, function, *args, **kwargs):
        """
        Executes a module function with retry logic and error handling.
        """
        logger.info(f"Starting module: {name}")
        print(f"\n[{name}] executing...")
        
        attempt = 0
        while attempt < self.max_retries:
            try:
                # Execute the function
                data = function(*args, **kwargs)
                
                # Check for empty results if that's considered a failure (optional logic)
                if data is None:
                    logger.warning(f"Module {name} returned None")
                    return []
                
                count = len(data) if isinstance(data, list) else 1
                logger.info(f"Module {name} completed successfully. Items: {count}")
                print(f"    [*] Success. Found {count} items.")
                
                # Add source tag if missing
                if isinstance(data, list):
                    for item in data:
                        if 'source' not in item:
                            item['source'] = name
                            
                return data

            except Exception as e:
                attempt += 1
                wait_time = self.backoff_factor ** attempt
                
                logger.error(f"Module {name} failed (Attempt {attempt}/{self.max_retries}): {str(e)}")
                print(f"    [!] Error: {str(e)}")
                
                # Record error pattern
                self._log_error(name, str(e))
                
                if attempt < self.max_retries:
                    print(f"    ... Retrying in {wait_time} seconds ...")
                    time.sleep(wait_time)
                else:
                    print(f"    [!!!] Module {name} FAILED after {self.max_retries} attempts.")
                    return []
        return []

    def _log_error(self, source, error_msg):
        """
        Logs error patterns to a JSON file for "learning".
        """
        error_file = "logs/error_patterns.json"
        
        # Determine error type
        error_type = "unknown"
        if "400" in error_msg: error_type = "bad_request_cfg"
        elif "401" in error_msg or "403" in error_msg: error_type = "auth_error"
        elif "429" in error_msg: error_type = "rate_limit"
        elif "timeout" in error_msg.lower(): error_type = "timeout"
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "error_type": error_type,
            "message": str(error_msg)
        }
        
        # Load existing
        patterns = []
        if os.path.exists(error_file):
            try:
                with open(error_file, 'r') as f:
                    patterns = json.load(f)
            except:
                patterns = []
        
        patterns.append(entry)
        
        # Keep last 100
        if len(patterns) > 100:
            patterns = patterns[-100:]
            
        # Save
        try:
            with open(error_file, 'w') as f:
                json.dump(patterns, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save error log: {e}")

    def consolidate_results(self, result_lists):
        """
        Flattens execution results into a single list.
        """
        all_items = []
        for res in result_lists:
            if isinstance(res, list):
                all_items.extend(res)
            elif res:
                all_items.append(res)
        return all_items
