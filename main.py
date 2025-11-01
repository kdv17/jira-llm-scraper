import jsonlines
import time
from api import JiraAPI
from processor import process_issue
from state_manager import load_state, save_state
import config

def scrape_project(project_key):
    """
    Main scraping pipeline for a single project.
    """
    print(f"--- Starting scrape for project: {project_key} ---")
    
    api = JiraAPI()
    output_file = f"{project_key}_corpus.jsonl"
    
    # 1. Resume from last state
    start_at = load_state(project_key)
    total_processed_in_session = 0
    max_results = 50  # API batch size (50 is a common default)
    
    # 'a' mode appends to the file. If it doesn't exist, it's created.
    with jsonlines.open(output_file, mode='a') as writer:
        while True:
            try:
                # 2. Fetch a batch of issues
                batch_data = api.search_issues(project_key, start_at, max_results)
                
                if not batch_data or not batch_data.get("issues"):
                    print(f"No more issues found for {project_key} at startAt={start_at}.")
                    break
                
                issues = batch_data.get("issues", [])
                
                # 3. Transform and Write each issue
                for raw_issue in issues:
                    llm_sample = process_issue(raw_issue)
                    if llm_sample:
                        # Pydantic's .dict() is deprecated; use .model_dump()
                        writer.write(llm_sample.model_dump()) 
                
                batch_size = len(issues)
                total_processed_in_session += batch_size
                
                # 4. Update state for next loop
                start_at += batch_size
                save_state(project_key, start_at) # Save state *after* successful batch
                
                print(f"Processed batch for {project_key}. Issues {start_at - batch_size} to {start_at}. Total this session: {total_processed_in_session}")
                
                # Check if we're at the end
                total_available = batch_data.get("total", 0)
                if start_at >= total_available:
                    print(f"Finished project {project_key}. Scraped all {total_available} issues.")
                    break
                
                # Small courtesy delay
                time.sleep(0.5) 

            except Exception as e:
                print(f"A critical error occurred: {e}. Stopping.")
                print(f"Last successful state saved: project {project_key} at startAt={start_at}")
                # The state is not saved for this failed batch,
                # so it will retry from the last successful 'start_at' index on next run.
                break

if __name__ == "__main__":
    print("Starting Jira LLM Corpus Scraper...")
    for project in config.PROJECTS:
        scrape_project(project)
    print("--- All scraping jobs complete. ---")