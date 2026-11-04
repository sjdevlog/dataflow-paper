import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    cors: true,
    // GitHub Codespaces 등 원격 주소(*.app.github.dev)로 접속할 수 있게 허용
    allowedHosts: true,
    // 프론트에서 /api 로 부르면 같은 컴퓨터의 백엔드(B1, 8000번)로 넘겨준다.
    // .env 에 VITE_API_URL=/api 로 두면 백엔드 포트를 따로 공개하지 않아도 된다.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
