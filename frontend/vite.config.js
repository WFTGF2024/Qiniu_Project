// vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      // 所有发到 /tts 的请求，转发到 120.79.25.184:7206
      '/tts': {
        target: 'http://120.79.25.184:7206',
        changeOrigin: true,
        rewrite: p => p.replace(/^\/tts/, '')
      }
    }
  }
})
