import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import BudgetDashboard from './views/BudgetDashboard.vue'
import CompetitorCompare from './views/CompetitorCompare.vue'
import ImportData from './views/ImportData.vue'
import './assets/style.css'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/budget' },
    { path: '/budget', component: BudgetDashboard },
    { path: '/competitor', component: CompetitorCompare },
    { path: '/import', component: ImportData },
  ],
})

createApp(App).use(router).mount('#app')
