<script setup>
import { ref, reactive, onMounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import {
  getCostTrend, getCostCurrent, getCostLastPeriod,
  saveCostBatch, deleteCostTrack,
} from '../api'

const biz = '海运'
const trend = ref({ series: [] })
const current = ref({ rows: [] })
const loading = ref(false)
const chartEl = ref(null)
let chart = null
const selectedLanes = ref([])      // 趋势图选中的线路

// 录入面板
const showEntry = ref(false)
const entry = reactive({ effective_date: '', end_date: '', rows: [] })
const saving = ref(false)
const toast = ref('')

const COLORS = ['#4285F4', '#34A853', '#F29900', '#9334E6', '#EA4335', '#00ACC1']

async function load() {
  loading.value = true
  try {
    trend.value = await getCostTrend(biz)
    current.value = await getCostCurrent(biz)
    if (!selectedLanes.value.length)
      selectedLanes.value = trend.value.series.map((s) => s.lane)
    await nextTick()
    renderChart()
  } finally {
    loading.value = false
  }
}

function renderChart() {
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)
  const series = trend.value.series
    .filter((s) => selectedLanes.value.includes(s.lane))
    .map((s, i) => ({
      name: s.lane, type: 'line', step: 'end', symbol: 'circle', symbolSize: 4,
      data: s.points.map((p) => [p.effective_date, p.amount]),
    }))
  chart.setOption({
    color: COLORS,
    tooltip: { trigger: 'axis', valueFormatter: (v) => (v == null ? '' : v.toLocaleString()) },
    legend: { data: series.map((s) => s.name), top: 0, type: 'scroll' },
    grid: { left: 56, right: 20, top: 36, bottom: 40 },
    xAxis: { type: 'time' },
    yAxis: { type: 'value', name: 'USD/FEU', scale: true },
    series,
  }, true)
}

function toggleLane(l) {
  const i = selectedLanes.value.indexOf(l)
  if (i >= 0) selectedLanes.value.splice(i, 1)
  else selectedLanes.value.push(l)
  renderChart()
}

// ---- 开一期录入 ----
async function openEntry() {
  const lp = await getCostLastPeriod(biz)
  entry.effective_date = lp.suggest_effective || ''
  entry.end_date = ''
  entry.rows = lp.rows.map((r) => ({
    lane_id: r.lane_id, lane: r.lane, unit: r.unit,
    last_amount: r.last_amount, amount: r.last_amount, // 预填上期值
  }))
  showEntry.value = true
}

function carryAll() {
  entry.rows.forEach((r) => { r.amount = r.last_amount })
}

// 整列粘贴：在某行输入框粘贴 Excel 一列，自动从该行向下填充
function onPaste(e, idx) {
  const text = (e.clipboardData || window.clipboardData).getData('text')
  if (!text || !/[\n\t]/.test(text.trim()) && text.split(/\s+/).length < 2) return
  e.preventDefault()
  const nums = text.split(/[\r\n\t]+/).map((x) => x.trim()).filter((x) => x !== '')
  nums.forEach((n, k) => {
    const row = entry.rows[idx + k]
    if (row) { const v = parseFloat(n.replace(/,/g, '')); if (!isNaN(v)) row.amount = v }
  })
}

function changed(r) {
  return r.amount != null && r.last_amount != null && Number(r.amount) !== Number(r.last_amount)
}

async function saveBatch() {
  if (!entry.effective_date) { toast.value = '请填生效日期'; return }
  saving.value = true
  try {
    const items = entry.rows
      .filter((r) => r.amount !== '' && r.amount != null)
      .map((r) => ({ lane_id: r.lane_id, amount: Number(r.amount) }))
    const res = await saveCostBatch({
      biz_type: biz, effective_date: entry.effective_date,
      end_date: entry.end_date || null, items,
    })
    toast.value = `已保存 ${res.saved} 条`
    showEntry.value = false
    await load()
  } finally { saving.value = false }
}

const fmt = (v) => (v == null ? '—' : Number(v).toLocaleString())

onMounted(load)
window.addEventListener('resize', () => chart && chart.resize())
</script>

<template>
  <div class="filters">
    <div class="filter-group"><label>业务线</label>
      <select disabled><option>海运</option></select>
    </div>
    <button class="btn" @click="openEntry">＋ 开一期录入</button>
    <span class="spacer" style="margin-left:auto;font-size:12px;color:var(--text3)">
      目标成本 · 市场价跟踪（单位 USD/FEU）
    </span>
  </div>

  <div class="page" style="max-width:none">
    <!-- 开一期录入面板 -->
    <div class="card" v-if="showEntry" style="margin-bottom:12px;border:1px solid var(--blue)">
      <div class="card-header" style="position:static">
        <h3>开一期目标成本</h3>
        <div class="row" style="gap:8px">
          <label style="font-size:13px">生效日期
            <input type="date" v-model="entry.effective_date" class="inp" />
          </label>
          <label style="font-size:13px">结束日期
            <input type="date" v-model="entry.end_date" class="inp" />
          </label>
          <button class="btn btn-ghost" @click="carryAll">全部沿用上期</button>
        </div>
      </div>
      <p style="font-size:12px;color:var(--text3);margin-bottom:8px">
        本期价已预填上期值，只改动变化的；可从 Excel 复制一列价格，点第一格粘贴自动整列填充；Tab/Enter 逐格跳。
      </p>
      <table>
        <thead><tr><th>线路</th><th>上期价</th><th>本期目标成本</th><th></th></tr></thead>
        <tbody>
          <tr v-for="(r, idx) in entry.rows" :key="r.lane_id">
            <td><b>{{ r.lane }}</b></td>
            <td style="color:var(--text3)">{{ fmt(r.last_amount) }}</td>
            <td>
              <input type="number" step="0.01" v-model="r.amount"
                     @paste="onPaste($event, idx)"
                     style="width:120px;border:1px solid var(--border);border-radius:4px;padding:6px 8px"
                     :style="changed(r) ? 'border-color:var(--blue);background:var(--blue-bg)' : ''" />
            </td>
            <td><span v-if="changed(r)" style="color:var(--blue);font-size:12px">改</span></td>
          </tr>
        </tbody>
      </table>
      <div class="row" style="margin-top:12px;gap:8px">
        <button class="btn" :disabled="saving" @click="saveBatch">{{ saving ? '保存中…' : '保存本期' }}</button>
        <button class="btn btn-ghost" @click="showEntry = false">取消</button>
        <span v-if="toast" class="toast ok" style="margin:0">{{ toast }}</span>
      </div>
    </div>

    <!-- 趋势图 -->
    <div class="card" style="margin-bottom:12px">
      <div class="card-header" style="position:static">
        <h3>目标成本趋势</h3>
        <div class="chips">
          <span v-for="(s, i) in trend.series" :key="s.lane" class="chip"
                :class="{ active: selectedLanes.includes(s.lane) }" @click="toggleLane(s.lane)">
            {{ s.lane }}
          </span>
        </div>
      </div>
      <div ref="chartEl" style="height:340px"></div>
    </div>

    <!-- 当前成本 + 变动预警 -->
    <div class="card">
      <div class="card-header" style="position:static"><h3>当前目标成本 · 环比变动</h3></div>
      <table>
        <thead><tr>
          <th>线路</th><th>目的港</th><th>船东</th><th>当前目标成本</th>
          <th>生效区间</th><th>环比上期</th><th>起运港费</th>
        </tr></thead>
        <tbody>
          <tr v-for="r in current.rows" :key="r.lane">
            <td><b>{{ r.lane }}</b></td>
            <td style="color:var(--text3);font-size:12px">{{ r.dest_ports }}</td>
            <td style="font-size:12px">{{ r.carrier }}</td>
            <td><b>{{ fmt(r.amount) }}</b> <span style="color:var(--text3);font-size:11px">{{ r.currency }}/{{ r.unit }}</span></td>
            <td style="font-size:12px;color:var(--text3)">{{ r.effective_date }} ~ {{ r.end_date || '' }}</td>
            <td :class="r.change_pct > 0 ? 'c-red' : (r.change_pct < 0 ? 'c-green' : '')">
              <template v-if="r.change_pct != null">
                {{ r.change_pct > 0 ? '▲' : (r.change_pct < 0 ? '▼' : '') }}{{ Math.abs(r.change_pct) }}%
                <span style="color:var(--text3);font-size:11px">(上期 {{ fmt(r.prev_amount) }})</span>
              </template>
              <span v-else style="color:var(--text3)">—</span>
            </td>
            <td style="font-size:12px">{{ fmt(r.extra_fee) }}</td>
          </tr>
        </tbody>
      </table>
      <p style="font-size:12px;color:var(--text3);margin-top:10px">
        ▲红=涨 / ▼绿=跌（环比上一期）。线路固定属性（港口/船东/柜型/起运港费）在主数据维护，录入只填会变的目标成本。
      </p>
    </div>
  </div>
</template>
