import os
from typing import List, Optional
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Portfolio Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Portfolio Backend Running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/api/github/profile")
def github_profile(username: str = Query(..., description="GitHub username")):
    """Fetch public GitHub profile details for the given username."""
    url = f"https://api.github.com/users/{username}"
    try:
        r = requests.get(url, headers={"Accept": "application/vnd.github+json"}, timeout=10)
        if r.status_code == 404:
            raise HTTPException(status_code=404, detail="GitHub user not found")
        r.raise_for_status()
        data = r.json()
        # Select useful fields
        profile = {
            "login": data.get("login"),
            "name": data.get("name") or data.get("login"),
            "avatar_url": data.get("avatar_url"),
            "bio": data.get("bio"),
            "location": data.get("location"),
            "blog": data.get("blog"),
            "html_url": data.get("html_url"),
            "followers": data.get("followers"),
            "following": data.get("following"),
            "public_repos": data.get("public_repos"),
            "company": data.get("company"),
            "twitter_username": data.get("twitter_username"),
        }
        return profile
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"GitHub API error: {str(e)}")

@app.get("/api/github/repos")
def github_repos(
    username: str = Query(..., description="GitHub username"),
    limit: int = Query(6, ge=1, le=50, description="Max repositories to return"),
    include_forks: bool = Query(False, description="Whether to include forks"),
):
    """Fetch public repositories for the given username, sorted by stargazers then updated."""
    url = f"https://api.github.com/users/{username}/repos?per_page=100&type=public&sort=updated"
    try:
        r = requests.get(url, headers={"Accept": "application/vnd.github+json"}, timeout=15)
        r.raise_for_status()
        repos = r.json()
        # Filter and map
        filtered = [
            {
                "name": repo.get("name"),
                "full_name": repo.get("full_name"),
                "description": repo.get("description"),
                "html_url": repo.get("html_url"),
                "homepage": repo.get("homepage"),
                "language": repo.get("language"),
                "stargazers_count": repo.get("stargazers_count", 0),
                "fork": repo.get("fork", False),
                "topics": repo.get("topics", []),
                "updated_at": repo.get("updated_at"),
            }
            for repo in repos
            if include_forks or not repo.get("fork", False)
        ]
        # Sort by stars then updated
        filtered.sort(key=lambda x: (x.get("stargazers_count", 0), x.get("updated_at") or ""), reverse=True)
        return filtered[:limit]
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"GitHub API error: {str(e)}")

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
