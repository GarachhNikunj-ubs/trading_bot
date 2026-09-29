import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { exec } from 'child_process'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'market-scanner-api',
      configureServer(server) {
        server.middlewares.use('/api/live-quotes', (req, res, next) => {
          const filePath = path.join(__dirname, 'src', 'data', 'market_scanner.json')
          const pythonBin = path.join(__dirname, '..', 'venv', 'bin', 'python')
          const scriptPath = path.join(__dirname, 'database', 'fetch_market_scanner.py')

          const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`)
          const refresh = url.searchParams.get('refresh') === 'true'

          const sendData = () => {
            try {
              if (fs.existsSync(filePath)) {
                const data = fs.readFileSync(filePath, 'utf-8')
                res.setHeader('Content-Type', 'application/json')
                res.setHeader('Access-Control-Allow-Origin', '*')
                res.end(data)
              } else {
                res.statusCode = 404
                res.end(JSON.stringify({ error: 'Data not found' }))
              }
            } catch (err) {
              res.statusCode = 500
              res.end(JSON.stringify({ error: err.message }))
            }
          }

          if (refresh) {
            exec(`"${pythonBin}" "${scriptPath}"`, (error, stdout, stderr) => {
              if (error) {
                console.error('Error fetching live quotes:', error)
              }
              sendData()
            })
          } else {
            sendData()
          }
        })
      }
    }
  ],
})

