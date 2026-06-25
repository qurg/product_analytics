<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getDimensions, getAnalysis } from '../api'

// 成本统一为财报成本（目标成本仅用于洲际下钻，不在口径层展示）
const metrics = computed(() => [
  { key: 'revenue', label: '收入' },
  { key: 'cost', label: '成本' },
  { key: 'gross', label: '毛利' },
  { key: 'expense', label: '费用' },
  { key: 'contrib', label: '贡献利润' },
])
const MONTH_LABELS = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']

const dims = reactive({ years: [], regions: [], l2s: [], l3_to_l2: {} })
// month=null 表示全年；点击月度图某月柱子可下钻该月，再点取消
const filters = reactive({ metric: 'revenue', region: '', l2: '', l3: '', month: null })
const data = ref(null)
const loading = ref(false)

// 三级产品根据所选二级产品联动
const l3Options = computed(() => {
  const all = Object.keys(dims.l3_to_l2)
  if (!filters.l2) return all
  return all.filter((l3) => dims.l3_to_l2[l3] === filters.l2)
})

let cMonth, cRegion, cL2
const monthEl = ref(null), regionEl = ref(null), l2El = ref(null)

const fmt = (v) => {
  if (v == null) return '-'
  const n = Number(v)
  if (Math.abs(n) >= 1e8) return (n / 1e8).toFixed(2) + '亿'
  if (Math.abs(n) >= 1e4) return Math.round(n / 1e4) + '万'
  return n.toFixed(0)
}

const kpis = computed(() => {
  const k = data.value?.kpis || {}
  const mo = filters.month
  return [
    { label: mo ? `本年${mo}月` : '本年累计', val: fmt(k.cur_total), cls: 'c-blue' },
    { label: '同比', val: k.yoy == null ? '-' : k.yoy + '%', cls: k.yoy >= 0 ? 'c-green' : 'c-red' },
    { label: '预算', val: fmt(k.budget_total), cls: 'c-grey' },
    { label: '达成率', val: k.achieve_rate == null ? '-' : k.achieve_rate + '%', cls: k.achieve_rate >= 100 ? 'c-green' : 'c-yellow' },
    { label: mo ? `上年${mo}月` : '上年同期', val: fmt(k.prev_total), cls: 'c-grey' },
    { label: '今年预算 vs 去年累计', val: `${fmt(k.budget_full_total)}｜${fmt(k.prev_full_total)}`, cls: 'c-grey', small: true },
  ]
})

// 对比口径说明：本年至今 vs 上年同期（按相同月份）
const periodText = computed(() => {
  const d = data.value
  if (!d) return ''
  if (d.month) return `对比口径：${d.month}月（本年 vs 上年同月）`
  const ms = d.cur_months || []
  if (!ms.length) return ''
  const span = ms.length === 1 ? `${ms[0]}月` : `${ms[0]}-${ms[ms.length - 1]}月`
  return `对比口径：本年${span} vs 上年同期${span}（同比/达成率均按同期计算，预算亦取同期）`
})

async function load() {
  loading.value = true
  try {
    data.value = await getAnalysis({
      metric: filters.metric,
      region: filters.region,
      l2: filters.l2,
      l3: filters.l3,
      month: filters.month || undefined,
    })
    await nextTick()
    renderCharts()
  } finally {
    loading.value = false
  }
}

function renderCharts() {
  const d = data.value
  if (!d) return
  cMonth = cMonth || echarts.init(monthEl.value)
  cRegion = cRegion || echarts.init(regionEl.value)
  cL2 = cL2 || echarts.init(l2El.value)

  const months = d.monthly
  // 选中月份时在月度图上高亮该月
  const markArea = filters.month
    ? {
        silent: true,
        itemStyle: { color: 'rgba(66,133,244,0.10)' },
        data: [[{ xAxis: MONTH_LABELS[filters.month - 1] }, { xAxis: MONTH_LABELS[filters.month - 1] }]],
      }
    : undefined
  cMonth.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (ps) => {
        let s = ps[0].axisValue + '<br/>'
        ps.forEach((p) => {
          const v = p.seriesName === '同比%'
            ? (p.value == null ? '-' : p.value + '%')
            : fmt(p.value)
          s += `${p.marker}${p.seriesName}：${v}<br/>`
        })
        return s
      },
    },
    legend: { data: [`${d.prev_year}实际`, `${d.cur_year}实际`, `${d.cur_year}预算`, '同比%'], top: 0 },
    grid: { left: 64, right: 56, top: 36, bottom: 28 },
    xAxis: { type: 'category', data: MONTH_LABELS },
    yAxis: [
      { type: 'value', axisLabel: { formatter: (v) => fmt(v) } },
      { type: 'value', axisLabel: { formatter: '{value}%' }, splitLine: { show: false } },
    ],
    series: [
      { name: `${d.prev_year}实际`, type: 'bar', data: months.map((m) => m.prev), itemStyle: { color: '#4285F4' } },
      { name: `${d.cur_year}实际`, type: 'bar', data: months.map((m) => m.cur), itemStyle: { color: '#FBBC05' }, markArea },
      { name: `${d.cur_year}预算`, type: 'bar', data: months.map((m) => m.budget), itemStyle: { color: '#34A853' } },
      { name: '同比%', type: 'line', yAxisIndex: 1, data: months.map((m) => m.yoy), itemStyle: { color: '#EA4335' }, smooth: true },
    ],
  }, true)
  // 点击某月柱子 -> 下钻该月；再点同一月 -> 取消
  cMonth.off('click')
  cMonth.on('click', (p) => {
    const mo = p.dataIndex + 1
    filters.month = filters.month === mo ? null : mo
  })

  // 洲际/二级产品对比：本年实际 + 预算(非收入指标) + 签约收入 + 操作收入
  const isRevenue = filters.metric === 'revenue'
  const barCmp = (rows) => {
    const series = [
      { name: '本年实际', type: 'bar', data: rows.map((r) => r.cur), itemStyle: { color: '#4285F4' } },
    ]
    // 收入指标下"预算"即签约收入，避免重复故不另画
    if (!isRevenue && !d.budget_disabled) {
      series.push({ name: '预算', type: 'bar', data: rows.map((r) => r.budget), itemStyle: { color: '#34A853' } })
    }
    series.push(
      { name: '签约收入', type: 'bar', data: rows.map((r) => r.sign_rev), itemStyle: { color: '#00ACC1' } },
      { name: '操作收入', type: 'bar', data: rows.map((r) => r.op_rev), itemStyle: { color: '#FB8C00' } },
    )
    return {
      tooltip: { trigger: 'axis', valueFormatter: (v) => fmt(v) },
      legend: { data: series.map((s) => s.name), top: 0 },
      grid: { left: 56, right: 16, top: 36, bottom: 64 },
      xAxis: {
        type: 'category',
        data: rows.map((r) => r.name),
        axisLabel: {
          interval: 0,
          rotate: rows.length > 5 ? 35 : 0,
          formatter: (v) => (v.length > 6 ? v.slice(0, 6) + '…' : v),
        },
      },
      yAxis: { type: 'value', axisLabel: { formatter: (v) => fmt(v) } },
      series,
    }
  }
  cRegion.setOption(barCmp(d.by_region), true)
  cL2.setOption(barCmp(d.by_l2), true)
}

const monthScope = computed(() =>
  filters.month ? `${filters.month}月` : '全年'
)

watch(() => filters.l2, () => {
  if (filters.l3 && dims.l3_to_l2[filters.l3] !== filters.l2) filters.l3 = ''
})
watch(filters, load, { deep: true })
window.addEventListener('resize', () => { cMonth?.resize(); cRegion?.resize(); cL2?.resize() })

onMounted(async () => {
  dims.years = (await getDimensions().then((d) => (Object.assign(dims, d), d))).years
  await load()
})
</script>

<template>
  <div class="filters">
    <div class="filter-group">
      <label>洲际</label>
      <select v-model="filters.region">
        <option value="">全部</option>
        <option v-for="r in dims.regions" :key="r" :value="r">{{ r }}</option>
      </select>
    </div>
    <div class="filter-group">
      <label>二级产品</label>
      <select v-model="filters.l2">
        <option value="">全部</option>
        <option v-for="l in dims.l2s" :key="l" :value="l">{{ l }}</option>
      </select>
    </div>
    <div class="filter-group">
      <label>三级产品</label>
      <select v-model="filters.l3">
        <option value="">全部</option>
        <option v-for="l in l3Options" :key="l" :value="l">{{ l }}</option>
      </select>
    </div>
    <div class="divider"></div>
    <div class="filter-group">
      <label>指标</label>
      <div class="chips">
        <button v-for="m in metrics" :key="m.key" class="chip" :class="{ active: filters.metric === m.key }" @click="filters.metric = m.key">{{ m.label }}</button>
      </div>
    </div>
  </div>

  <div class="kpis">
    <div class="kpi" v-for="k in kpis" :key="k.label">
      <div class="kpi-label">{{ k.label }}</div>
      <div class="kpi-val" :class="k.cls" :style="k.small ? 'font-size:18px' : ''">{{ k.val }}</div>
    </div>
  </div>

  <div v-if="periodText" style="padding:0 24px 4px;color:var(--text3);font-size:12px">
    {{ periodText }}
  </div>

  <div v-if="data?.budget_disabled" style="padding:0 24px;color:#EA8600;font-size:13px">
    已选具体三级产品，预算仅到二级粒度，故预算/达成率不展示。
  </div>

  <div class="charts">
    <div class="card chart-full">
      <div class="card-header">
        <h3>月度对比（实际 vs 预算 vs 同比）</h3>
        <span style="font-size:12px;color:var(--text3)">
          {{ filters.month ? `已选 ${filters.month} 月（点该月柱子取消）` : '点击某月柱子可下钻联动下方对比' }}
        </span>
      </div>
      <div class="canvas-wrap-tall" ref="monthEl"></div>
    </div>
    <div class="card">
      <div class="card-header"><h3>洲际对比 · {{ monthScope }}</h3></div>
      <div class="canvas-wrap" ref="regionEl"></div>
    </div>
    <div class="card">
      <div class="card-header"><h3>二级产品对比 · {{ monthScope }}</h3></div>
      <div class="canvas-wrap" ref="l2El"></div>
    </div>
  </div>
</template>
