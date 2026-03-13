import time
import json
import logging
from datetime import datetime
import os
import concurrent.futures

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
        self.default_timeout = 30 # Default 30s timeout per module
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

    def run_module(self, name, function, *args, **kwargs):
        """
        Executes a module function with retry logic and error handling.
        """
        logger.info(f"Starting module: {name}")
        print(f"\n[{name}] executing...")
        
        attempt = 0
        while attempt < self.max_retries:
            try:
                # Execute with pre-emptive timeout guard using ThreadPoolExecutor
                future = self.executor.submit(function, *args, **kwargs)
                try:
                    data = future.result(timeout=self.default_timeout)
                except concurrent.futures.TimeoutError:
                    raise TimeoutError(f"Module {name} timed out after {self.default_timeout}s")
                
                # Check for empty results
                if data is None:
                    logger.warning(f"Module {name} returned None")
                    return {"status": "success", "data": [], "message": "No items found"}
                
                count = len(data) if isinstance(data, list) else 1
                logger.info(f"Module {name} completed successfully. Items: {count}")
                print(f"    [*] Success. Found {count} items.")
                
                # Add source tag 
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'source' not in item:
                            item['source'] = name
                            
                return {"status": "success", "data": data, "count": count}

            except Exception as e:
                attempt += 1
                wait_time = self.backoff_factor ** attempt
                
                error_msg = str(e)
                logger.error(f"Module {name} failed (Attempt {attempt}/{self.max_retries}): {error_msg}")
                print(f"    [!] Error: {error_msg}")
                
                # Record error pattern - MANDATORY AUDIT REQUIREMENT
                self.errors.append({"module": name, "error": error_msg, "attempt": attempt})
                self._log_error(name, error_msg)
                
                if attempt < self.max_retries:
                    print(f"    ... Retrying in {wait_time} seconds ...")
                    time.sleep(wait_time)
                else:
                    print(f"    [!!!] Module {name} FAILED after {self.max_retries} attempts.")
                    return {"status": "failed", "error": error_msg, "attempts": attempt}
        
        return {"status": "failed", "message": "Max retries exceeded"}

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
