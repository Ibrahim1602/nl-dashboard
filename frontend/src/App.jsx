import { useState } from 'react'
import Plot from 'react-plotly.js'

// Change this once you deploy your backend (e.g. to your Render URL)
const API_URL = 'http://127.0.0.1:8000/query'

const EXAMPLE_QUESTIONS = [
  'top 5 highest rated action movies',
  'average budget by genre',
  'which director has the most movies',
  'top 10 highest grossing movies after 2010',
]

function App() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [errorMsg, setErrorMsg] = useState(null)

  async function runQuery(q) {
    const finalQuestion = q ?? question
    if (!finalQuestion.trim()) return

    setLoading(true)
    setErrorMsg(null)
    setResult(null)

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: finalQuestion }),
      })

      if (!response.ok) {
        throw new Error(`Server responded with status ${response.status}`)
      }

      const data = await response.json()

      if (data.error) {
        setErrorMsg(data.error)
      }

      setResult(data)
    } catch (err) {
      setErrorMsg(`Request failed: ${err.message}. Is the backend running at ${API_URL}?`)
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(e) {
    e.preventDefault()
    runQuery()
  }

  function handleExampleClick(q) {
    setQuestion(q)
    runQuery(q)
  }

  const chartFigure = result?.chart_json ? JSON.parse(result.chart_json) : null

  return (
    <div className="app">
      <header className="header">
        <h1>Ask Your Data</h1>
        <p className="subtitle">Ask a question about the movies dataset in plain English</p>
      </header>

      <form onSubmit={handleSubmit} className="query-form">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. top 5 highest rated action movies"
          className="query-input"
        />
        <button type="submit" className="query-button" disabled={loading}>
          {loading ? 'Thinking...' : 'Ask'}
        </button>
      </form>

      <div className="examples">
        <span className="examples-label">Try:</span>
        {EXAMPLE_QUESTIONS.map((q) => (
          <button
            key={q}
            className="example-chip"
            onClick={() => handleExampleClick(q)}
            disabled={loading}
          >
            {q}
          </button>
        ))}
      </div>

      {errorMsg && (
        <div className="error-box">
          <strong>Something went wrong:</strong> {errorMsg}
        </div>
      )}

      {result && !errorMsg && (
        <div className="results">
          <div className="sql-box">
            <span className="sql-label">Generated SQL</span>
            <code>{result.sql}</code>
          </div>

          {chartFigure && (
            <div className="chart-container">
              <Plot
                data={chartFigure.data}
                layout={{ ...chartFigure.layout, autosize: true }}
                useResizeHandler
                style={{ width: '100%', height: '500px' }}
              />
            </div>
          )}

          {!chartFigure && result.rows && (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    {result.columns.map((col) => (
                      <th key={col}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.rows.map((row, i) => (
                    <tr key={i}>
                      {row.map((cell, j) => (
                        <td key={j}>{cell}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default App
