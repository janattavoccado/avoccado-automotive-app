"""
FastAPI Application with Crawl4AI Integration
This is the FastAPI version of the crawler application, based on the original main3.py.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from pydantic import BaseModel, HttpUrl
from typing import Optional, List

app = FastAPI(
    title="URL Crawler API",
    description="A web crawler API powered by Crawl4AI",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class CrawlRequest(BaseModel):
    url: HttpUrl

class CrawlResponse(BaseModel):
    url: str
    status_code: int
    content_preview: Optional[str] = None
    markdown_content: Optional[str] = None
    metadata: Optional[dict] = None
    internal_links_count: Optional[int] = None
    external_links_count: Optional[int] = None
    internal_links: Optional[List[str]] = None
    external_links: Optional[List[str]] = None

class BatchCrawlRequest(BaseModel):
    urls: List[HttpUrl]

class BatchCrawlResponse(BaseModel):
    results: List[dict]
    total: int

class SearchRequest(BaseModel):
    url: HttpUrl
    extract_links: bool = True

class SearchResponse(BaseModel):
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    content_preview: Optional[str] = None
    internal_links: Optional[List[str]] = None
    external_links: Optional[List[str]] = None
    total_links: Optional[int] = None

def process_result(result) -> dict:
    """
    Process a successful crawl result and return structured data.
    """
    content_preview = None
    markdown_content = None
    
    if result.markdown:
        clean_text = ' '.join(result.markdown.split())
        content_preview = clean_text[:300] + '...' if len(clean_text) > 300 else clean_text
        markdown_content = result.markdown

    internal_links = result.links.get("internal", []) if result.links else []
    external_links = result.links.get("external", []) if result.links else []
    
    # Extract just the URLs from link objects
    internal_urls = [link.get('href', link) if isinstance(link, dict) else str(link) for link in internal_links]
    external_urls = [link.get('href', link) if isinstance(link, dict) else str(link) for link in external_links]

    return {
        "url": result.url,
        "status_code": result.status_code,
        "content_preview": content_preview,
        "markdown_content": markdown_content,
        "metadata": result.metadata,
        "internal_links_count": len(internal_links),
        "external_links_count": len(external_links),
        "internal_links": internal_urls[:50],
        "external_links": external_urls[:50]
    }

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page."""
    with open("templates/index.html", "r") as f:
        return f.read()

@app.post("/api/crawl", response_model=CrawlResponse)
async def crawl_url(request: CrawlRequest):
    """
    Crawl a single URL and return the extracted content.
    """
    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        check_robots_txt=True,
        stream=False
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        results = await crawler.arun_many(
            urls=[str(request.url)],
            config=run_config
        )
        
        if not results or not results[0].success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to crawl {request.url}: {results[0].error_message if results else 'Unknown error'}"
            )
        
        return process_result(results[0])

@app.post("/api/crawl/batch", response_model=BatchCrawlResponse)
async def crawl_batch(request: BatchCrawlRequest):
    """
    Crawl multiple URLs and return all results.
    """
    if len(request.urls) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 URLs allowed per batch"
        )
    
    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        check_robots_txt=True,
        stream=False
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        results = await crawler.arun_many(
            urls=[str(url) for url in request.urls],
            config=run_config
        )
        
        processed_results = []
        for result in results:
            if result.success:
                processed_results.append(process_result(result))
            else:
                processed_results.append({
                    "error": True,
                    "message": f"Failed to crawl {result.url}: {result.error_message}",
                    "url": result.url
                })
        
        return BatchCrawlResponse(results=processed_results, total=len(processed_results))

@app.post("/api/search", response_model=SearchResponse)
async def search_url(request: SearchRequest):
    """
    Search/crawl a URL with optional link extraction.
    """
    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        check_robots_txt=True,
        stream=False
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        results = await crawler.arun_many(
            urls=[str(request.url)],
            config=run_config
        )
        
        if not results or not results[0].success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to crawl {request.url}: {results[0].error_message if results else 'Unknown error'}"
            )
        
        result = process_result(results[0])
        
        response = SearchResponse(
            url=result["url"],
            title=result.get("metadata", {}).get("title"),
            description=result.get("metadata", {}).get("description"),
            content_preview=result.get("content_preview")
        )
        
        if request.extract_links:
            response.internal_links = result.get("internal_links", [])
            response.external_links = result.get("external_links", [])
            response.total_links = (
                result.get("internal_links_count", 0) + 
                result.get("external_links_count", 0)
            )
        
        return response

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "fastapi-crawler"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
