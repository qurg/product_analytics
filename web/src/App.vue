<template>
  <header>
    <div class="logo">📊</div>
    <h1>产品分析系统</h1>
    <nav class="nav">
      <router-link to="/budget">预算分析</router-link>
      <router-link to="/competitor">竞对价对比</router-link>
      <router-link to="/import">数据导入</router-link>
    </nav>
    <span class="spacer">预算达成 · 同比分析</span>
  </header>
  <router-view />
</template>
