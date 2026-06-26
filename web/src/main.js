import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import CompetitorCompare from './views/CompetitorCompare.vue'
import CostTarget from './views/CostTarget.vue'
import './assets/style.css'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/competitor' },
    { path: '/competitor', component: CompetitorCompare },
    { path: '/cost', component: CostTarget },
  ],
})

createApp(App).use(router).mount('#app')
