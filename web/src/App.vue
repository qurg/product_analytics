<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const menu = [
  { name: '竞对价对比', children: [
    { label: '仓内', path: '/competitor', q: { scope: '仓内' } },
    { label: '尾程', path: '/competitor', q: { scope: '尾程' } },
  ] },
  { name: '目标成本', children: [
    { label: '跨境运输海运', path: '/cost', q: { line: '跨境运输海运' } },
    { label: '跨境到仓-海运', path: '/cost', q: { line: '跨境到仓-海运' } },
    { label: '跨境到仓-空运', path: '/cost', q: { line: '跨境到仓-空运' } },
    { label: '小包空运', path: '/cost', q: { line: '小包空运' } },
  ] },
]
const activeKey = computed(() => {
  const q = route.query
  return route.path + '|' + (q.scope || q.line || '')
})
const keyOf = (c) => c.path + '|' + (c.q.scope || c.q.line || '')
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand"><span class="logo">📊</span><span>产品分析系统</span></div>
      <nav class="menu">
        <div v-for="m in menu" :key="m.name" class="menu-group">
          <div class="menu-top">{{ m.name }}</div>
          <router-link v-for="c in m.children" :key="c.label"
                       :to="{ path: c.path, query: c.q }"
                       class="menu-sub" :class="{ active: activeKey === keyOf(c) }">
            {{ c.label }}
          </router-link>
        </div>
      </nav>
    </aside>
    <main class="content"><router-view /></main>
  </div>
</template>
