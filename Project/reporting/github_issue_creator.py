import logging
import requests

logger = logging.getLogger(__name__)

def create_github_issue(config: dict, title: str, body: str) -> bool:
    """Creates a GitHub issue on verification failures."""
    github_settings = config.get("github_settings", {})
    if not github_settings.get("enabled", False):
        logger.info("GitHub notifier is disabled.")
        return False
        
    import os
    token = os.environ.get("GITHUB_TOKEN", github_settings.get("github_token"))
    owner = os.environ.get("GITHUB_OWNER", github_settings.get("repository_owner"))
    repo = os.environ.get("GITHUB_REPO", github_settings.get("repository_name"))
    
    # Auto-default if placeholders are present
    if not owner or owner == "YOUR_GITHUB_OWNER":
        owner = "Vannilavan05"
    if not repo or repo == "YOUR_GITHUB_REPO":
        repo = "IM_INFI"
        
    if not token or token == "YOUR_GITHUB_TOKEN":
        logger.warning("GitHub token is not set up. Skipping issue creation.")
        return False
        
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "title": title,
        "body": body
    }
    
    try:
        logger.info(f"Filing GitHub Issue to repository {owner}/{repo}: {title}")
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 201:
            logger.info("GitHub Issue created successfully.")
            return True
        else:
            logger.error(f"Failed to create GitHub Issue. Status Code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error while calling GitHub API: {e}")
        return False
