import { useState, useEffect } from 'react'
import { Search, Loader2, Plus, MessageSquare, Mic, Image as ImageIcon, ArrowRight } from 'lucide-react'

// Define types based on backend API
interface SearchResultItem {
  title: string;
  price: string;
  url: string;
  color: string | null;
}

interface HistoryItem {
  id: string;
  query: string;
  timestamp: string;
  results?: SearchResultItem[];
}

const API_BASE = 'http://localhost:8000/api';

function App() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<SearchResultItem[]>([])
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [searched, setSearched] = useState(false)

  const fetchHistory = () => {
    try {
      const localHistory = localStorage.getItem('chatHistory');
      if (localHistory) {
        setHistory(JSON.parse(localHistory));
      }
    } catch (err) {
      console.error("Failed to fetch history from local storage", err)
    }
  }

  useEffect(() => {
    fetchHistory()
  }, [])

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setSearched(true)
    setResults([])

    try {
      const res = await fetch(`${API_BASE}/search/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query })
      })
      
      if (!res.ok || !res.body) {
        console.error("Search failed")
        setLoading(false)
        return
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let done = false;
      let buffer = "";

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";
          
          for (const part of parts) {
            if (part.startsWith("data: ")) {
              const dataStr = part.slice(6);
              try {
                const event = JSON.parse(dataStr);
                if (event.type === "product") {
                  setResults(prev => [...prev, event.product]);
                } else if (event.type === "done") {
                  const newHistoryItem: HistoryItem = {
                    id: event.id,
                    query: event.query,
                    timestamp: event.timestamp,
                    results: event.results
                  };
                  const currentHistory = JSON.parse(localStorage.getItem('chatHistory') || '[]');
                  const updatedHistory = [newHistoryItem, ...currentHistory];
                  localStorage.setItem('chatHistory', JSON.stringify(updatedHistory));
                  setHistory(updatedHistory);
                  setLoading(false);
                }
              } catch (e) {
                console.error("Failed to parse SSE", e);
              }
            }
          }
        }
      }
    } catch (err) {
      console.error("Network error", err)
      setLoading(false)
    }
  }

  const handleNewChat = () => {
    setQuery('')
    setResults([])
    setSearched(false)
  }

  return (
    <div className="app-container">
      {/* Sidebar for Recent Chats */}
      <aside className="sidebar">
        <button className="new-chat-btn" onClick={handleNewChat}>
          <Plus size={20} />
          New chat
        </button>
        
        <div className="recent-section">
          <h3>Recent</h3>
          <div className="history-list">
            {history.length === 0 ? (
              <div style={{ padding: '12px 16px', fontSize: '14px', color: 'var(--text-muted)' }}>No recent searches</div>
            ) : (
              history.map(item => (
                <button 
                  key={item.id} 
                  className="history-item"
                  onClick={() => {
                    setQuery(item.query)
                    setResults(item.results || [])
                    setSearched(true)
                  }}
                >
                  <MessageSquare size={16} />
                  {item.query}
                </button>
              ))
            )}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        {!searched && (
          <div className="greeting">
            <h1>Hi there, <span>what are you looking for?</span></h1>
          </div>
        )}

        <div className="search-container" style={{ marginTop: searched ? '20px' : '0' }}>
          <form className="search-box" onSubmit={handleSearch}>
            <Search size={22} color="var(--text-muted)" />
            <input 
              type="text" 
              placeholder="e.g. stanley cup, pink, under $40" 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={loading}
              autoFocus
            />
            {/* Visual fluff for premium feel */}
            {!query && (
              <>
                <button type="button" className="search-action-btn"><Mic size={20} /></button>
                <button type="button" className="search-action-btn"><ImageIcon size={20} /></button>
              </>
            )}
            
            {query && (
              <button type="submit" className="search-action-btn submit-btn" disabled={loading}>
                {loading ? <Loader2 size={20} className="spinner" /> : <ArrowRight size={20} />}
              </button>
            )}
          </form>
        </div>

        {/* Results */}
        <div className="results-container">
          {loading && (
            <div className="loading">
              <Loader2 size={32} className="spinner" />
              <span>Browsing the web for products...</span>
            </div>
          )}

          {!loading && searched && results.length === 0 && (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '15px' }}>
              No matches found. Try loosening the price or color.
            </div>
          )}

          {!loading && results.map((item, idx) => (
            <a key={idx} href={item.url} target="_blank" rel="noreferrer" className="result-card">
              <div className="result-header">
                <span className="result-price">{item.price}</span>
                <span className="result-color" style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
                  {item.color || 'No color specified'}
                </span>
              </div>
              <div className="result-title">{item.title}</div>
              <div className="result-meta">
                <span>{new URL(item.url).hostname}</span>
              </div>
            </a>
          ))}
        </div>
      </main>
    </div>
  )
}

export default App
