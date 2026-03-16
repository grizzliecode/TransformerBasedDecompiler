import os
import requests
import time
import zipfile
from github import Github, GithubException, Auth

TOKEN_LOCATION = "TOKEN.txt"
DATASET_RAW_DIRECTORY = "../dataset_raw"
USER_AGENT = "C-DECOMPILER_RESEARCH_BOT"
MIN_STARS = 50
MAX_REPOS = 2500
licenses = ["mit", "apache-2.0", "gpl-3.0", "bsd-3-clause", "lgpl-3.0", "mpl-2.0"]

def load_github_token():
    if not os.path.exists(TOKEN_LOCATION):
        raise FileNotFoundError(f"Token file '{TOKEN_LOCATION}' not found.")
    else:
        with open(TOKEN_LOCATION, 'r') as fin:
            token = fin.read().strip()
            if not token:
                raise ValueError(f"Token file '{TOKEN_LOCATION}' is empty.")
            return token

def unzip_file(filepath, extract_to):
    with zipfile.ZipFile(filepath, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def download(repo):
    try:
        zip_url = repo.get_archive_link("zipball")
        response = requests.get(zip_url, stream=True)
        if response.status_code == 200:
            filename = f"{repo.owner.login}_{repo.name}.zip"
            filepath = os.path.join(DATASET_RAW_DIRECTORY, filename)
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            unzip_file(filepath, os.path.join(DATASET_RAW_DIRECTORY, f"{repo.owner.login}_{repo.name}"))
            os.remove(filepath)
        else:
            print(f"Failed to download {repo.full_name}: HTTP {response.status_code}")
    except (GithubException, zipfile.BadZipFile) as e:
        print(f"Error occurred while processing {repo.full_name}: {e}")

if __name__ == "__main__":
    os.makedirs(DATASET_RAW_DIRECTORY, exist_ok=True)
    token = ""
    try:
        token = load_github_token()
    except (FileNotFoundError, ValueError) as e:
        print(f"Error loading GitHub token: {e}")
        exit(1)
    auth = Auth.Token(token)
    g = Github(auth=auth, user_agent=USER_AGENT)
    alredy_downloaded = 0 
    for license in licenses:
        query = f"language:c stars:>={MIN_STARS} size:500..50000 license:{license}"
        repositories = g.search_repositories(query=query, sort="stars", order="desc")
        print(repositories.totalCount)
        for i in range(min(MAX_REPOS, repositories.totalCount)):
            if alredy_downloaded >= MAX_REPOS:
                break
            
            languages = repositories[i].get_languages()
            total_bytes = sum(languages.values())
            c_bytes = languages.get("C", 0)
            c_percentage = (c_bytes / total_bytes) * 100 if total_bytes > 0 else 0
            if c_percentage < 80:
                continue

            if i % 100 == 0:
                print(f"Processing repository {i+1}/{min(MAX_REPOS, repositories.totalCount)}")
            download(repositories[i])
            
            limits = g.get_rate_limit()
            rate_limit = limits.rate
            if rate_limit.remaining < 10:
                reset_time = rate_limit.reset.timestamp() - time.time()
                # Sleep until the rate limit resets, so that I don't get blocked by github
                time.sleep(max(reset_time, 0))
            time.sleep(2) 
            alredy_downloaded += 1
        if alredy_downloaded >= MAX_REPOS:
            break
        