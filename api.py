import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, retry_if_result
from requests.exceptions import RequestException

# Define what is a "bad" response that needs a retry
def is_rate_limit_or_server_error(response):
    """Return True if the response status code is 429 or 5xx."""
    return response.status_code == 429 or response.status_code >= 500

class JiraAPI:
    BASE_URL = "https://issues.apache.org/jira/rest/api/2"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "LLM-Corpus-Scraper (github.com/Naman-Bhalla)"
        })

    @retry(
        # Try 7 times before giving up
        stop=stop_after_attempt(7),  
        # Wait 2s, then 4s, 8s, 16s, 32s, 60s (max)
        wait=wait_exponential(multiplier=1, min=2, max=60),  
        # Retry on network errors OR if the function returns a 429/5xx response
        retry=(retry_if_exception_type(RequestException) | retry_if_result(is_rate_limit_or_server_error))
    )
    def _make_request(self, method, url, **kwargs):
        """A single, retry-enabled request method."""
        try:
            response = self.session.request(method, url, timeout=15, **kwargs)
            
            # If we get a 429 or 5xx, we want to retry.
            # We return the response object to let tenacity's `retry_if_result` check it.
            if is_rate_limit_or_server_error(response):
                print(f"Server error or rate limit hit: {response.status_code}. Retrying...")
                return response

            # For other 4xx errors (like 404 Not Found), raise an exception immediately.
            response.raise_for_status()  
            
            return response
            
        except RequestException as e:
            # This catches connection errors, timeouts, etc.
            print(f"Network error: {e}. Retrying...")
            raise  # Re-raise to trigger tenacity's retry_if_exception_type

    def search_issues(self, project_key, start_at=0, max_results=50):
        """
        Fetches a batch of issues for a project, ordered by creation date.
        """
        print(f"Fetching issues for {project_key} (startAt={start_at})...")
        url = f"{self.BASE_URL}/search"
        
        # JQL: Order by 'created' date ASC to ensure a stable order for pagination
        jql = f"project = '{project_key}' ORDER BY created ASC"
        
        # Optimize: Only request fields you actually need!
        fields = [
            "summary", "description", "comment", "status", "priority", 
            "labels", "issuetype", "reporter", "assignee", "created", "updated",
            "project" # Need project for the processor
        ]
        
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": ",".join(fields)
        }
        
        response = self._make_request("GET", url, params=params)
        
        # If we exit the retry loop and still have a bad response, raise an error
        if response.status_code != 200:
            raise Exception(f"Failed to fetch data after retries. Final status: {response.status_code} {response.text}")
            
        return response.json()