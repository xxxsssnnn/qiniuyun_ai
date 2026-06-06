import react from '@vitejs/plugin-react'
import { createServer } from 'vite'

const server = await createServer({
  configFile: false,
  plugins: [react()],
  server: {
    host: process.env.VITE_HOST ?? '127.0.0.1',
    port: Number(process.env.VITE_PORT ?? 5173),
  },
})

await server.listen()
server.printUrls()
