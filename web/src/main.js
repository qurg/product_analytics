import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import CompetitorCompare from './views/CompetitorCompare.vue'
import './assets/style.css'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/competitor' },
    { path: '/competitor', component: CompetitorCompare },
  ],
})

createApp(App).use(router).mount('#app')
