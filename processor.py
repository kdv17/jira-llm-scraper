import re
from pydantic import BaseModel, ValidationError, Field
from typing import List, Optional, Dict, Any

# --- 1. Define the Target LLM Schema ---
# This model *enforces* the clean structure.
class LLMTrainingSample(BaseModel):
    issue_key: str
    project: str
    created_at: str
    updated_at: str
    status: str
    priority: str
    issue_type: str
    reporter: Optional[str] = None
    assignee: Optional[str] = None
    labels: List[str]
    
    # The cleaned, unstructured text
    title: str
    description_text: str
    comments_text: str
    
    # The derived tasks for an instruction-tuned LLM
    derived_tasks: List[Dict[str, str]]

# --- 2. Helper for cleaning Jira's markup ---
def clean_jira_text(text: Optional[str]) -> str:
    """
    A simple cleaner for Jira's wiki markup.
    This can be improved, but it's a good start.
    """
    if not text:
        return ""
    
    # Remove {code...} blocks
    text = re.sub(r'\{code:.*?\}', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove {noformat...} blocks
    text = re.sub(r'\{noformat\}', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove {quote...} blocks
    text = re.sub(r'\{quote\}', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove panel macros
    text = re.sub(r'\{panel:.*?\}', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove image thumbnails
    text = re.sub(r'!image.png\|thumbnail!', ' ', text, flags=re.IGNORECASE)
    
    # Remove [links|...]
    text = re.sub(r'\[(.*?)\|.*?\]', r'\1', text) # Keep text from links
    
    # Remove standalone links [http...]
    text = re.sub(r'\[(https?|ftp)://.*?\]', ' ', text)
    
    # Remove formatting characters: *bold*, _italic_, -strike-, +under+, ^super^, ~sub~
    text = re.sub(r'[\*_+\^~-]', '', text)
    
    # Remove color markup
    text = re.sub(r'\{color:.*?\}', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _get_name(field: Optional[Dict[str, Any]]) -> Optional[str]:
    """Safely get a 'name' or 'displayName' from a Jira user/status field."""
    if field:
        return field.get("displayName", field.get("name"))
    return None

# --- 3. The Transformation Function ---
def process_issue(raw_issue: Dict[str, Any]) -> Optional[LLMTrainingSample]:
    """
    Transforms a single raw issue JSON from the API into our clean
    LLMTrainingSample.
    """
    try:
        fields = raw_issue.get("fields", {})
        
        # Extract and clean text
        title = fields.get("summary", "")
        description = clean_jira_text(fields.get("description"))
        
        # Combine all comments into a single text block
        comments_list = []
        if fields.get("comment", {}).get("comments"):
            for comment in fields["comment"]["comments"]:
                comments_list.append(clean_jira_text(comment.get("body")))
        comments_text = "\n---\n".join(comments_list)
        
        # --- 4. Generate Derived Tasks ---
        tasks = []

        # Task 1: Summarization (using title as the summary)
        full_text = f"Title: {title}\nDescription: {description}\nComments: {comments_text}"
        if len(full_text) > len(title) + 50: # Only create task if text is substantial
            tasks.append({
                "instruction": "Summarize the following issue report.",
                "input": full_text,
                "output": title 
            })
        
        # Task 2: Q&A - Priority
        priority_name = _get_name(fields.get("priority"))
        if priority_name:
            tasks.append({
                "instruction": f"What is the priority of issue {raw_issue.get('key')}?",
                "input": f"Title: {title}\nDescription: {description}",
                "output": priority_name
            })
        
        # Task 3: Q&A - Issue Type
        type_name = _get_name(fields.get("issuetype"))
        if type_name:
            tasks.append({
                "instruction": f"What is the issue type for {raw_issue.get('key')}?",
                "input": f"Title: {title}\nDescription: {description}",
                "output": type_name
            })
        
        # Task 4: Classification - Status
        status_name = _get_name(fields.get("status"))
        if status_name:
             tasks.append({
                "instruction": "Classify the current status of this issue.",
                "input": f"Title: {title}\nDescription: {description}",
                "output": status_name
            })

        # Use Pydantic to validate and build the clean object
        sample = LLMTrainingSample(
            issue_key=raw_issue.get("key"),
            project=_get_name(fields.get("project")),
            created_at=fields.get("created"),
            updated_at=fields.get("updated"),
            status=_get_name(fields.get("status")),
            priority=_get_name(fields.get("priority")),
            issue_type=_get_name(fields.get("issuetype")),
            reporter=_get_name(fields.get("reporter")),
            assignee=_get_name(fields.get("assignee")),
            labels=fields.get("labels", []),
            title=title,
            description_text=description,
            comments_text=comments_text,
            derived_tasks=tasks
        )
        return sample

    except ValidationError as e:
        # This handles "malformed data"
        print(f"Data validation error for issue {raw_issue.get('key')}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error processing issue {raw_issue.get('key')}: {e}")
        return None